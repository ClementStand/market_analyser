import asyncio
import os
import types
from google import genai as google_genai
from google.genai import types as genai_types
from dotenv import load_dotenv

load_dotenv('.env')

_gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def go():
    prompt = "Search for news articles published in the last 7 days about the company 'MazeMap'. Focus on: new contracts, partnerships. For each article, include the DIRECT URL to the article in plain text (e.g. 'URL: https://...')."
    response = await _gemini_client.aio.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
            temperature=1.0  # Required for optimal grounding activation
        )
    )
    print("Response text:", response.text)
    candidate = response.candidates[0]
    grounding = getattr(candidate, 'grounding_metadata', None)
    if grounding:
        chunks = getattr(grounding, 'grounding_chunks', []) or []
        for c in chunks:
            if hasattr(c, 'web') and c.web:
                print(c.web.uri)
                print(dir(c.web))

asyncio.run(go())
