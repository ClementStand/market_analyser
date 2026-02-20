from scripts.news_fetcher import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("DELETE FROM \"CompetitorNews\" WHERE title LIKE '%Monitoring Active%'")
print(f"Deleted {cursor.rowcount} fake articles")
conn.commit()
conn.close()
