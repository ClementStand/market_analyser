"""
News Fetcher for Competitor Intelligence Platform
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
import urllib.parse
import anthropic
from google import genai as google_genai
from google.genai import types as genai_types
from dotenv import load_dotenv

# Load .env.local first, then .env as fallback
load_dotenv('.env.local')
load_dotenv()

try:
    import config
except ImportError:
    # Fallback if running from root
    from scripts import config


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
        # Process list items: bullets (*, -) and numbered items (1., 2., etc.)
        is_list_item = (
            line_clean.startswith('*') or
            line_clean.startswith('-') or
            bool(re.match(r'^\d+[\.\)]\s', line_clean))
        )
        if not is_list_item:
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
                                 if uri:
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
             
             # Clean snippet: remove bullets, numbered markers, and bold formatting
             snippet = re.sub(r'^[\*\-]\s*', '', line_clean)
             snippet = re.sub(r'^\d+[\.\)]\s*', '', snippet)
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


def search_gemini(competitor_name, days_back=7, industry_context=None):
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

    focus_areas = "new contracts, partnerships, product launches, funding rounds, office openings, leadership changes, market expansion"
    if industry_context:
        focus_areas += f", {industry_context}"

    try:
        prompt = (
            f"Search for news articles published in the last {days_back} days about "
            f"the company '{search_name}'. Focus on: {focus_areas}. "
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


async def search_news_async(competitor_name, regions_to_search, days_back=None, native_region=None, industry_keywords=None, website=None):
    """Async version — fires ALL (query × region) Serper combinations concurrently."""
    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()
    queries = []

    # Base topics (contract, launch, financial, etc.)
    for topic in config.DEFAULT_SEARCH_TOPICS:
        queries.append(f'"{search_name}" {topic}')

    # Industry-specific keywords — prefer org-specific, fall back to global config
    kws = industry_keywords if industry_keywords else config.INDUSTRY_KEYWORDS
    if kws:
        # Group keywords into chunks of 3-4 to avoid massive queries
        chunk_size = 4
        for i in range(0, len(kws), chunk_size):
            chunk = kws[i:i+chunk_size]
            joined = " OR ".join([f'"{k}"' for k in chunk])
            queries.append(f'"{search_name}" {joined}')

    # Domain-scoped queries to reduce homonym noise
    if website:
        domain = re.sub(r'^https?://', '', website).rstrip('/')
        for topic in config.DEFAULT_SEARCH_TOPICS:
            queries.append(f'"{search_name}" {topic} site:{domain}')

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


async def search_gemini_async(competitor_name, days_back=7, industry_context=None):
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

    focus_areas = "new contracts, partnerships, product launches, funding rounds, office openings, leadership changes, market expansion"
    if industry_context:
        focus_areas += f", {industry_context}"

    try:
        prompt = (
            f"Your goal is to find specific, high-value business news about '{search_name}' from the last {days_back} days.\n"
            f"Use the Google Search tool with multiple specific queries. Do NOT just search for generic terms.\n"
            f"SUGGESTED QUERIES (execute these):\n"
            f"- '{search_name} press release'\n"
            f"- '{search_name} CEO'\n"
            f"- '{search_name} contract'\n"
            f"- '{search_name} partnership'\n"
            f"- '{search_name} new product'\n"
            f"- '{search_name} blog'\n"
            f"IMPORTANT: Do NOT add 'last {days_back} days' to the search query string itself, as it confuses the search engine. Just check the dates of the results.\n"
            f"Focus on: {focus_areas}.\n"
            f"Return a bulleted list (use - for each item) of every article found, with its date and a brief description."
        )
        response = await _gemini_client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
            )
        )
        articles = _parse_gemini_grounding(response)
        if not articles:
            print(f"      [GEMINI-DEBUG] No articles extracted. Raw Text:\n{response.text}")
            try:
                print(f"      [GEMINI-DEBUG] Grounding Metadata: {response.candidates[0].grounding_metadata}")
            except:
                pass
        
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


# Use config for regions
REGIONS = config.REGIONS
HQ_NATIVE_REGIONS = config.HQ_NATIVE_REGIONS
ENGLISH_SPEAKING_HQ = config.ENGLISH_SPEAKING_HQ



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


async def validate_urls_async(articles, timeout=5.0, max_concurrent=10):
    """HEAD-request each article URL. Discard 404/500 and root-only paths (fail-open on timeout)."""
    from urllib.parse import urlparse
    semaphore = asyncio.Semaphore(max_concurrent)

    # Root-only paths that indicate a generic page, not a specific article
    GENERIC_PATHS = {'', '/', '/blog', '/blog/', '/news', '/news/', '/press', '/press/',
                     '/media', '/media/', '/insights', '/insights/', '/resources', '/resources/'}

    async def check_one(article):
        url = article.get('link', '')
        if not url:
            return None

        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if path in GENERIC_PATHS or path == '':
            return None

        try:
            async with semaphore:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    resp = await client.head(url)
                    if resp.status_code >= 400:
                        return None
        except (httpx.TimeoutException, httpx.ConnectError, Exception):
            # Fail-open: keep the article if we can't reach the server
            pass
        return article

    tasks = [check_one(a) for a in articles]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if r is not None and not isinstance(r, Exception)]


# Use config for regions
# Fix: Escape braces for .format()
ANALYSIS_PROMPT = config.ANALYSIS_PROMPT_TEMPLATE



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


def get_organization(org_id):
    """Fetch organization details from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, industry, keywords, regions,
               "vipCompetitors", "priorityRegions"
        FROM "Organization"
        WHERE id = %s
    """, (org_id,))
    org = cursor.fetchone()
    conn.close()
    return org


def get_competitors(org_id=None):
    """Fetch competitors from database, optionally filtered by organization"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if org_id:
        cursor.execute("""
            SELECT id, name, website, industry, region, headquarters
            FROM "Competitor"
            WHERE (status = 'active' OR status IS NULL)
            AND "organizationId" = %s
        """, (org_id,))
    else:
        cursor.execute("""
            SELECT id, name, website, industry, region, headquarters
            FROM "Competitor"
            WHERE status = 'active' OR status IS NULL
        """)
    all_competitors = cursor.fetchall()
    conn.close()

    return sorted(all_competitors, key=lambda c: c['name'])


