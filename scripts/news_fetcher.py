"""
News Fetcher for Abuzz Competitor Intelligence
Uses Serper.dev (Google Search API) + Claude AI (Anthropic) for analysis
"""

import asyncio
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import hashlib
import httpx
import json
import os
import time
import uuid
import re
import requests
import anthropic
from google import genai as google_genai
from google.genai import types as genai_types
from dotenv import load_dotenv

# Load .env.local first, then .env as fallback
load_dotenv('.env.local')
load_dotenv()

# Configure APIs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_gemini_client = google_genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
# Get database URL - prefer pooler connection, strip Prisma-specific params
_raw_db_url = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL")
DATABASE_URL = _raw_db_url.split('?')[0] if _raw_db_url else None  # Remove query params like ?pgbouncer=true

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- Serper API cache (file-based, 7-day TTL) ---
SERPER_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache', 'serper')
SERPER_CACHE_TTL = 7 * 24 * 3600  # 7 days in seconds

# Global semaphore for Serper rate limiting (initialized in async main)
SERPER_SEMAPHORE = None


def _serper_cache_key(query, region, search_type):
    raw = f"{query}|{region}|{search_type}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(query, region, search_type):
    key = _serper_cache_key(query, region, search_type)
    cache_file = os.path.join(SERPER_CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
            age = time.time() - data.get('cached_at', 0)
            if age < SERPER_CACHE_TTL:
                return data.get('results', [])
        except Exception:
            pass
    return None


def _cache_set(query, region, search_type, results):
    os.makedirs(SERPER_CACHE_DIR, exist_ok=True)
    key = _serper_cache_key(query, region, search_type)
    cache_file = os.path.join(SERPER_CACHE_DIR, f"{key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump({'cached_at': time.time(), 'results': results}, f)
    except Exception:
        pass

# --- Gemini search cache (file-based, 1-day TTL) ---
GEMINI_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache', 'gemini')
GEMINI_CACHE_TTL = 24 * 3600  # 1 day in seconds


def _gemini_cache_get(name):
    key = hashlib.md5(name.lower().encode()).hexdigest()
    path = os.path.join(GEMINI_CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            if time.time() - data.get('cached_at', 0) < GEMINI_CACHE_TTL:
                return data.get('results', [])
        except Exception:
            pass
    return None


def _gemini_cache_set(name, results):
    os.makedirs(GEMINI_CACHE_DIR, exist_ok=True)
    key = hashlib.md5(name.lower().encode()).hexdigest()
    path = os.path.join(GEMINI_CACHE_DIR, f"{key}.json")
    try:
        with open(path, 'w') as f:
            json.dump({'cached_at': time.time(), 'results': results}, f)
    except Exception:
        pass


def _parse_gemini_grounding(response):
    """Extract verified article URLs and summaries from Gemini text + grounding metadata.
    Uses grounding_supports to map text segments to the best source URL.
    """
    articles = []
    candidate = response.candidates[0] if response.candidates else None
    if not candidate:
        return articles
    
    # Get text and grounding
    text = ""
    if candidate.content and candidate.content.parts:
        text = candidate.content.parts[0].text or ""
    
    grounding = getattr(candidate, 'grounding_metadata', None)
    if not grounding:
        return articles

    chunks = getattr(grounding, 'grounding_chunks', []) or []
    supports = getattr(grounding, 'grounding_supports', []) or []
    
    # Map text lines to chunks via overlap with supports
    current_idx = 0
    # Split keeping newlines to calculate indices correctly, then strip for processing
    # Using simple split and manual tracking
    
    # We iterate character by character? No, simple split is fine if we assume \n
    lines = text.split('\n')
    
    processed_urls = set()

    for line in lines:
        line_len = len(line)
        start = current_idx
        end = current_idx + line_len
        current_idx = end + 1 # count the newline
        
        line_clean = line.strip()
        # Only process list items
        if not (line_clean.startswith('*') or line_clean.startswith('-')):
            continue
            
        # Find overlapping supports
        best_chunk_idx = -1
        max_score = 0.0
        
        for support in supports:
            # support.segment is an object with start_index, end_index
            seg = support.segment
            # Check overlap: start < seg.end and end > seg.start
            if max(start, seg.start_index) < min(end, seg.end_index):
                # This support overlaps with the line
                indices = support.grounding_chunk_indices
                scores = support.confidence_scores
                
                for idx, score in zip(indices, scores):
                    if score > max_score:
                         if 0 <= idx < len(chunks):
                             chunk = chunks[idx]
                             if hasattr(chunk, 'web') and chunk.web:
                                 uri = getattr(chunk.web, 'uri', None)
                                 # Skip if not news url
                                 if uri and is_news_url(uri):
                                     max_score = score
                                     best_chunk_idx = idx

        if best_chunk_idx != -1:
             chunk = chunks[best_chunk_idx]
             uri = getattr(chunk.web, 'uri', None)
             
             # Avoid adding same URL multiple times from same response
             if uri in processed_urls:
                 continue
             processed_urls.add(uri)

             title_source = getattr(chunk.web, 'title', None)
             
             # Clean snippet: remove markers
             snippet = re.sub(r'^[\*\-]\s*', '', line_clean)
             snippet = snippet.replace('**', '')
             
             # Use snippet as title if extracted title is missing or generic
             title = title_source if title_source else snippet[:100]

             articles.append({
                'title': title,
                'link': uri,
                'snippet': snippet,
                'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'), 
                '_search_region': 'gemini_search'
            })

    return articles


def search_gemini(competitor_name, days_back=7):
    """Search for news using Gemini 2.0 Flash with Google Search grounding.
    Returns article dicts in the same format as search_news() (Serper).
    Grounding metadata provides verified URLs — no hallucination risk.
    """
    if not GEMINI_API_KEY or not _gemini_client:
        return []

    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()

    cached = _gemini_cache_get(search_name)
    if cached is not None:
        print(f"      [GEMINI-CACHED] {search_name}: {len(cached)} articles")
        return cached

    try:
        prompt = (
            f"Search for news articles published in the last {days_back} days about "
            f"the company '{search_name}'. Focus on: new contracts, partnerships, "
            f"product launches, funding rounds, office openings, leadership changes, "
            f"deployments in malls, airports, hospitals, or universities. "
            f"Please provide a bulleted list of the articles you find, including their dates."
        )
        response = _gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                temperature=1.0  # Required for optimal grounding activation
            )
        )

        articles = _parse_gemini_grounding(response)
        print(f"      [GEMINI]  {search_name}: {len(articles)} articles found")
        _gemini_cache_set(search_name, articles)
        return articles

    except Exception as e:
        print(f"      Gemini search error: {e}")
        return []


