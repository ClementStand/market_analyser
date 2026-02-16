"""
Sync competitors from competitors2.csv to the database.

Safe for production: upserts competitors and archives stale ones,
but does NOT touch CompetitorNews data.

Usage:
    python scripts/sync_competitors.py
    python scripts/sync_competitors.py --dry-run
"""

import csv
import os
import sys
import uuid
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv('.env.local')
load_dotenv()

# Use pooler connection (same as news_fetcher.py), strip Prisma-specific params
_raw_url = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL")
DATABASE_URL = _raw_url.split('?')[0] if _raw_url else None

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'competitors2.csv')


def generate_cuid():
    return 'c' + uuid.uuid4().hex[:24]


def get_db_connection():
    if not DATABASE_URL:
        print("ERROR: No DATABASE_URL or DIRECT_URL set in environment.")
        sys.exit(1)
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def load_csv():
    """Load and parse competitors2.csv, skipping Abuzz and blank rows."""
    companies = []
    csv_path = os.path.abspath(CSV_PATH)
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get('Company') or '').strip()
            if not name:
                continue
            if name.lower().startswith('abuzz'):
                continue
            companies.append({
                'name': name,
                'website': (row.get('Website') or '').strip() or None,
                'description': (row.get('Primary Solution') or '').strip() or None,
                'industry': (row.get('Category') or '').strip() or None,
                'headquarters': (row.get('HQ Location') or '').strip() or None,
                'keyMarkets': (row.get('Key Markets') or '').strip() or None,
                'region': (row.get('Key Markets') or row.get('HQ Location') or '').strip() or None,
                'employeeCount': (row.get('Approx Employees') or '').strip() or None,
                'revenue': (row.get('Est. Revenue (USD)') or '').strip() or None,
                'fundingStatus': (row.get('Funding/Status') or '').strip() or None,
            })
    return companies


def sync(dry_run=False):
    companies = load_csv()
    csv_names = {c['name'] for c in companies}
    print(f"  CSV: {len(companies)} competitors loaded (excluding Abuzz)")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch current DB state
    cursor.execute('SELECT id, name, status FROM "Competitor"')
    db_rows = cursor.fetchall()
    db_by_name = {r['name']: r for r in db_rows}

    added = 0
    updated = 0
    archived = 0

    for company in companies:
        name = company['name']
        existing = db_by_name.get(name)

        if existing:
            # Update fields and ensure status=active
            if not dry_run:
                cursor.execute(
                    '''UPDATE "Competitor"
                       SET website = %s,
                           description = %s,
                           industry = %s,
                           headquarters = %s,
                           "keyMarkets" = %s,
                           region = %s,
                           "employeeCount" = %s,
                           revenue = %s,
                           "fundingStatus" = %s,
                           status = 'active',
                           "updatedAt" = NOW()
                       WHERE name = %s''',
                    (
                        company['website'], company['description'], company['industry'],
                        company['headquarters'], company['keyMarkets'], company['region'],
                        company['employeeCount'], company['revenue'], company['fundingStatus'],
                        name
                    )
                )
            updated += 1
            print(f"  ~ Updated: {name}")
        else:
            # Insert new competitor
            if not dry_run:
                cursor.execute(
                    '''INSERT INTO "Competitor"
                       (id, name, website, description, industry, headquarters,
                        "keyMarkets", region, "employeeCount", revenue, "fundingStatus",
                        status, "createdAt", "updatedAt")
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())''',
                    (
                        generate_cuid(), name, company['website'], company['description'],
                        company['industry'], company['headquarters'], company['keyMarkets'],
                        company['region'], company['employeeCount'], company['revenue'],
                        company['fundingStatus']
                    )
                )
            added += 1
            print(f"  + Added:   {name}")

    # Archive competitors in DB that are no longer in the CSV
    for db_name, db_row in db_by_name.items():
        if db_name not in csv_names and db_row['status'] == 'active':
            if not dry_run:
                cursor.execute(
                    'UPDATE "Competitor" SET status = \'archived\', "updatedAt" = NOW() WHERE name = %s',
                    (db_name,)
                )
            archived += 1
            print(f"  - Archived: {db_name}")

    if not dry_run:
        conn.commit()
        print(f"\nDone: {added} added, {updated} updated, {archived} archived.")
    else:
        print(f"\nDry-run: {added} would be added, {updated} would be updated, {archived} would be archived.")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sync competitors2.csv to database')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing to DB')
    args = parser.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Syncing competitors from competitors2.csv...")
    sync(dry_run=args.dry_run)
