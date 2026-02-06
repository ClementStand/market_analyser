"""
News Fetcher for Abuzz Competitor Intelligence
Uses Serper.dev (Google Search API) + Claude AI (Anthropic) for analysis
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import json
import os
import time
import uuid
import re
import requests
import anthropic
from dotenv import load_dotenv

# Load .env.local first, then .env as fallback
load_dotenv('.env.local')
load_dotenv()

# Configure APIs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
# Get database URL - prefer pooler connection, strip Prisma-specific params
_raw_db_url = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL")
DATABASE_URL = _raw_db_url.split('?')[0] if _raw_db_url else None  # Remove query params like ?pgbouncer=true

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Priority competitors (most likely to have news)
PRIORITY_COMPETITORS = [
    "Mappedin", "22Miles", "Pointr", "MapsPeople", "Broadsign",
    "Stratacache", "Poppulo", "Korbyt", "IndoorAtlas", "Inpixon",
    "Quuppa", "MazeMap", "Navori", "ViaDirect", "ZetaDisplay"
]

# Regional search configurations
REGIONS = {
    'global': {'gl': 'us', 'hl': 'en'},
    'mena': {'gl': 'ae', 'hl': 'en'},  # UAE
    'europe': {'gl': 'uk', 'hl': 'en'},  # UK as proxy for Europe
    'apac': {'gl': 'au', 'hl': 'en'},  # Australia
}

ANALYSIS_PROMPT = """You are a competitive intelligence analyst for Abuzz, a 3D wayfinding and kiosk solutions company.

I found these news articles about {competitor_name}:

{articles}

Based on these articles, identify any news related to:
- Wayfinding, indoor navigation, mapping
- Digital signage, kiosks, displays
- Retail technology, mall solutions
- Airport, hospital, venue technology
- Partnerships, funding, acquisitions
- Product launches, expansions

If there's genuinely no relevant news, respond with: {{"no_relevant_news": true}}

Otherwise, return JSON:

{{
  "news_items": [
    {{
      "event_type": "New Project/Installation" | "Investment/Funding Round" | "Award/Recognition" | "Product Launch" | "Partnership/Acquisition" | "Leadership Change" | "Market Expansion" | "Technical Innovation" | "Financial Performance",
      "title": "Clear headline (max 100 chars)",
      "summary": "2-3 sentence summary (max 500 chars)",
      "threat_level": 1-5,
      "date": "YYYY-MM-DD",
      "source_url": "The actual URL from the article",
      "region": "NORTH_AMERICA" | "EUROPE" | "MENA" | "APAC" | "GLOBAL",
      "details": {{
        "location": "City, Country or null",
        "financial_value": "Amount or null",
        "partners": ["Companies"],
        "products": ["Products"]
      }}
    }}
  ]
}}

Threat Level Guide:
- 1: Routine news, minimal impact
- 2: Minor development, worth monitoring
- 3: Moderate competitive move
- 4: Significant threat to Abuzz
- 5: Major threat (big contract in MENA/airports/malls, or game-changing development)

CRITICAL: Assign higher threat levels (4-5) for news in MENA region (UAE, Saudi, Qatar) as these are our primary markets.

DATE EXTRACTION INSTRUCTIONS:
- Use the EXACT "Published Date" provided in the article metadata.
- Do NOT use today's date unless the article explicitly says "today".
- If the date is "October 28, 2024", the output date must be "2024-10-28".
- If no date is found, use the current date as fallback.

Return ONLY valid JSON, no markdown formatting or explanation."""


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
    text = text.encode('ascii', 'ignore').decode('ascii')
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
        SELECT id, name, website, industry, region 
        FROM "Competitor" 
        WHERE status = 'active' OR status IS NULL
    """)
    all_competitors = cursor.fetchall()  # Already dicts thanks to RealDictCursor
    conn.close()
    
    def sort_key(c):
        name = c['name']
        if name in PRIORITY_COMPETITORS:
            return (0, PRIORITY_COMPETITORS.index(name))
        elif 'Direct' in (c.get('industry') or ''):
            return (1, name)
        else:
            return (2, name)
    
    return sorted(all_competitors, key=sort_key)