# ---------------------------------------------------------------------------
# ASYNC SEARCH LAYER
# All async functions share the same file caches as their sync counterparts.
# ---------------------------------------------------------------------------

async def search_serper_async(query, search_type='news', region='global', num_results=10, tbs_val=None):
    """Async version of search_serper() — uses httpx.AsyncClient, same 7-day cache."""
    if isinstance(region, dict):
        region_config = region
        region_label = region.get('_label', f"{region.get('gl', '?')}_{region.get('hl', '?')}")
    else:
        region_config = REGIONS.get(region, REGIONS['global'])
        region_label = region

    cached = _cache_get(query, region_label, search_type)
    if cached is not None:
        print(f"      [CACHED] {region_label}: {query[:60]}")
        return cached

    if not SERPER_API_KEY:
        return []

    payload = {"q": query, "gl": region_config['gl'], "hl": region_config['hl'], "num": num_results}
    if tbs_val:
        payload["tbs"] = tbs_val

    try:
        global SERPER_SEMAPHORE
        if SERPER_SEMAPHORE is None:
             # Fallback if not initialized (though it should be)
             SERPER_SEMAPHORE = asyncio.Semaphore(3)
        
        async with SERPER_SEMAPHORE:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await http.post(
                    f"https://google.serper.dev/{search_type}",
                    json=payload,
                    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
                )
        if response.status_code in (400, 403) and "credits" in response.text.lower():
            print("      ❌ Serper credits exhausted!")
            return []
        response.raise_for_status()
        data = response.json()
        results = data.get('news' if search_type == 'news' else 'organic', [])
        print(f"      [API]    {region_label}: {query[:60]}")
        _cache_set(query, region_label, search_type, results)
        return results
    except Exception as e:
        print(f"      Serper async error: {e}")
        return []


async def search_news_async(competitor_name, regions_to_search, days_back=None, native_region=None):
    """Async version — fires ALL (query × region) Serper combinations concurrently."""
    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()
    queries = [
        f'"{search_name}" contract OR deal OR partnership OR launch OR expansion',
        f'"{search_name}" mall OR airport OR hospital OR university',
        f'"{search_name}" wayfinding OR "digital signage" OR kiosk',
        f'"{search_name}" "virtual assistant" OR "directory" OR screens',
    ]

    # Build all (query, region) task pairs
    task_pairs = []
    for region in regions_to_search:
        for query in queries:
            task_pairs.append((region, query))
    if native_region:
        for query in queries:
            task_pairs.append((native_region, query))

    tasks = [search_serper_async(q, 'news', r, 10) for r, q in task_pairs]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls = set()
    all_results = []
    filtered = 0
    for (region_key, _), result in zip(task_pairs, results_lists):
        if isinstance(result, Exception):
            continue
        for r in result:
            url = r.get('link', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                if is_news_url(url):
                    label = region_key if isinstance(region_key, str) else region_key.get('_label', 'native')
                    r['_search_region'] = label
                    all_results.append(r)
                else:
                    filtered += 1
    if filtered > 0:
        print(f" ({filtered} filtered)", end="")
    return all_results


async def search_gemini_async(competitor_name, days_back=7):
    """Async Gemini search with per-call jitter for Tier 1 rate limit safety."""
    if not GEMINI_API_KEY or not _gemini_client:
        return []

    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()

    cached = _gemini_cache_get(search_name)
    if cached is not None:
        print(f"      [GEMINI-CACHED] {search_name}: {len(cached)} articles")
        return cached

    # Jitter before live API call — prevents all 5 parallel competitors hitting Gemini at T=0
    await asyncio.sleep(random.uniform(1.0, 3.0))

    try:
        prompt = (
            f"Search for news articles published in the last {days_back} days about "
            f"the company '{search_name}'. Focus on: new contracts, partnerships, "
            f"product launches, funding rounds, office openings, leadership changes, "
            f"deployments in malls, airports, hospitals, or universities. "
            f"Please provide a bulleted list of the articles you find, including their dates."
        )
        response = await _gemini_client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
            )
        )
        articles = _parse_gemini_grounding(response)
        print(f"      [GEMINI]  {search_name}: {len(articles)} articles found")
        _gemini_cache_set(search_name, articles)
        return articles

    except Exception as e:
        if '429' in str(e):
            print(f"      [GEMINI] Rate limited ({search_name}) — skipping")
        else:
            print(f"      Gemini async error: {e}")
        return []


