"""
Onboarding Agent
Runs during the onboarding "processing" screen.
1. Enriches competitor data (Revenue, Employees, Headquarters, Key Markets)
2. Fetches historical news from 2025-01-01 to Today
"""

import asyncio
import argparse
import json
import os
import sys
import datetime
from dotenv import load_dotenv

# Load env variables
load_dotenv('.env.local')
load_dotenv()

# Add scripts dir to path to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import config
import news_fetcher
from google import genai as google_genai
from google.genai import types as genai_types

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_gemini_client = google_genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def get_db_connection():
    return news_fetcher.get_db_connection()

async def enrich_competitor_metadata(competitor):
    """
    Uses Gemini to find: Revenue, Employees, Headquarters, Key Markets
    Updates the DB record directly.
    """
    if not _gemini_client:
        return

    print(f"    🔍 Enriching metadata for {competitor['name']}...")
    
    try:
        search_prompt = (
            f"Research the company '{competitor['name']}' (Website: {competitor.get('website', '')}). "
            f"Find their latest available: \n"
            f"1. Estimated Annual Revenue (e.g. '$50M' or 'Undisclosed')\n"
            f"2. Employee Count (e.g. '250+')\n"
            f"3. Headquarters City/Country\n"
            f"4. Key Markets / Regions they operate in\n\n"
            f"Return purely valid JSON with keys: revenue, employees, headquarters, key_markets."
        )

        response = await _gemini_client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=search_prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                # response_mime_type="application/json"  # REMOVED: Incompatible with Search tool
            )
        )
        
        text = response.text
        # Clean JSON if needed
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        data = json.loads(text.strip())
        
        # Update DB
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE "Competitor"
            SET revenue = %s,
                "employeeCount" = %s,
                headquarters = %s,
                "keyMarkets" = %s,
                "updatedAt" = NOW()
            WHERE id = %s
        """, (
            data.get('revenue') or None,
            data.get('employees') or None,
            data.get('headquarters') or None,
            data.get('key_markets') or None,
            competitor['id']
        ))
        
        conn.commit()
        conn.close()
        print(f"    ✅ Enriched {competitor['name']}")
        
    except Exception as e:
        print(f"    ❌ Error enriching {competitor['name']}: {e}")

async def process_competitor(competitor):
    """
    1. Enrich Metadata
    2. Fetch Historical News (2025-01-01 to Now)
    """
    print(f"🚀 Processing {competitor['name']}...")
    
    # 1. Metadata Enrichment
    await enrich_competitor_metadata(competitor)
    
    # 2. News Fetching
    # Calculate days back from 2025-01-01 to now
    start_date = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    days_back = (now - start_date).days + 1
    
    # Determine regions to search
    # Check if competitor has a specific region, else use Organization's regions or Global
    # For now, let's just search Global + Native to be safe and comprehensive
    regions_to_search = ['global'] 
    
    if competitor.get('region'):
        # Map DB region string to config key if possible
        r_lower = competitor['region'].lower()
        if 'north america' in r_lower: regions_to_search.append('north_america')
        elif 'europe' in r_lower: regions_to_search.append('europe')
        elif 'mena' in r_lower: regions_to_search.append('mena')
        elif 'apac' in r_lower: regions_to_search.append('apac')
    
    print(f"    📰 Fetching news since {start_date.strftime('%Y-%m-%d')} ({days_back} days)...")
    
    articles = await news_fetcher.gather_all_articles(competitor, days_back, regions_to_search)
    
    print(f"    Found {len(articles)} raw articles.")
    
    # Save relevant articles
    saved_count = 0
    conn = get_db_connection()
    for article in articles:
        # We manually process/save here to ensure we capture them
        # Note: news_fetcher.save_news_item does the AI threat analysis / summary IF we passed it through analysis first
        # But gathered articles are raw. We need to standardise or just save them raw?
        # The prompt in news_fetcher is designed to Analyze a BATCH of articles.
        # For the onboarding, we might want to just save them raw or run a quick analysis.
        # Let's use the existing analysis flow if possible, or just save them with basic info?
        
        # Realistically, for 5 competitors * many months, running Claude analysis on ALL might be too slow/expensive?
        # Let's filter first.
        
        # Actually, let's stick to the high quality approach: Validate/Analyze with Claude.
        # But we'll batch them.
        pass
    conn.close()

    # Run Analysis (Batched)
    analyzed_data = await news_fetcher.analyze_with_claude_async(competitor['name'], articles, days_back)
    
    if analyzed_data and 'news_items' in analyzed_data:
        conn = get_db_connection()
        for item in analyzed_data['news_items']:
            success, msg = news_fetcher.save_news_item(competitor['id'], item, conn)
            if success:
                saved_count += 1
        conn.close()
        
    print(f"    ✅ Saved {saved_count} analyzed news items for {competitor['name']}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--competitor-ids', help='Comma separated list of competitor IDs')
    parser.add_argument('--org-id', help='Organization ID')
    args = parser.parse_args()

    competitors = []
    conn = get_db_connection()
    cursor = conn.cursor()

    if args.competitor_ids:
        ids = args.competitor_ids.split(',')
        cursor.execute(f"SELECT * FROM \"Competitor\" WHERE id = ANY(%s)", (ids,))
        competitors = cursor.fetchall()
    elif args.org_id:
        print(f"Fetching competitors for Organization: {args.org_id}")
        cursor.execute(f"SELECT * FROM \"Competitor\" WHERE \"organizationId\" = %s", (args.org_id,))
        competitors = cursor.fetchall()
    else:
        print("Error: Must provide either --competitor-ids or --org-id")
        conn.close()
        return

    conn.close()
    
    if not competitors:
        print("No competitors found matching criteria.")
        return
    
    print(f"Starting Onboarding Agent for {len(competitors)} competitors...")
    
    # Process in parallel? Or sequential to avoid rate limits?
    # Serper/Gemini have limits. Let's do parallel but with semaphores inside news_fetcher.
    # news_fetcher.gather_all_articles handles concurrency for one competitor.
    # processing multiple competitors in parallel might hit global limits.
    # Let's stick to sequential for safety in this MVP phase, or chunks of 2.
    
    for comp in competitors:
        await process_competitor(comp)

    print("Onboarding Agent Complete.")

if __name__ == "__main__":
    asyncio.run(main())