def check_existing_url(cursor, url):
    """Check if URL already exists in database (pass cursor to reuse connection)"""
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
        return False, "duplicate"
    
    try:
        news_id = generate_cuid()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Prepare strictly formatted strings for SQLite/Prisma compatibility
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
            news_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except:
            news_date = now
            
        # Ensure UTC time is used for consistency, though strptime is naive
        # We manually format to ISO 8601 with Z suffix
        news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
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


def search_serper(query, search_type='news', region='global', num_results=10):
    """
    Search using Serper.dev API
    search_type: 'news' or 'search'
    """
    if not SERPER_API_KEY:
        print("      ERROR: SERPER_API_KEY not set in .env")
        return []
    
    url = f"https://google.serper.dev/{search_type}"
    
    region_config = REGIONS.get(region, REGIONS['global'])
    
    payload = {
        "q": query,
        "gl": region_config['gl'],
        "hl": region_config['hl'],
        "num": num_results
    }
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract results based on search type
        if search_type == 'news':
            return data.get('news', [])
        else:
            return data.get('organic', [])
            
    except requests.exceptions.RequestException as e:
        print(f"      Serper error: {e}")
        return []


def search_news(competitor_name, regions_to_search=['global', 'mena', 'europe']):
    """
    Search for news about a competitor across multiple regions
    """
    all_results = []
    seen_urls = set()
    
    # Build search queries
    queries = [
        f'"{competitor_name}" news',
        f'{competitor_name} wayfinding OR signage OR kiosk OR navigation',
    ]
    
    for region in regions_to_search:
        for query in queries:
            results = search_serper(query, search_type='news', region=region, num_results=5)
            
            for r in results:
                url = r.get('link', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    r['_search_region'] = region  # Track which region found this
                    all_results.append(r)
            
            # Also try regular search for more coverage
            results = search_serper(query, search_type='search', region=region, num_results=5)
            
            for r in results:
                url = r.get('link', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    r['_search_region'] = region
                    all_results.append(r)
            
            if len(all_results) >= 15:
                break
        
        if len(all_results) >= 15:
            break
    
    return all_results[:15]


def analyze_with_claude(competitor_name, articles):
    """Send articles to Claude for analysis"""
    if not articles:
        return None
    
    if not ANTHROPIC_API_KEY:
        print("      ERROR: ANTHROPIC_API_KEY not set in .env")
        return None
    
    articles_text = ""
    for i, article in enumerate(articles, 1):
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
    
    prompt = ANALYSIS_PROMPT.format(
        competitor_name=competitor_name,
        articles=articles_text
    )
    
    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Clean JSON if wrapped in markdown
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        result = json.loads(response_text.strip())
        return result
        
    except json.JSONDecodeError as e:
        print(f"      JSON error: {e}")
        return None
    except anthropic.APIError as e:
        print(f"      Claude API error: {e}")
        return None
    except Exception as e:
        print(f"      Error: {e}")
        return None


def fetch_news_for_competitor(competitor, regions=['global', 'mena', 'europe']):
    """Fetch and analyze news for one competitor"""
    comp_id = competitor['id']
    name = competitor['name']
    
    print(f"\n  🔍 {name}")
    
    articles = search_news(name, regions)
    
    if not articles:
        print(f"      No articles found")
        return 0
    
    print(f"      Found {len(articles)} articles, analyzing with Claude...")
    
    analysis = analyze_with_claude(name, articles)
    
    if not analysis:
        print(f"      Analysis failed")
        return 0
    
    if analysis.get('no_relevant_news'):
        print(f"      No relevant news found")
        return 0
    
    news_items = analysis.get('news_items', [])
    saved = 0
    
    for item in news_items:
        success, status = save_news_item(comp_id, item)
        if success:
            saved += 1
            threat = item.get('threat_level', '?')
            region = item.get('region', 'GLOBAL')
            print(f"      ✅ [{threat}] [{region}] {item.get('title', '')[:45]}...")
        elif status == "duplicate":
            print(f"      ⏭️  Duplicate: {item.get('title', '')[:40]}...")
    
    return saved


def write_status(status, current_competitor=None, processed=0, total=0, error=None):
    """Write progress status to JSON file for Next.js API to read"""
    import time
    from datetime import datetime

    # Calculate progress
    percent_complete = 0
    if total > 0:
        percent_complete = int((processed / total) * 100)

    # Estimate remaining time (assuming ~15 seconds per competitor)
    estimated_seconds_remaining = (total - processed) * 15

    status_data = {
        'status': status,
        'current_competitor': current_competitor,
        'processed': processed,
        'total': total,
        'percent_complete': percent_complete,
        'estimated_seconds_remaining': estimated_seconds_remaining,
        'started_at': datetime.utcnow().isoformat() + 'Z' if status == 'running' and processed == 0 else None,
        'completed_at': datetime.utcnow().isoformat() + 'Z' if status == 'completed' else None,
        'error': error
    }

    # Write to public directory
    status_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'public', 'refresh_status.json')
    os.makedirs(os.path.dirname(status_path), exist_ok=True)

    with open(status_path, 'w') as f:
        json.dump(status_data, f, indent=2)
        f.flush()  # Ensure immediate write

    return status_data


def clear_all_news():
    """Clear all news"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM "CompetitorNews"')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def fetch_all_news(limit=None, clean_start=False, regions=['global', 'mena', 'europe']):
    """Main function"""
    print("=" * 60)
    print("🎯 ABUZZ COMPETITOR INTELLIGENCE FETCHER")
    print("   Powered by Serper.dev + Claude AI")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found in .env")
        print("   Get your API key at https://console.anthropic.com")
        write_status('error', error='ANTHROPIC_API_KEY not found')
        return 0

    if clean_start:
        deleted = clear_all_news()
        print(f"\n🧹 Cleared {deleted} news entries")

    competitors = get_competitors()
    print(f"\n📋 Found {len(competitors)} competitors")
    print(f"🌍 Searching regions: {', '.join(regions)}")

    if limit:
        competitors = competitors[:limit]
        print(f"🎯 Processing {limit} competitors")

    total_competitors = len(competitors)
    total_news = 0

    # Write initial status
    write_status('running', current_competitor=None, processed=0, total=total_competitors)

    try:
        for i, comp in enumerate(competitors, 1):
            # Update status before processing each competitor
            write_status('running', current_competitor=comp['name'], processed=i-1, total=total_competitors)

            print(f"\n[{i}/{len(competitors)}]", end="")
            saved = fetch_news_for_competitor(comp, regions)
            total_news += saved

            # Update status after processing
            write_status('running', current_competitor=comp['name'], processed=i, total=total_competitors)

            # Rate limiting - Serper is fast but let's be nice
            if i < len(competitors):
                time.sleep(2)

        # Write completion status
        write_status('completed', processed=total_competitors, total=total_competitors)

        print("\n\n" + "=" * 60)
        print(f"✅ COMPLETE: Added {total_news} news items")
        print("=" * 60)

        return total_news

    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        write_status('error', error=str(e), processed=i-1, total=total_competitors)
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fetch competitor news using Serper.dev')
    parser.add_argument('--limit', type=int, help='Limit number of competitors')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N competitors')
    parser.add_argument('--test', action='store_true', help='Test with 5 competitors')
    parser.add_argument('--clean', action='store_true', help='Clear all news first')
    parser.add_argument('--region', type=str, help='Specific region: global, mena, europe, apac')
    parser.add_argument('--mena', action='store_true', help='Focus on MENA region')
    args = parser.parse_args()
    
    # Determine regions to search
    regions = ['global', 'mena', 'europe']
    if args.region:
        regions = [args.region]
    elif args.mena:
        regions = ['mena', 'global']
    
    if args.test:
        fetch_all_news(limit=5, clean_start=True, regions=regions)
    elif args.limit:
        fetch_all_news(limit=args.limit, clean_start=args.clean, regions=regions)
    else:
        fetch_all_news(clean_start=args.clean, regions=regions)