async def search_gemini_deep_async(competitor_name, website, days_back=7):
    """Deep site-specific Gemini search — triggered when Serper returns 0 results.
    Uses site:competitor.com grounding to surface press releases and niche trade coverage.
    """
    if not GEMINI_API_KEY or not _gemini_client or not website:
        return []

    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()
    domain = re.sub(r'^https?://', '', website).rstrip('/')

    # Extra jitter — stacks on top of the base jitter from the concurrent sibling call
    await asyncio.sleep(random.uniform(1.5, 3.0))

    try:
        prompt = (
            f"Find any press releases, news announcements, or blog posts from or about "
            f"'{search_name}' (website: {domain}) published in the last {days_back} days. "
            f"Also search trade publications, PR Newswire, BusinessWire, and industry blogs "
            f"for any coverage of {search_name}. "
            f"Please provide a bulleted list of the articles you find, including their dates."
        )
        response = await _gemini_client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
            )
        )
        articles = _parse_gemini_grounding(response)
        if articles:
            print(f"      [GEMINI-DEEP] {search_name}: {len(articles)} articles found")
        return articles

    except Exception as e:
        if '429' not in str(e):
            print(f"      Gemini deep search error: {e}")
        return []


# Priority competitors (most likely to have news)
PRIORITY_COMPETITORS = [
    "Mappedin", "22Miles", "Pointr", "MapsPeople", "Broadsign",
    "Stratacache", "Poppulo", "Korbyt", "IndoorAtlas", "Inpixon"
]

# Regional search configurations - MENA + Europe + Global focus
REGIONS = {
    'global': {'gl': 'us', 'hl': 'en'},
    'mena': {'gl': 'ae', 'hl': 'en'},     # UAE/MENA in English
    'europe': {'gl': 'gb', 'hl': 'en'},   # Europe (via UK) in English
    'ksa': {'gl': 'sa', 'hl': 'en'},      # Saudi Arabia
}

# Native language search configs keyed by lowercase country name
HQ_NATIVE_REGIONS = {
    'france':       {'gl': 'fr', 'hl': 'fr', '_label': 'france_fr'},
    'germany':      {'gl': 'de', 'hl': 'de', '_label': 'germany_de'},
    'spain':        {'gl': 'es', 'hl': 'es', '_label': 'spain_es'},
    'norway':       {'gl': 'no', 'hl': 'no', '_label': 'norway_no'},
    'denmark':      {'gl': 'dk', 'hl': 'da', '_label': 'denmark_da'},
    'finland':      {'gl': 'fi', 'hl': 'fi', '_label': 'finland_fi'},
    'sweden':       {'gl': 'se', 'hl': 'sv', '_label': 'sweden_sv'},
    'switzerland':  {'gl': 'ch', 'hl': 'de', '_label': 'switzerland_de'},
    'netherlands':  {'gl': 'nl', 'hl': 'nl', '_label': 'netherlands_nl'},
    'italy':        {'gl': 'it', 'hl': 'it', '_label': 'italy_it'},
    'israel':       {'gl': 'il', 'hl': 'iw', '_label': 'israel_iw'},
    'south korea':  {'gl': 'kr', 'hl': 'ko', '_label': 'korea_ko'},
    'korea':        {'gl': 'kr', 'hl': 'ko', '_label': 'korea_ko'},
    'japan':        {'gl': 'jp', 'hl': 'ja', '_label': 'japan_ja'},
    'hong kong':    {'gl': 'hk', 'hl': 'zh-tw', '_label': 'hongkong_zh'},
    'china':        {'gl': 'cn', 'hl': 'zh-cn', '_label': 'china_zh'},
    'poland':       {'gl': 'pl', 'hl': 'pl', '_label': 'poland_pl'},
}
# Countries where English is primary — no native-language search needed
ENGLISH_SPEAKING_HQ = {'uk', 'usa', 'canada', 'australia', 'ireland', 'new zealand', 'singapore'}


def get_native_region(headquarters):
    """Return native language search config for a non-English-speaking HQ, or None."""
    if not headquarters:
        return None
    hq_lower = headquarters.lower()
    for eng in ENGLISH_SPEAKING_HQ:
        if eng in hq_lower:
            return None
    for country, config in HQ_NATIVE_REGIONS.items():
        if country in hq_lower:
            return config
    return None

# URLs that indicate non-news content (product pages, sales, profiles)
BLOCKED_URL_PATTERNS = [
    'linkedin.com', 'crunchbase.com', 'facebook.com', 'instagram.com',
    'youtube.com', 'twitter.com', 'x.com',
    '/product', '/products', '/catalog', '/catalogo',
    '/shop', '/store', '/loja', '/tienda',
    '/contact', '/contato', '/about', '/sobre',
    'mercadolivre', 'mercadolibre', 'amazon.com', 'alibaba.com',
    'olx.com', 'ebay.com',
    'glassdoor.com', 'indeed.com', 'ziprecruiter.com',
    'wikipedia.org', 'dnb.com', 'zoominfo.com',
    '/careers', '/vagas', '/empleo',
]


def is_news_url(url):
    """Filter out product pages, sales sites, social media, and company profiles"""
    if not url:
        return False
    url_lower = url.lower()
    for pattern in BLOCKED_URL_PATTERNS:
        if pattern in url_lower:
            return False
    return True


