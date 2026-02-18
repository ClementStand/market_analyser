"""
Onboarding Agent
Runs during the onboarding "processing" screen.
1. Enriches competitor data (Revenue, Employees, Headquarters, Key Markets)
2. Fetches historical news (Phase 1: 2025-01-01 to today, Phase 2: last 7 days for more detail)
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


async def process_competitor(competitor, org=None):
    """
    1. Enrich Metadata
    2. Phase 1: Fetch Historical News (2025-01-01 to Now)
    3. Phase 2: Fetch Recent News (last 7 days) for more detail
    """
    print(f"🚀 Processing {competitor['name']}...")

    # Get org context
    org_company_name = (org.get('name') if org else None) or config.COMPANY_NAME
    org_industry = (org.get('industry') if org else None) or config.INDUSTRY
    org_keywords = (org.get('keywords') if org else None) or config.INDUSTRY_KEYWORDS
    if isinstance(org_keywords, str):
        org_keywords = [k.strip() for k in org_keywords.split(',') if k.strip()]
    org_industry_context = f"developments in the {org_industry} industry" if org_industry else None

    # 1. Metadata Enrichment
    await enrich_competitor_metadata(competitor)

    # Determine regions to search
    regions_to_search = ['global']
    if org and org.get('regions'):
        org_regions = org['regions']
        if isinstance(org_regions, str):
            org_regions = [r.strip().lower().replace(' ', '_') for r in org_regions.split(',')]
        region_map = {
            'global': 'global', 'north_america': 'north_america', 'north america': 'north_america',
            'europe': 'europe', 'mena': 'mena', 'apac': 'apac',
        }
        for r in org_regions:
            mapped = region_map.get(r.lower().replace(' ', '_'))
            if mapped and mapped not in regions_to_search:
                regions_to_search.append(mapped)

    if competitor.get('region'):
        r_lower = competitor['region'].lower()
        if 'north america' in r_lower and 'north_america' not in regions_to_search:
            regions_to_search.append('north_america')
        elif 'europe' in r_lower and 'europe' not in regions_to_search:
            regions_to_search.append('europe')
        elif 'mena' in r_lower and 'mena' not in regions_to_search:
            regions_to_search.append('mena')
        elif 'apac' in r_lower and 'apac' not in regions_to_search:
            regions_to_search.append('apac')

    # Phase 1: Historical scan (2025-01-01 to now)
    start_date = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    days_back = (now - start_date).days + 1

    print(f"    📰 Phase 1: Historical news since {start_date.strftime('%Y-%m-%d')} ({days_back} days)...")

    articles = await news_fetcher.gather_all_articles(
        competitor, days_back, regions_to_search,
        industry_keywords=org_keywords, industry_context=org_industry_context
    )

    print(f"    Found {len(articles)} raw articles.")

    # Run Analysis (Batched)
    saved_count = 0
    analyzed_data = await news_fetcher.analyze_with_claude_async(
        competitor['name'], articles, days_back,
        company_name=org_company_name, industry=org_industry
    )

    if analyzed_data and 'news_items' in analyzed_data:
        conn = get_db_connection()
        for item in analyzed_data['news_items']:
            success, msg = news_fetcher.save_news_item(competitor['id'], item, conn)
            if success:
                saved_count += 1
        conn.close()

    print(f"    ✅ Phase 1: Saved {saved_count} items for {competitor['name']}")

    # Phase 2: Recent scan (last 7 days) for more detail
    print(f"    📰 Phase 2: Recent news (last 7 days)...")
    recent_articles = await news_fetcher.gather_all_articles(
        competitor, 7, regions_to_search,
        industry_keywords=org_keywords, industry_context=org_industry_context
    )

    # Filter out articles we already have
    existing_urls = {a.get('link', '') for a in articles}
    new_recent = [a for a in recent_articles if a.get('link', '') not in existing_urls]

    if new_recent:
        print(f"    Found {len(new_recent)} additional recent articles.")
        recent_analyzed = await news_fetcher.analyze_with_claude_async(
            competitor['name'], new_recent, 7,
            company_name=org_company_name, industry=org_industry
        )
        recent_saved = 0
        if recent_analyzed and 'news_items' in recent_analyzed:
            conn = get_db_connection()
            for item in recent_analyzed['news_items']:
                success, msg = news_fetcher.save_news_item(competitor['id'], item, conn)
                if success:
                    recent_saved += 1
            conn.close()
        saved_count += recent_saved
        print(f"    ✅ Phase 2: Saved {recent_saved} additional items")
    else:
        print(f"    Phase 2: No new articles beyond Phase 1")

    print(f"    ✅ Total: {saved_count} news items for {competitor['name']}")


async def run_onboarding(competitors, org_id=None, job_id=None):
    """Run the full onboarding process for a list of competitors."""
    # Load org context
    org = None
    if org_id:
        org = news_fetcher.get_organization(org_id)

    total = len(competitors)
    print(f"Starting Onboarding Agent for {total} competitors...")

    for i, comp in enumerate(competitors):
        if job_id:
            news_fetcher.write_status('running', current_competitor=comp.get('name'),
                                      processed=i, total=total, job_id=job_id)
        await process_competitor(comp, org=org)

    if job_id:
        news_fetcher.write_status('completed', processed=total, total=total, job_id=job_id)

    print("Onboarding Agent Complete.")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--competitor-ids', help='Comma separated list of competitor IDs')
    parser.add_argument('--org-id', help='Organization ID')
    parser.add_argument('--job-id', help='FetchJob ID for status tracking')
    args = parser.parse_args()

    competitors = []
    conn = get_db_connection()
    cursor = conn.cursor()

    if args.competitor_ids:
        ids = args.competitor_ids.split(',')
        cursor.execute("SELECT * FROM \"Competitor\" WHERE id = ANY(%s)", (ids,))
        competitors = cursor.fetchall()
    elif args.org_id:
        print(f"Fetching competitors for Organization: {args.org_id}")
        cursor.execute("SELECT * FROM \"Competitor\" WHERE \"organizationId\" = %s", (args.org_id,))
        competitors = cursor.fetchall()
    else:
        print("Error: Must provide either --competitor-ids or --org-id")
        conn.close()
        return

    conn.close()

    if not competitors:
        print("No competitors found matching criteria.")
        return

    await run_onboarding(competitors, org_id=args.org_id, job_id=args.job_id)

if __name__ == "__main__":
    asyncio.run(main())