def check_existing_url(cursor, url):
    """Check if URL already exists in database"""
    cursor.execute('SELECT id FROM "CompetitorNews" WHERE "sourceUrl" = %s', (url,))
    return cursor.fetchone() is not None


def save_news_item(competitor_id, news_item, conn=None, max_age_days=None):
    """Save news item to database. Accepts an optional shared connection to avoid
    opening a new connection per item. max_age_days rejects articles older than N days."""
    owns_conn = conn is None
    if owns_conn:
        conn = get_db_connection()
    cursor = conn.cursor()

    source_url = sanitize_text(news_item.get('source_url', ''))

    if not source_url or 'example.com' in source_url:
        if owns_conn:
            conn.close()
        return False, "invalid_url"

    if check_existing_url(cursor, source_url):
        if owns_conn:
            conn.close()
        return False, "duplicate_url"

    # Check strict title duplicate (avoid cloning same story from diff URL)
    title_check = sanitize_text(news_item.get('title', 'Untitled'))[:200]
    cursor.execute('SELECT id FROM "CompetitorNews" WHERE "competitorId" = %s AND "title" = %s', (competitor_id, title_check))
    if cursor.fetchone():
        if owns_conn:
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

        impact_score = news_item.get('impact_score')
        try:
            impact_score = int(impact_score) if impact_score is not None else None
        except:
            impact_score = None
        if impact_score is not None:
            impact_score = max(0, min(100, impact_score))

        date_str = news_item.get('date', now.strftime('%Y-%m-%d'))
        try:
            news_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        except:
            news_date = now

        # Cap future dates to today
        if news_date > now:
            news_date = now

        news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        # Skip articles older than max_age_days (e.g. 14 days for "Search News 2 weeks")
        if max_age_days:
            min_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_age_days)
            if news_date < min_date:
                if owns_conn:
                    conn.close()
                print(f" [Skip: too_old ({news_date.strftime('%Y-%m-%d')}, max {max_age_days}d)]", end="")
                return False, "too_old"

        # Skip news before configured cutoff
        cutoff = config.DEFAULT_DATE_CUTOFF
        if news_date < cutoff:
            if news_item.get('_search_region') == 'gemini_search':
                print(f" [Warn: Pre-2025 ({news_date.strftime('%Y-%m-%d')}) but Gemini - Keeping]", end="")
                if news_date.year < 2024:
                    news_date = now
                    news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            else:
                if owns_conn:
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
        category = news_item.get('category', '')
        if category:
            clean_details['category'] = sanitize_text(category)
        details_json = json.dumps(clean_details)

        cursor.execute("""
            INSERT INTO "CompetitorNews" (
                id, "competitorId", "eventType", date, title, summary,
                "threatLevel", "impactScore", details, "sourceUrl", "isRead", "isStarred", "extractedAt", region
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            news_id,
            competitor_id,
            event_type,
            news_date_str,
            title,
            summary,
            threat_level,
            impact_score,
            details_json,
            source_url,
            False,
            False,
            iso_now_str,
            region
        ))

        conn.commit()
        if owns_conn:
            conn.close()
        return True, "saved"

    except Exception as e:
        if owns_conn:
            conn.close()
        return False, str(e)


def get_last_fetch_date(org_id=None):
    """Get the date of the most recent news item in the DB, optionally for an org"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if org_id:
            cursor.execute("""
                SELECT MAX(cn."extractedAt") as last_fetch
                FROM "CompetitorNews" cn
                JOIN "Competitor" c ON cn."competitorId" = c.id
                WHERE c."organizationId" = %s
            """, (org_id,))
        else:
            cursor.execute('SELECT MAX("extractedAt") as last_fetch FROM "CompetitorNews"')
        result = cursor.fetchone()
        conn.close()
        if result and result['last_fetch']:
            return result['last_fetch']
    except:
        pass
    return None


def get_all_existing_urls(org_id=None):
    """Fetch all existing source URLs from DB, optionally for an org"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if org_id:
        cursor.execute("""
            SELECT cn."sourceUrl"
            FROM "CompetitorNews" cn
            JOIN "Competitor" c ON cn."competitorId" = c.id
            WHERE c."organizationId" = %s
        """, (org_id,))
    else:
        cursor.execute('SELECT "sourceUrl" FROM "CompetitorNews"')
    urls = {row['sourceUrl'] for row in cursor.fetchall()}
    conn.close()
    return urls


def get_recent_titles(competitor_id, days=5):
    """Fetch titles of recent news items for a competitor (for dedup context)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days))
    cutoff_str = cutoff.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    cursor.execute("""
        SELECT title, "eventType", date
        FROM "CompetitorNews"
        WHERE "competitorId" = %s AND date >= %s
        ORDER BY date DESC
        LIMIT 30
    """, (competitor_id, cutoff_str))
    rows = cursor.fetchall()
    conn.close()
    return rows