ANALYSIS_PROMPT = """You are a competitive intelligence analyst for Abuzz, a company specializing in wayfinding and directory solutions.

I found these search results about {competitor_name}:

{articles}

CONTEXT:
Today is {today_date}.
{date_instruction}

IMPORTANT: Analyze ALL articles. Always output your title and summary in ENGLISH.

IMPORTANT: Analyze ALL articles. Always output your title and summary in ENGLISH.

For articles where 'Region Found' contains "GEMINI": You MUST be more lenient. Include minor updates, blog posts, and general company activity even if it's not a major "news event". DO NOT filter these out unless they are completely irrelevant (spam/ads).

Your job is to find REAL NEWS EVENTS only. Include:

Your job is to find REAL NEWS EVENTS only. Include:
- New contracts, deals, project wins (especially malls, airports, hospitals)
- Partnerships, acquisitions, mergers, joint ventures
- Product launches (new kiosks, wayfinding software, mobile apps)
- Trade show appearances with NEW products
- Financial results, funding rounds, investment news
- New office openings (especially in MENA/Europe)
- Leadership changes

STRICTLY EXCLUDE (these are NOT news):
- Product catalog pages or sales listings
- Generic company profile descriptions
- Job postings
- Social media posts without real news content
- "About us" pages
- Blog posts that are just general advice (content marketing)
- News about a PERSON named "{competitor_name}" (e.g. "Joseph was hospitalized") unless they are the CEO/Founder of the company. Ensure it is about the COMPANY.

If NONE of the articles contain real news events, respond with: {{"no_relevant_news": true}}

Otherwise, return JSON:

{{
  "news_items": [
    {{
      "event_type": "New Project" | "Investment" | "Product Launch" | "Partnership" | "Leadership Change" | "Market Expansion" | "Financial Performance" | "Other",
      "category": "Product" | "Expansion" | "Pricing" | "General",
      "title": "Clear headline in ENGLISH (max 100 chars)",
      "summary": "2-3 sentence summary in ENGLISH (max 500 chars). Focus on the 'So What?' for a competitor analysis.",
      "threat_level": 1-5,
      "date": "YYYY-MM-DD",
      "source_url": "The actual URL from the article",
      "region": "MENA" | "EUROPE" | "NORTH_AMERICA" | "APAC" | "GLOBAL",
      "details": {{
        "location": "City, Country or null",
        "financial_value": "Amount or null",
        "partners": ["Companies"],
        "products": ["Products"]
      }}
    }}
  ]
}}

Category Guide:
- "Product": New product/feature/hardware launches
- "Expansion": New contracts, new markets, new offices, partnerships, deployments
- "Pricing": Funding rounds, revenue news, financial results, investments
- "General": Leadership changes, trade show appearances, other

Threat Level Guide:
- 1: Routine news, minimal impact
- 2: Minor development
- 3: Moderate competitive move
- 4: Significant threat (e.g. major new mall project in UAE/Saudi)
- 5: Major threat (direct competitor winning a key account or launching a clone product)

CRITICAL: Assign higher threat levels (4-5) for news in MENA (UAE, Saudi Arabia, Qatar) as these are our primary markets.

DATE EXTRACTION INSTRUCTIONS:
- Use the EXACT "Published Date" provided.
- If no date is found, use the current date.
- Return ONLY valid JSON."""


def sanitize_text(text):
    """Remove problematic characters"""
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', str(text))
    replacements = {
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-',
        '\u2026': '...',
        '\u00a0': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    try:
        text = text.encode('ascii', 'ignore').decode('ascii')
    except:
        pass
    return text.strip()


def generate_cuid():
    return 'c' + uuid.uuid4().hex[:24]


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_competitors():
    """Fetch competitors from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, website, industry, region, headquarters
        FROM "Competitor"
        WHERE status = 'active' OR status IS NULL
    """)
    all_competitors = cursor.fetchall()
    conn.close()
    
    def sort_key(c):
        name = c['name']
        if name in PRIORITY_COMPETITORS:
            return (0, PRIORITY_COMPETITORS.index(name))
        else:
            return (1, name)
    
    return sorted(all_competitors, key=sort_key)


def check_existing_url(cursor, url):
    """Check if URL already exists in database"""
    cursor.execute('SELECT id FROM "CompetitorNews" WHERE "sourceUrl" = %s', (url,))
    return cursor.fetchone() is not None


def save_news_item(competitor_id, news_item):
    """Save news item to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    source_url = sanitize_text(news_item.get('source_url', ''))
    
    if not source_url or 'example.com' in source_url:
        conn.close()
        return False, "invalid_url"
    
    if check_existing_url(cursor, source_url):
        conn.close()
        return False, "duplicate_url"

    # Check strict title duplicate (avoid cloning same story from diff URL)
    title_check = sanitize_text(news_item.get('title', 'Untitled'))[:200]
    cursor.execute('SELECT id FROM "CompetitorNews" WHERE "competitorId" = %s AND "title" = %s', (competitor_id, title_check))
    if cursor.fetchone():
        conn.close()
        return False, "duplicate_title"
    
    try:
        news_id = generate_cuid()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        iso_now_str = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        title = sanitize_text(news_item.get('title', 'Untitled'))[:200]
        summary = sanitize_text(news_item.get('summary', ''))[:1000]
        event_type = sanitize_text(news_item.get('event_type', 'Unknown'))[:100]
        region = news_item.get('region', 'GLOBAL')
        
        threat_level = news_item.get('threat_level', 2)
        try:
            threat_level = int(threat_level)
        except:
            threat_level = 2
        threat_level = max(1, min(5, threat_level))
        
        date_str = news_item.get('date', now.strftime('%Y-%m-%d'))
        try:
            # Handle YYYY-MM-DD
            news_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        except:
            news_date = now

        # Cap future dates to today
        if news_date > now:
            news_date = now

        news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        # Skip news before 2025 (Relaxed for Gemini)
        cutoff = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
        if news_date < cutoff:
            # If it's a Gemini item, we trust it might be niche/recent even if date parsing failed or is old
            # But the user said: "default to Current Year" if no year explicits found. 
            # We logic handled that in _parse_gemini_grounding (defaults to today).
            # If we are here, it means we parsed a date < 2025.
            if news_item.get('_search_region') == 'gemini_search':
                print(f" [Warn: Pre-2025 ({news_date.strftime('%Y-%m-%d')}) but Gemini - Keeping]", end="")
                # Force date to today if it's really old? Or just keep it. 
                # User said: "default to 'Current Year' instead of skipping"
                if news_date.year < 2024:
                    news_date = now
                    news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            else:
                conn.close()
                print(f" [Skip: pre_2025 ({news_date.strftime('%Y-%m-%d')})]", end="")
                return False, "pre_2025"
        
        details = news_item.get('details', {})
        if isinstance(details, dict):
            clean_details = {
                'location': sanitize_text(details.get('location', '')),
                'financial_value': sanitize_text(details.get('financial_value', '')),
                'partners': [sanitize_text(p) for p in (details.get('partners') or [])],
                'products': [sanitize_text(p) for p in (details.get('products') or [])]
            }
        else:
            clean_details = {}
        # Store category in details blob — no DB migration required
        category = news_item.get('category', '')
        if category:
            clean_details['category'] = sanitize_text(category)
        details_json = json.dumps(clean_details)
        
        cursor.execute("""
            INSERT INTO "CompetitorNews" (
                id, "competitorId", "eventType", date, title, summary,
                "threatLevel", details, "sourceUrl", "isRead", "isStarred", "extractedAt", region
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            news_id,
            competitor_id,
            event_type,
            news_date_str,
            title,
            summary,
            threat_level,
            details_json,
            source_url,
            False,
            False,
            iso_now_str,
            region
        ))
        
        conn.commit()
        conn.close()
        return True, "saved"
        
    except Exception as e:
        conn.close()
        return False, str(e)


