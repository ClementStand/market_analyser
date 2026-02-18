"""
Debrief Generator for Competitor Intelligence Platform
Generates weekly intelligence debrief using Claude AI and saves to database.
Run locally: ./.venv/bin/python scripts/debrief_generator.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import json
import os
import uuid
import anthropic
from dotenv import load_dotenv

# Load .env.local first, then .env as fallback
load_dotenv('.env.local')
load_dotenv()

try:
    import config
except ImportError:
    # Fallback if running from root
    from scripts import config

# Configure
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
_raw_db_url = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL")
DATABASE_URL = _raw_db_url.split('?')[0] if _raw_db_url else None

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_cuid():
    return 'c' + uuid.uuid4().hex[:24]


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_organization(org_id):
    """Fetch organization details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, industry, keywords, regions FROM "Organization" WHERE id = %s', (org_id,))
    org = cursor.fetchone()
    conn.close()
    return org


def build_system_prompt(org=None):
    """Generate system prompt, optionally using org-specific context."""
    company_name = config.COMPANY_NAME
    industry = config.INDUSTRY
    regions_str = ", ".join([r.title() for r in config.REGIONS.keys()]) if config.REGIONS else "Global"
    kws_str = ", ".join(config.INDUSTRY_KEYWORDS) if config.INDUSTRY_KEYWORDS else "key industry developments"

    if org:
        company_name = org.get('name') or company_name
        industry = org.get('industry') or industry
        org_regions = org.get('regions')
        if org_regions:
            if isinstance(org_regions, list):
                regions_str = ", ".join(org_regions)
            elif isinstance(org_regions, str):
                regions_str = org_regions
        org_keywords = org.get('keywords')
        if org_keywords:
            if isinstance(org_keywords, list):
                kws_str = ", ".join(org_keywords)
            elif isinstance(org_keywords, str):
                kws_str = org_keywords

    return config.DEBRIEF_PROMPT_TEMPLATE.format(
        company_name=company_name,
        industry=industry,
        region_list=regions_str,
        industry_keywords=kws_str
    )


def fetch_recent_news(days=14, org_id=None):
    """Fetch news from the last N days, optionally filtered by org."""
    conn = get_db_connection()
    cursor = conn.cursor()

    end = datetime.datetime.now(datetime.timezone.utc)
    start = end - datetime.timedelta(days=days)

    if org_id:
        cursor.execute("""
            SELECT cn.*, c.name as competitor_name
            FROM "CompetitorNews" cn
            JOIN "Competitor" c ON cn."competitorId" = c.id
            WHERE cn.date >= %s AND cn.date <= %s
            AND (c.status = 'active' OR c.status IS NULL)
            AND c."organizationId" = %s
            ORDER BY cn."threatLevel" DESC
            LIMIT 50
        """, (start.isoformat(), end.isoformat(), org_id))
    else:
        cursor.execute("""
            SELECT cn.*, c.name as competitor_name
            FROM "CompetitorNews" cn
            JOIN "Competitor" c ON cn."competitorId" = c.id
            WHERE cn.date >= %s AND cn.date <= %s
            AND (c.status = 'active' OR c.status IS NULL)
            ORDER BY cn."threatLevel" DESC
            LIMIT 50
        """, (start.isoformat(), end.isoformat()))

    news = cursor.fetchall()
    conn.close()
    return news, start, end


def format_news(news_items):
    """Format news items for Claude"""
    lines = []
    for i, item in enumerate(news_items, 1):
        lines.append(f"""{i}. [{item['competitor_name']}] {item['title']}
   Date: {item['date']}
   Threat Level: {item['threatLevel']}/5
   Type: {item['eventType']}
   Region: {item.get('region') or 'Global'}
   Summary: {item['summary']}
   Source: {item['sourceUrl']}
""")
    return '\n'.join(lines)


def generate_debrief(news_items, system_prompt):
    """Generate debrief using Claude"""
    formatted = format_news(news_items)

    user_prompt = f"""Analyze these {len(news_items)} intelligence items from the past week and generate a strategic debrief:

{formatted}

Generate a comprehensive weekly intelligence debrief following the structure outlined."""

    print("  Calling Claude API...")
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return message.content[0].text


def save_debrief(content, period_start, period_end, item_count, org_id=None):
    """Save debrief to database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    debrief_id = generate_cuid()
    now = datetime.datetime.now(datetime.timezone.utc)

    cursor.execute("""
        INSERT INTO "Debrief" (id, content, "periodStart", "periodEnd", "itemCount", "generatedAt", "organizationId")
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        debrief_id,
        content,
        period_start.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        period_end.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        item_count,
        now.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        org_id
    ))

    conn.commit()
    conn.close()
    return debrief_id


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate intelligence debrief')
    parser.add_argument('--days', type=int, default=14, help='Number of days to look back (default: 14)')
    parser.add_argument('--org-id', type=str, help='Organization ID (required for multi-tenant)')
    args = parser.parse_args()

    print("=" * 60)
    print("📊 WEEKLY INTELLIGENCE DEBRIEF GENERATOR")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found")
        exit(1)

    if not DATABASE_URL:
        print("\n❌ ERROR: DATABASE_URL not found")
        exit(1)

    # Load org context
    org = None
    if args.org_id:
        org = get_organization(args.org_id)
        if org:
            print(f"\n🏢 Organization: {org.get('name')}")

    system_prompt = build_system_prompt(org)

    # Fetch news
    print(f"\n📋 Fetching recent news (last {args.days} days)...")
    news, start, end = fetch_recent_news(days=args.days, org_id=args.org_id)
    print(f"   Found {len(news)} items from {start.strftime('%b %d')} to {end.strftime('%b %d, %Y')}")

    if len(news) == 0:
        print("\n⚠️  No news found. Nothing to generate.")
        exit(0)

    # Generate debrief
    print("\n🤖 Generating debrief with Claude...")
    content = generate_debrief(news, system_prompt)
    print(f"   Generated {len(content)} characters")

    # Save to database
    print("\n💾 Saving to database...")
    debrief_id = save_debrief(content, start, end, len(news), org_id=args.org_id)
    print(f"   Saved with ID: {debrief_id}")

    print("\n" + "=" * 60)
    print("✅ DEBRIEF GENERATED AND SAVED")
    print("   View at: /debrief")
    print("=" * 60)