async def gather_all_articles(competitor, days_back, regions, industry_keywords=None, industry_context=None):
    """Run Serper + Gemini in parallel; apply niche deep-search fallback if Serper returns 0."""
    name = competitor['name']
    headquarters = competitor.get('headquarters') or ''
    website = competitor.get('website') or ''
    native_region = get_native_region(headquarters)

    serper_task = search_news_async(name, regions, days_back=days_back, native_region=native_region, industry_keywords=industry_keywords, website=website)
    gemini_task = search_gemini_async(name, days_back=days_back or 7, industry_context=industry_context)
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

    # Validate URLs (async HEAD requests) — discard 404s and generic pages
    pre_validation_count = len(merged)
    merged = await validate_urls_async(merged)
    validated_out = pre_validation_count - len(merged)
    if validated_out > 0:
        print(f" ({validated_out} failed URL validation)", end="")

    # FALLBACK SEARCH: If strict queries yielded absolutely nothing, do a broad "name merely mentioned" search
    if not merged:
        print(f" [Loosening constraints]...", end="")
        fallback = await search_serper_async(name, 'news', 'global', 5)
        if fallback:
            for r in fallback:
                 if is_news_url(r.get('link', '')):
                     r['_search_region'] = 'fallback'
                     merged.append(r)
            merged = await validate_urls_async(merged)

    return merged