def get_last_fetch_date():
    """Get the date of the most recent news item in the DB"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT MAX("extractedAt") as last_fetch FROM "CompetitorNews"')
        result = cursor.fetchone()
        conn.close()
        if result and result['last_fetch']:
            return result['last_fetch']
    except:
        pass
    return None


def get_all_existing_urls():
    """Fetch all existing source URLs from DB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "sourceUrl" FROM "CompetitorNews"')
    urls = {row['sourceUrl'] for row in cursor.fetchall()}
    conn.close()
    return urls


def search_serper(query, search_type='news', region='global', num_results=10, date_restrict=None, tbs_val=None):
    """Search using Serper.dev API (with 7-day file cache to save credits).
    `region` can be a string key from REGIONS or a native-language dict with gl/hl/_label keys.
    """
    # Normalise: support both string keys and native-language dicts
    if isinstance(region, dict):
        region_config = region
        region_label = region.get('_label', f"{region.get('gl', '?')}_{region.get('hl', '?')}")
    else:
        region_config = REGIONS.get(region, REGIONS['global'])
        region_label = region

    # Check cache first
    cached = _cache_get(query, region_label, search_type)
    if cached is not None:
        print(f"      [CACHED] {region_label}: {query[:60]}")
        return cached

    if not SERPER_API_KEY:
        print("      ERROR: SERPER_API_KEY not set in .env")
        return []

    url = f"https://google.serper.dev/{search_type}"

    payload = {
        "q": query,
        "gl": region_config['gl'],
        "hl": region_config['hl'],
        "num": num_results
    }

    # Add date restriction if provided
    if tbs_val:
        payload["tbs"] = tbs_val
    elif date_restrict:
        payload["tbs"] = f"qdr:{date_restrict}"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 403 or (response.status_code == 400 and "credits" in response.text.lower()):
             print(f"      ❌ ERROR: Serper API credits exhausted! Please check your plan.")
             return []

        response.raise_for_status()
        data = response.json()

        if search_type == 'news':
            results = data.get('news', [])
        else:
            results = data.get('organic', [])

        print(f"      [API]    {region_label}: {query[:60]}")
        _cache_set(query, region_label, search_type, results)
        return results

    except requests.exceptions.RequestException as e:
        print(f"      Serper error: {e}")
        return []


