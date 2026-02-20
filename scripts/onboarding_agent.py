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

        # Normalize values to clean strings before storing
        revenue = data.get('revenue')
        if isinstance(revenue, list):
            revenue = ', '.join(str(r) for r in revenue)
        revenue = str(revenue).strip() if revenue else None

        employees = data.get('employees')
        if isinstance(employees, list):
            employees = ', '.join(str(e) for e in employees)
        employees = str(employees).strip() if employees else None

        headquarters = data.get('headquarters')
        if isinstance(headquarters, list):
            headquarters = ', '.join(str(h) for h in headquarters)
        headquarters = str(headquarters).strip() if headquarters else None

        key_markets = data.get('key_markets')
        if isinstance(key_markets, list):
            key_markets = ', '.join(str(m) for m in key_markets)
        key_markets = str(key_markets).strip() if key_markets else None

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
            revenue,
            employees,
            headquarters,
            key_markets,
            competitor['id']
        ))

        conn.commit()
        conn.close()
        print(f"    ✅ Enriched {competitor['name']}")

    except Exception as e:
        print(f"    ❌ Error enriching {competitor['name']}: {e}")


async def process_competitor(competitor, org=None, job_id=None, processed=0, total=0):
    """
    1. Enrich Metadata
    2. Phase 1: Fetch Historical News (2025-01-01 to Now)
    3. Phase 2: Fetch Recent News (last 7 days) for more detail
    """
    print(f"🚀 Processing {competitor['name']}...")
    
    # helper for status updates
    def update_phase(phase_name):
        if job_id:
            news_fetcher.write_status('running', current_competitor=f"{competitor['name']} ({phase_name})",
                                    processed=processed, total=total, job_id=job_id)

    # Get org context
    org_company_name = (org.get('name') if org else None) or config.COMPANY_NAME
    org_industry = (org.get('industry') if org else None) or config.INDUSTRY
    org_keywords = (org.get('keywords') if org else None) or config.INDUSTRY_KEYWORDS
    if isinstance(org_keywords, str):
        org_keywords = [k.strip() for k in org_keywords.split(',') if k.strip()]
    org_industry_context = f"developments in the {org_industry} industry" if org_industry else None
    org_vip_competitors = (org.get('vipCompetitors') if org else None) or []
    org_priority_regions = (org.get('priorityRegions') if org else None) or []

    update_phase("Enriching Data")
    
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
    
    update_phase(f"Searching {days_back}d History")
    
    articles = await news_fetcher.gather_all_articles(
        competitor, days_back, regions_to_search,
        industry_keywords=org_keywords, industry_context=org_industry_context
    )

    print(f"    Found {len(articles)} raw articles.")

    # Run Analysis (Batched)
    update_phase(f"Analyzing {len(articles)} Items")

    saved_count = 0
    analyzed_data = await news_fetcher.analyze_with_claude_async(
        competitor['name'], articles, days_back,
        company_name=org_company_name, industry=org_industry,
        vip_competitors=org_vip_competitors, priority_regions=org_priority_regions
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
    
    update_phase("Deep Search Recent")
    
    recent_articles = await news_fetcher.gather_all_articles(
        competitor, 7, regions_to_search,
        industry_keywords=org_keywords, industry_context=org_industry_context
    )

    # Filter out articles we already have
    existing_urls = {a.get('link', '') for a in articles}
    new_recent = [a for a in recent_articles if a.get('link', '') not in existing_urls]

    if new_recent:
        print(f"    Found {len(new_recent)} additional recent articles.")
        
        update_phase(f"Analyzing {len(new_recent)} Recent Items")
        
        recent_analyzed = await news_fetcher.analyze_with_claude_async(
            competitor['name'], new_recent, 7,
            company_name=org_company_name, industry=org_industry,
            vip_competitors=org_vip_competitors, priority_regions=org_priority_regions
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


def send_completion_email(org_id, job_id):
    """Send analysis completion email via Resend API. Skips silently on failure."""
    resend_api_key = os.getenv("RESEND_API_KEY")
    if not resend_api_key:
        print("    ⚠️ RESEND_API_KEY not configured, skipping email")
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already sent for this job
        cursor.execute('SELECT "emailSent" FROM "FetchJob" WHERE id = %s', (job_id,))
        job_row = cursor.fetchone()
        if job_row and job_row.get('emailSent'):
            conn.close()
            return

        # Get org name and user email
        cursor.execute('SELECT name FROM "Organization" WHERE id = %s', (org_id,))
        org_row = cursor.fetchone()
        cursor.execute('SELECT email FROM "UserProfile" WHERE "organizationId" = %s LIMIT 1', (org_id,))
        user_row = cursor.fetchone()
        conn.close()

        if not org_row or not user_row:
            print("    ⚠️ Could not find org/user for email")
            return

        org_name = org_row['name']
        user_email = user_row['email']
        dashboard_url = os.getenv("APP_URL", "https://market-analyser-dtcf.vercel.app")

        # Send via Resend API
        import httpx
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "Market Analyser <onboarding@resend.dev>",
                "to": [user_email],
                "subject": f"Analysis Complete - {org_name}",
                "html": f"""
                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 500px; margin: 0 auto; padding: 32px;">
                        <h2 style="color: #0f172a; margin-bottom: 16px;">Analysis Complete</h2>
                        <p style="color: #475569; line-height: 1.6;">
                            Your competitor intelligence analysis for <strong>{org_name}</strong> has finished.
                            New articles have been added to your dashboard.
                        </p>
                        <a href="{dashboard_url}" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background-color: #0891b2; color: white; text-decoration: none; border-radius: 8px; font-weight: 500;">
                            View Dashboard
                        </a>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 32px;">
                            Market Analyser - Competitor Intelligence Platform
                        </p>
                    </div>
                """,
            },
            timeout=10,
        )

        if response.status_code == 200:
            # Mark email as sent in DB
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE "FetchJob" SET "emailSent" = true WHERE id = %s', (job_id,))
            conn.commit()
            conn.close()
            print(f"    ✅ Completion email sent to {user_email}")
        else:
            print(f"    ⚠️ Email send failed: {response.status_code} {response.text}")

    except Exception as e:
        print(f"    ⚠️ Email send error: {e}")


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
        await process_competitor(comp, org=org, job_id=job_id, processed=i, total=total)

    if job_id:
        news_fetcher.write_status('completed', processed=total, total=total, job_id=job_id)
        # Send completion email server-side (handles case where user closed the page)
        send_completion_email(org_id, job_id)

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
