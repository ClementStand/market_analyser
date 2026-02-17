
import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
load_dotenv('.env.local')

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def test():
    search_name = "IndoorAtlas"
    domain = "indooratlas.com"
    days_back = 420
    
    prompt = (
            f"Find any press releases, news announcements, or blog posts from or about "
            f"'{search_name}' (website: {domain}) published in the last {days_back} days. "
            f"Also search trade publications, PR Newswire, BusinessWire, and industry blogs "
            f"for any coverage of {search_name}. "
            f"Please provide a bulleted list of the articles you find, including their dates."
        )
    print(f"Prompt: {prompt}\n")
    
    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    
    candidate = response.candidates[0] if response.candidates else None
    if candidate and candidate.content and candidate.content.parts:
        print("\n--- Response Text ---")
        print(candidate.content.parts[0].text)
        print("---------------------\n")
    
    grounding = getattr(candidate, 'grounding_metadata', None)
    if grounding:
        print("\n--- Grounding Supports ---")
        supports = getattr(grounding, 'grounding_supports', [])
        for s in supports:
            print(s)
        print("--------------------------\n")
        
        chunks = getattr(grounding, 'grounding_chunks', None) 
        if chunks:
            print(f"Num Chunks: {len(chunks)}\n")

if __name__ == "__main__":
    asyncio.run(test())
