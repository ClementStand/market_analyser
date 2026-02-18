import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env.local')
url = os.getenv("DATABASE_URL")
# Handle pooler vs session if needed, but standard lib usually handles it if url is correct
url = os.getenv("DATABASE_URL").split('?')[0]
try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute('SELECT id, name, "createdAt" FROM "Organization" ORDER BY "createdAt" DESC LIMIT 5')
    print("Recent Organizations:")
    for row in cur.fetchall():
        print(row)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