def search_news(competitor_name, regions_to_search=['global', 'mena', 'europe', 'australia'], days_back=None, native_region=None):
    """Search for news about a competitor across multiple regions.
    native_region: optional dict {'gl':..., 'hl':..., '_label':...} for the competitor's home language.
    Native language results are collected separately and always appended (not subject to the 25-cap cutoff).
    """
    all_results = []
    seen_urls = set()
    filtered_count = 0

    # Strip parenthetical annotations like "(Everbridge)" or "(Atrius)" — these are our
    # internal notes, not the real company name used in news articles.
    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()

    queries = [
        f'"{search_name}" contract OR deal OR partnership OR launch OR expansion',
        f'"{search_name}" mall OR airport OR hospital OR university',
        f'"{search_name}" wayfinding OR "digital signage" OR kiosk',
        f'"{search_name}" "virtual assistant" OR "directory" OR screens',
    ]

    today_str = datetime.datetime.now().strftime('%m/%d/%Y')

    # API-side date filtering (tbs)
    tbs_val = None
    if days_back:
        if days_back <= 1:
            tbs_val = "qdr:d"
        elif days_back <= 7:
            tbs_val = "qdr:w"
        elif days_back <= 30:
            tbs_val = "qdr:m"
        elif days_back <= 365:
            tbs_val = "qdr:y"

    def _collect(region_key, results_list):
        for r in results_list:
            url = r.get('link', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                if is_news_url(url):
                    r['_search_region'] = region_key if isinstance(region_key, str) else (region_key.get('_label', 'native'))
                    all_results.append(r)
                else:
                    filtered_count_ref[0] += 1

    filtered_count_ref = [0]

    # Standard English-language region searches (capped at 25)
    for region in regions_to_search:
        for query in queries:
            results = search_serper(query, search_type='news', region=region, num_results=10, tbs_val=tbs_val)
            _collect(region, results)
            if len(all_results) >= 25:
                break
        if len(all_results) >= 25:
            break

    # Native language search — always runs, results appended after English ones
    if native_region:
        native_label = native_region.get('_label', 'native')
        for query in queries:
            results = search_serper(query, search_type='news', region=native_region, num_results=10, tbs_val=tbs_val)
            _collect(native_label, results)

    filtered_count = filtered_count_ref[0]
    if filtered_count > 0:
        print(f" ({filtered_count} filtered)", end="")

    return all_results


async def gather_all_articles(competitor, days_back, regions):
    """Run Serper + Gemini in parallel; apply niche deep-search fallback if Serper returns 0."""
    name = competitor['name']
    headquarters = competitor.get('headquarters') or ''
    website = competitor.get('website') or ''
    native_region = get_native_region(headquarters)

    serper_task = search_news_async(name, regions, days_back=days_back, native_region=native_region)
    gemini_task = search_gemini_async(name, days_back=days_back or 7)
    deep_task = None
    if website:
        deep_task = search_gemini_deep_async(name, website, days_back=days_back or 14)

    results = await asyncio.gather(
        serper_task, gemini_task, deep_task if deep_task else asyncio.sleep(0),
        return_exceptions=True
    )
    
    serper_results = results[0]
    gemini_results = results[1]
    deep_results = results[2] if deep_task else []

    if isinstance(serper_results, Exception):
        print(f"      Serper error: {serper_results}")
        serper_results = []
    if isinstance(gemini_results, Exception):
        print(f"      Gemini error: {gemini_results}")
        gemini_results = []
    if isinstance(deep_results, Exception):
        print(f"      Gemini Deep error: {deep_results}")
        deep_results = []

    # Merge deep results into gemini_results
    if deep_results:
        deep_urls = {a['link'] for a in gemini_results}
        for a in deep_results:
            if a['link'] not in deep_urls:
                gemini_results.append(a)

    # Deduplicate by URL — Serper results take priority (appear first)
    seen = set()
    merged = []
    for a in serper_results + gemini_results:
        url = a.get('link', '')
        if url and url not in seen:
            seen.add(url)
            merged.append(a)
    return merged


async def analyze_with_claude_async(competitor_name, articles, days_back=None):
    """Async Claude analysis using AsyncAnthropic — same batch/retry logic as sync version."""
    if not articles or not ANTHROPIC_API_KEY:
        return None

    BATCH_SIZE = 12
    all_news_items = []
    async_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    for batch_start in range(0, len(articles), BATCH_SIZE):
        batch = articles[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE

        if total_batches > 1:
            print(f"      [batch {batch_num}/{total_batches}]", end="")

        articles_text = ""
        for i, article in enumerate(batch, 1):
            title = sanitize_text(article.get('title', 'No title'))
            snippet = sanitize_text(article.get('snippet', article.get('description', '')))
            url = article.get('link', article.get('url', ''))
            date = article.get('date', 'Unknown')
            region = article.get('_search_region', 'global').upper()
            articles_text += f"\n---\nArticle {i}:\nTitle: {title}\nPublished Date: {date}\nURL: {url}\nRegion Found: {region}\nContent: {snippet[:500]}\n---\n"

        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        date_instr = ""
        if days_back:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)
            date_instr = f"CRITICAL: IGNORE any news events that occurred before {cutoff.strftime('%Y-%m-%d')}. Only include news from the last {days_back} days."

        prompt = ANALYSIS_PROMPT.format(
            competitor_name=competitor_name,
            articles=articles_text,
            today_date=today_str,
            date_instruction=date_instr
        )

        for attempt in range(3):
            try:
                message = await async_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = message.content[0].text.strip()

                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                response_text = response_text.strip()

                result = None
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    for fix in ['}]}', ']}', '}']:
                        try:
                            result = json.loads(response_text + fix)
                            print(" (recovered)", end="")
                            break
                        except json.JSONDecodeError:
                            continue
                    if result is None:
                        m = re.search(r'\{[\s\S]*\}', response_text)
                        if m:
                            try:
                                result = json.loads(m.group())
                                print(" (regex-extracted)", end="")
                            except json.JSONDecodeError:
                                pass

                if result is None:
                    if attempt < 2:
                        continue
                    print(" JSON fail", end="")
                    break

                if not result.get('no_relevant_news'):
                    items = result.get('news_items', [])
                    # Re-attach _search_region from input articles
                    url_map = {a.get('link', ''): a.get('_search_region') for a in batch}
                    for item in items:
                        src = item.get('source_url', '')
                        if src in url_map:
                            item['_search_region'] = url_map[src]
                    
                    all_news_items.extend(items)
                    if total_batches > 1:
                        print(f" → {len(items)} items")
                else:
                    if total_batches > 1:
                        print(f" → 0 items")
                        # Debug: Check if deep search items were dropped
                        gemini_count = sum(1 for a in batch if 'gemini' in a.get('_search_region', '').lower())
                        if gemini_count > 0:
                            print(f" (Claude dropped {gemini_count} Gemini items)", end="")
                break

            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    print(f" (Claude failed: {e})", end="")

        if batch_start + BATCH_SIZE < len(articles):
            await asyncio.sleep(0.5)

    return {'news_items': all_news_items} if all_news_items else {'no_relevant_news': True}


def analyze_with_claude(competitor_name, articles, days_back=None):
    """Send articles to Claude for analysis"""
    if not articles:
        return None
    
    if not ANTHROPIC_API_KEY:
        print("      ERROR: ANTHROPIC_API_KEY not set in .env")
        return None
    
    BATCH_SIZE = 12
    all_news_items = []
    
    for batch_start in range(0, len(articles), BATCH_SIZE):
        batch = articles[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE
        
        if total_batches > 1:
            print(f"      [batch {batch_num}/{total_batches}]", end="")
        
        articles_text = ""
        for i, article in enumerate(batch, 1):
            title = sanitize_text(article.get('title', 'No title'))
            snippet = sanitize_text(article.get('snippet', article.get('description', '')))
            url = article.get('link', article.get('url', ''))
            date = article.get('date', 'Unknown')
            region = article.get('_search_region', 'global').upper()
            
            articles_text += f"""
---
Article {i}:
Title: {title}
Published Date: {date}
URL: {url}
Region Found: {region}
Content: {snippet[:500]}
---
"""
        
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        date_instr = ""
        if days_back:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)
            cutoff_str = cutoff.strftime('%Y-%m-%d')
            date_instr = f"CRITICAL: IGNORE any news events that occurred before {cutoff_str}. Only include news from the last {days_back} days (since {cutoff_str})."

        prompt = ANALYSIS_PROMPT.format(
            competitor_name=competitor_name,
            articles=articles_text,
            today_date=today_str,
            date_instruction=date_instr
        )
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                import httpx
                http_client = httpx.Client(timeout=60.0)
                retry_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, http_client=http_client)

                message = retry_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=8000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                response_text = message.content[0].text.strip()

                # Extract JSON from code blocks
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                response_text = response_text.strip()

                # Try to find JSON object/array using regex if direct parse fails
                result = None
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    # Try appending common truncation fixes
                    for fix in ['}]}', ']}', '}']:
                        try:
                            result = json.loads(response_text + fix)
                            print(" (recovered)", end="")
                            break
                        except json.JSONDecodeError:
                            continue
                    # Last resort: extract JSON block with regex
                    if result is None:
                        json_match = re.search(r'\{[\s\S]*\}', response_text)
                        if json_match:
                            try:
                                result = json.loads(json_match.group())
                                print(" (regex-extracted)", end="")
                            except json.JSONDecodeError:
                                pass
                
                if result is None:
                    if attempt < max_retries - 1:
                        continue  # Retry on JSON parse failure
                    print(f" JSON fail", end="")
                    break
                
                if not result.get('no_relevant_news'):
                    batch_items = result.get('news_items', [])
                    all_news_items.extend(batch_items)
                    if total_batches > 1:
                        print(f" → {len(batch_items)} items")
                else:
                    if total_batches > 1:
                        print(f" → 0 items")
                
                break # Success, break retry loop
                
            except (anthropic.APIError, httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    print(f" (emit retry {attempt+1})", end="")
                    time.sleep(2 * (attempt + 1))
                else:
                    print(f" (API failed: {e})", end="")
            except Exception as e:
                print(f" (Err: {e})", end="")
                break
        
        if batch_start + BATCH_SIZE < len(articles):
            time.sleep(0.5)
    
    if not all_news_items:
        return {'no_relevant_news': True}
    
    return {'news_items': all_news_items}


def fetch_news_for_competitor(competitor, regions=['global', 'mena', 'europe'], existing_urls=None, days_back=None):
    """Fetch and analyze news for one competitor"""
    comp_id = competitor['id']
    name = competitor['name']
    headquarters = competitor.get('headquarters') or ''

    # Determine native language region based on HQ country
    native_region = get_native_region(headquarters)
    if native_region:
        print(f"\n  🔍 {name} [{native_region['_label']}]", end="")
    else:
        print(f"\n  🔍 {name}", end="")

    articles = search_news(name, regions, days_back=days_back, native_region=native_region)

    # Gemini search — runs in parallel, merges unique URLs not already found by Serper
    gemini_articles = search_gemini(name, days_back=days_back or 7)
    seen_links = {a.get('link', '') for a in articles}
    for a in gemini_articles:
        if a.get('link', '') not in seen_links:
            seen_links.add(a['link'])
            articles.append(a)

    if not articles:
        print(f" — no articles")
        return 0

    if existing_urls:
        new_articles = [a for a in articles if a.get('link', '') not in existing_urls]
        skipped = len(articles) - len(new_articles)
        if skipped > 0:
            print(f" — {len(articles)} found, {skipped} known", end="")
        if not new_articles:
            print(f" — all double, skip")
            return 0
        articles = new_articles
    
    print(f" — {len(articles)} new...", end="")
    
    analysis = analyze_with_claude(name, articles, days_back=days_back)
    
    if not analysis:
        # print(f" (failed)")
        return 0
    
    if analysis.get('no_relevant_news'):
        # print(f" (none relevant)")
        return 0
    
    news_items = analysis.get('news_items', [])
    saved = 0
    
    for item in news_items:
        success, status = save_news_item(comp_id, item)
        if success:
            saved += 1
        else:
            print(f" [Skip: {status}]", end="")
    
    if saved > 0:
        print(f" ✅ Saved {saved}", end="")
    else:
        print(f" (0 saved)", end="")
        
    return saved


async def fetch_news_for_competitor_async(competitor, regions, existing_urls=None, days_back=None):
    """Async version of fetch_news_for_competitor — uses parallel Serper+Gemini."""
    name = competitor['name']
    headquarters = competitor.get('headquarters') or ''
    native_region = get_native_region(headquarters)

    if native_region:
        print(f"\n  🔍 {name} [{native_region['_label']}]", end="")
    else:
        print(f"\n  🔍 {name}", end="")

    articles = await gather_all_articles(competitor, days_back, regions)

    if not articles:
        print(" — no articles")
        return 0

    if existing_urls:
        new_articles = [a for a in articles if a.get('link', '') not in existing_urls]
        skipped = len(articles) - len(new_articles)
        if skipped > 0:
            print(f" — {len(articles)} found, {skipped} known", end="")
        if not new_articles:
            print(" — all known, skip")
            return 0
        articles = new_articles

    print(f" — {len(articles)} new...", end="")

    analysis = await analyze_with_claude_async(name, articles, days_back=days_back)

    if not analysis or analysis.get('no_relevant_news'):
        return 0

    news_items = analysis.get('news_items', [])
    saved = 0
    for item in news_items:
        success, status = await asyncio.to_thread(save_news_item, competitor['id'], item)
        if success:
            saved += 1
        else:
            print(f" [Skip: {status}]", end="")

    if saved > 0:
        print(f" ✅ Saved {saved}", end="")
    else:
        print(f" (0 saved)", end="")
    return saved


async def _fetch_all_news_async_inner(limit=None, clean_start=False, regions=None, days=None, competitor_name=None):
    """Async core of fetch_all_news — processes competitors in batches of 5."""
    print("=" * 60)
    print("🎯 ABUZZ INTELLIGENCE FETCHER (v2.1 - Parallel)")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found")
        write_status('error', error='ANTHROPIC_API_KEY not found')
        return 0

    if regions is None:
        regions = ['global', 'mena', 'europe']

    if clean_start:
        deleted = await asyncio.to_thread(clear_all_news)
        print(f"\n🧹 Cleared {deleted} entries")

    search_days = None
    if days:
        search_days = days
        print(f"\n📅 Last {days} days")
    elif not clean_start:
        last_fetch = await asyncio.to_thread(get_last_fetch_date)
        if last_fetch:
            if isinstance(last_fetch, str):
                last_fetch = datetime.datetime.fromisoformat(last_fetch.replace('Z', '+00:00'))
            if last_fetch.tzinfo is None:
                last_fetch = last_fetch.replace(tzinfo=datetime.timezone.utc)
            days_since = (datetime.datetime.now(datetime.timezone.utc) - last_fetch).days
            search_days = min(max(days_since + 1, 1), 14)
            print(f"\n📅 Auto-range: last {search_days} days")
        else:
            print(f"\n📅 Full history")

    print("📦 Loading URLs...")
    existing_urls = await asyncio.to_thread(get_all_existing_urls)
    print(f"   {len(existing_urls)} known URLs")

    competitors = await asyncio.to_thread(get_competitors)

    if competitor_name:
        competitors = [c for c in competitors if competitor_name.lower() in c['name'].lower()]
        if not competitors:
            print(f"❌ No competitor found matching '{competitor_name}'")
            return 0
        print(f"🎯 Filtered to: {competitors[0]['name']}")
    else:
        print(f"📋 {len(competitors)} competitors")

    if limit:
        competitors = competitors[:limit]

    total_competitors = len(competitors)
    total_news = 0
    write_status('running', current_competitor=None, processed=0, total=total_competitors)

    BATCH_SIZE = 5  # Gemini Tier 1: ~15 RPM; 5 parallel + 1–3s jitter = safe
    total_batches = (total_competitors + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx, batch_start in enumerate(range(0, total_competitors, BATCH_SIZE)):
        batch = competitors[batch_start:batch_start + BATCH_SIZE]

        if total_batches > 1:
            print(f"\n⚡ Batch {batch_idx + 1}/{total_batches} ({len(batch)} competitors)")

        write_status('running', current_competitor=batch[0]['name'],
                     processed=batch_start, total=total_competitors)

        tasks = [
            fetch_news_for_competitor_async(c, regions, existing_urls=existing_urls, days_back=search_days)
            for c in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, (comp, result) in enumerate(zip(batch, results)):
            idx = batch_start + i + 1
            if isinstance(result, Exception):
                print(f"\n  ❌ {comp['name']}: {result}")
                result = 0
            total_news += result
            write_status('running', current_competitor=comp['name'],
                         processed=idx, total=total_competitors)

        # Inter-batch cooldown — prevents Gemini burst at batch boundaries
        if batch_start + BATCH_SIZE < total_competitors:
            delay = random.uniform(3.0, 6.0)
            print(f"\n  ⏳ Cooling down {delay:.1f}s before next batch...")
            await asyncio.sleep(delay)

    write_status('completed', processed=total_competitors, total=total_competitors)
    print("\n" + "=" * 60)
    print(f"✅ COMPLETE: {total_news} items added")
    print("=" * 60)
    return total_news


def write_status(status, current_competitor=None, processed=0, total=0, error=None):
    """Write progress status to JSON file"""
    import time
    import datetime

    percent_complete = 0
    if total > 0:
        percent_complete = int((processed / total) * 100)

    estimated_seconds_remaining = (total - processed) * 20

    status_data = {
        'status': status,
        'current_competitor': current_competitor,
        'processed': processed,
        'total': total,
        'percent_complete': percent_complete,
        'estimated_seconds_remaining': estimated_seconds_remaining,
        'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat() if status == 'running' and processed == 0 else None,
        'completed_at': datetime.datetime.now(datetime.timezone.utc).isoformat() if status == 'completed' else None,
        'error': error
    }

    status_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'public', 'refresh_status.json')
    try:
        os.makedirs(os.path.dirname(status_path), exist_ok=True)
        with open(status_path, 'w') as f:
            json.dump(status_data, f, indent=2)
            f.flush()
    except:
        pass

    return status_data


def clear_all_news():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM "CompetitorNews"')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def fetch_all_news(limit=None, clean_start=False, regions=None, days=None, competitor_name=None):
    """Main entry point — thin sync wrapper around the async implementation."""
    if regions is None:
        regions = ['global', 'mena', 'europe']
    return asyncio.run(_fetch_all_news_async_inner(
        limit=limit,
        clean_start=clean_start,
        regions=regions,
        days=days,
        competitor_name=competitor_name,
    ))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int)
    parser.add_argument('--skip', type=int, default=0)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--region', type=str)
    parser.add_argument('--mena', action='store_true')
    parser.add_argument('--days', type=int)
    parser.add_argument('--competitor', type=str, help='Fetch news for a single competitor (partial name match)')
    args = parser.parse_args()

    regions = ['global', 'mena', 'europe']
    if args.region:
        regions = [args.region]
    elif args.mena:
        regions = ['mena', 'global']

    if args.test:
        fetch_all_news(limit=3, clean_start=True, regions=regions, days=args.days)
    elif args.limit:
        fetch_all_news(limit=args.limit, clean_start=args.clean, regions=regions, days=args.days, competitor_name=args.competitor)
    else:
        fetch_all_news(clean_start=args.clean, regions=regions, days=args.days, competitor_name=args.competitor)