async def analyze_with_claude_async(competitor_name, articles, days_back=None, company_name=None, industry=None,
                                     recent_titles=None, vip_competitors=None, priority_regions=None):
    """Async Claude analysis using AsyncAnthropic — same batch/retry logic as sync version."""
    if not articles or not ANTHROPIC_API_KEY:
        return None

    # Use org-specific values or fall back to global config
    _company_name = company_name or config.COMPANY_NAME
    _industry = industry or config.INDUSTRY

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

        # Build dedup context from recent titles
        dedup_context = ""
        if recent_titles:
            titles_list = "\n".join(
                f"- [{r['eventType']}] {r['title']} ({r['date']})"
                for r in recent_titles[:20]
            )
            dedup_context = (
                f"DEDUPLICATION CONTEXT:\n"
                f"The following articles are ALREADY in our database for {competitor_name}. "
                f"If any of the new search results describe the SAME underlying business event "
                f"(even if from a different source or with a slightly different headline), "
                f"DO NOT include them in your output. Only include genuinely NEW events.\n"
                f"Existing articles:\n{titles_list}"
            )

        # Build dynamic VIP/priority scoring instructions
        vip_instruction = ""
        if vip_competitors and competitor_name in vip_competitors:
            vip_instruction = f"- This competitor ({competitor_name}) is a VIP/high-priority competitor: +20 points to ALL their news items"
        elif vip_competitors:
            vip_instruction = f"- VIP Competitors (add +20 if the news involves any of these): {', '.join(vip_competitors)}"

        priority_instruction = ""
        if priority_regions:
            priority_instruction = f"- Priority Regions (add +20 if the news is in or affects any of these): {', '.join(priority_regions)}"

        prompt = ANALYSIS_PROMPT.format(
            company_name=_company_name,
            industry=_industry,
            competitor_name=competitor_name,
            articles=articles_text,
            today_date=today_str,
            date_instruction=date_instr,
            dedup_context=dedup_context,
            vip_competitor_instruction=vip_instruction,
            priority_region_instruction=priority_instruction
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


async def fetch_news_for_competitor_async(competitor, regions, existing_urls=None, days_back=None,
                                         company_name=None, industry=None, industry_keywords=None, industry_context=None,
                                         vip_competitors=None, priority_regions=None):
    """Async version of fetch_news_for_competitor — uses parallel Serper+Gemini."""
    name = competitor['name']
    headquarters = competitor.get('headquarters') or ''
    native_region = get_native_region(headquarters)

    if native_region:
        print(f"\n  🔍 {name} [{native_region['_label']}]", end="")
    else:
        print(f"\n  🔍 {name}", end="")

    articles = await gather_all_articles(competitor, days_back, regions,
                                         industry_keywords=industry_keywords, industry_context=industry_context)

    if not articles:
        print(" — no articles (triggering fallback)")
        analysis = None # Bypass claude
    else:

        if existing_urls:
            new_articles = [a for a in articles if a.get('link', '') not in existing_urls]
            skipped = len(articles) - len(new_articles)
            if skipped > 0:
                print(f" — {len(articles)} found, {skipped} known", end="")
            if not new_articles:
                print(" — all known, (triggering fallback)")
                analysis = None
            else:
                articles = new_articles

        if articles:
            print(f" — {len(articles)} new...", end="")

            # Fetch recent titles for dedup context
            recent_titles = await asyncio.to_thread(get_recent_titles, competitor['id'], days=5)

            analysis = await analyze_with_claude_async(name, articles, days_back=days_back,
                                                       company_name=company_name, industry=industry,
                                                       recent_titles=recent_titles,
                                                       vip_competitors=vip_competitors,
                                                       priority_regions=priority_regions)

    if not analysis or analysis.get('no_relevant_news'):
        pass # Allow fallback to catch this

    news_items = analysis.get('news_items', []) if analysis else []

    # FALLBACK: Ensure no business receives 0 news articles by salvaging the top raw article if Claude rejected all
    if not news_items and articles:
        # Pick the most "recent" or first raw article
        top_article = articles[0]
        news_items = [{
            'title': sanitize_text(top_article.get('title', f'{name} Update'))[:100],
            'summary': sanitize_text(top_article.get('snippet', top_article.get('description', 'No summary available.')))[:300],
            'date': top_article.get('date', datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')),
            'source_url': top_article.get('link', ''),
            'event_type': 'General Update',
            'threat_level': 1,
            'impact_score': 10,
            '_search_region': top_article.get('_search_region', 'fallback')
        }]

    saved = 0
    # Use a single shared connection for all saves in this competitor batch
    conn = await asyncio.to_thread(get_db_connection)
    try:
        for item in news_items:
            success, status = await asyncio.to_thread(save_news_item, competitor['id'], item, conn, days_back)
            if success:
                saved += 1
            else:
                print(f" [Skip: {status}]", end="")
    finally:
        conn.close()

    if saved > 0:
        print(f" ✅ Saved {saved}", end="")
    else:
        print(f" (0 saved)", end="")
    return saved


async def _fetch_all_news_async_inner(org_id=None, limit=None, clean_start=False, regions=None, days=None, competitor_name=None, job_id=None):
    """Async core of fetch_all_news — processes competitors in batches of 5."""
    print("=" * 60)
    print("🎯 INTELLIGENCE FETCHER (v2.1 - Parallel)")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found")
        write_status('error', error='ANTHROPIC_API_KEY not found', job_id=job_id)
        return 0

    # Load org context if org_id provided
    org = None
    org_company_name = config.COMPANY_NAME
    org_industry = config.INDUSTRY
    org_keywords = config.INDUSTRY_KEYWORDS
    org_industry_context = None

    if org_id:
        org = await asyncio.to_thread(get_organization, org_id)
        if org:
            org_company_name = org.get('name') or config.COMPANY_NAME
            org_industry = org.get('industry') or config.INDUSTRY
            org_keywords = org.get('keywords') or config.INDUSTRY_KEYWORDS
            if isinstance(org_keywords, str):
                org_keywords = [k.strip() for k in org_keywords.split(',') if k.strip()]
            # Build industry context string for Gemini prompts
            if org_industry:
                org_industry_context = f"developments in the {org_industry} industry"
            print(f"\n🏢 Organization: {org_company_name} ({org_industry})")

    # Extract VIP/priority config for impact scoring
    org_vip_competitors = []
    org_priority_regions = []
    if org:
        org_vip_competitors = org.get('vipCompetitors') or []
        org_priority_regions = org.get('priorityRegions') or []
        if isinstance(org_vip_competitors, str):
            org_vip_competitors = [v.strip() for v in org_vip_competitors.split(',') if v.strip()]
        if isinstance(org_priority_regions, str):
            org_priority_regions = [r.strip() for r in org_priority_regions.split(',') if r.strip()]
        else:
            print(f"\n⚠️  Organization {org_id} not found, using defaults")

    if regions is None:
        # Use org regions if available, else default
        if org and org.get('regions'):
            org_regions = org['regions']
            if isinstance(org_regions, str):
                org_regions = [r.strip().lower().replace(' ', '_') for r in org_regions.split(',')]
            # Map region names to config keys
            region_map = {
                'global': 'global', 'north_america': 'north_america', 'north america': 'north_america',
                'europe': 'europe', 'mena': 'mena', 'apac': 'apac',
                'south_america': 'global',  # fallback
            }
            regions = []
            for r in org_regions:
                r_lower = r.lower().replace(' ', '_')
                mapped = region_map.get(r_lower)
                if mapped and mapped not in regions:
                    regions.append(mapped)
            if not regions:
                regions = ['global']
            # Always include global
            if 'global' not in regions:
                regions.insert(0, 'global')
        else:
            regions = ['global', 'mena', 'europe']

    print(f"🌍 Regions: {', '.join(regions)}")

    if clean_start:
        deleted = await asyncio.to_thread(clear_all_news)
        print(f"\n🧹 Cleared {deleted} entries")

    search_days = None
    if days:
        search_days = days
        print(f"\n📅 Last {days} days")
    elif not clean_start:
        last_fetch = await asyncio.to_thread(get_last_fetch_date, org_id)
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
    existing_urls = await asyncio.to_thread(get_all_existing_urls, org_id)
    print(f"   {len(existing_urls)} known URLs")

    competitors = await asyncio.to_thread(get_competitors, org_id)

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
    write_status('running', current_competitor=None, processed=0, total=total_competitors, job_id=job_id)

    BATCH_SIZE = 5  # Gemini Tier 1: ~15 RPM; 5 parallel + 1–3s jitter = safe
    total_batches = (total_competitors + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx, batch_start in enumerate(range(0, total_competitors, BATCH_SIZE)):
        batch = competitors[batch_start:batch_start + BATCH_SIZE]

        if total_batches > 1:
            print(f"\n⚡ Batch {batch_idx + 1}/{total_batches} ({len(batch)} competitors)")

        write_status('running', current_competitor=batch[0]['name'],
                     processed=batch_start, total=total_competitors, job_id=job_id)

        tasks = [
            fetch_news_for_competitor_async(
                c, regions, existing_urls=existing_urls, days_back=search_days,
                company_name=org_company_name, industry=org_industry,
                industry_keywords=org_keywords, industry_context=org_industry_context,
                vip_competitors=org_vip_competitors, priority_regions=org_priority_regions
            )
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
                         processed=idx, total=total_competitors, job_id=job_id)

        # Inter-batch cooldown — prevents Gemini burst at batch boundaries
        if batch_start + BATCH_SIZE < total_competitors:
            delay = random.uniform(3.0, 6.0)
            print(f"\n  ⏳ Cooling down {delay:.1f}s before next batch...")
            await asyncio.sleep(delay)

    write_status('completed', processed=total_competitors, total=total_competitors, job_id=job_id)
    print("\n" + "=" * 60)
    print(f"✅ COMPLETE: {total_news} items added")
    print("=" * 60)
    return total_news


def write_status(status, current_competitor=None, processed=0, total=0, error=None, job_id=None):
    """Write progress status to FetchJob table in DB (for Supabase Realtime).
    Falls back to local JSON file if no job_id is provided."""

    if job_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            cursor.execute("""
                UPDATE "FetchJob"
                SET status = %s,
                    "currentStep" = %s,
                    processed = %s,
                    total = %s,
                    error = %s,
                    "updatedAt" = %s
                WHERE id = %s
            """, (status, current_competitor, processed, total, error, now, job_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"      [Status DB write error: {e}]")
    else:
        # Fallback: write to local JSON file (for local dev / CLI usage)
        percent_complete = 0
        if total > 0:
            percent_complete = int((processed / total) * 100)

        status_data = {
            'status': status,
            'current_competitor': current_competitor,
            'processed': processed,
            'total': total,
            'percent_complete': percent_complete,
            'estimated_seconds_remaining': (total - processed) * 20,
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


def create_fetch_job(org_id):
    """Create a FetchJob record and return its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    job_id = generate_cuid()
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    cursor.execute("""
        INSERT INTO "FetchJob" (id, "organizationId", status, processed, total, "createdAt", "updatedAt")
        VALUES (%s, %s, 'pending', 0, 0, %s, %s)
    """, (job_id, org_id, now, now))
    conn.commit()
    conn.close()
    return job_id


def clear_all_news():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM "CompetitorNews"')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def fetch_all_news(org_id=None, limit=None, clean_start=False, regions=None, days=None, competitor_name=None, job_id=None):
    """Main entry point — thin sync wrapper around the async implementation."""
    if regions is None and not org_id:
        regions = ['global', 'mena', 'europe']
    return asyncio.run(_fetch_all_news_async_inner(
        org_id=org_id,
        limit=limit,
        clean_start=clean_start,
        regions=regions,
        days=days,
        competitor_name=competitor_name,
        job_id=job_id,
    ))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--org-id', type=str, help='Organization ID (required for multi-tenant)')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--skip', type=int, default=0)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--region', type=str)
    parser.add_argument('--mena', action='store_true')
    parser.add_argument('--days', type=int)
    parser.add_argument('--competitor', type=str, help='Fetch news for a single competitor (partial name match)')
    args = parser.parse_args()

    regions = None  # Will be auto-detected from org
    if args.region:
        regions = [args.region]
    elif args.mena:
        regions = ['mena', 'global']

    if args.test:
        fetch_all_news(org_id=args.org_id, limit=3, clean_start=True, regions=regions, days=args.days)
    elif args.limit:
        fetch_all_news(org_id=args.org_id, limit=args.limit, clean_start=args.clean, regions=regions, days=args.days, competitor_name=args.competitor)
    else:
        fetch_all_news(org_id=args.org_id, clean_start=args.clean, regions=regions, days=args.days, competitor_name=args.competitor)