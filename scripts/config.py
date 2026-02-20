import os
from dotenv import load_dotenv
import datetime

# Load env variables
load_dotenv('.env.local')
load_dotenv()

# App Configuration
APP_NAME = os.getenv("NEXT_PUBLIC_APP_NAME", "Market Analyser")
COMPANY_NAME = os.getenv("NEXT_PUBLIC_COMPANY_NAME", "My Company")
INDUSTRY = os.getenv("NEXT_PUBLIC_INDUSTRY", "Technology")
INDUSTRY_KEYWORDS = [k.strip() for k in os.getenv("NEXT_PUBLIC_INDUSTRY_KEYWORDS", "").split(',') if k.strip()]

# Search Configuration
# If no specific keywords are provided, these defaults will be used in news_fetcher.py
# Default keywords for Serper searches (combined with Company Name)
DEFAULT_SEARCH_TOPICS = [
    "contract OR deal",
    "launch OR expansion",
    "financial results OR funding",
    "acquisition OR merger",
    "partnership OR partner",
    "CEO OR appoints OR executive",
    "press release"
]

# Region Configuration (Mirrors src/lib/config.ts)
REGIONS = {
    'global': {'gl': 'us', 'hl': 'en'},
    'mena': {'gl': 'ae', 'hl': 'en'},
    'europe': {'gl': 'gb', 'hl': 'en'},
    'north_america': {'gl': 'us', 'hl': 'en'},
    'apac': {'gl': 'sg', 'hl': 'en'},
}

# Native Language Search Configuration
HQ_NATIVE_REGIONS = {
    'france':       {'gl': 'fr', 'hl': 'fr', '_label': 'france_fr'},
    'germany':      {'gl': 'de', 'hl': 'de', '_label': 'germany_de'},
    'spain':        {'gl': 'es', 'hl': 'es', '_label': 'spain_es'},
    'norway':       {'gl': 'no', 'hl': 'no', '_label': 'norway_no'},
    'denmark':      {'gl': 'dk', 'hl': 'da', '_label': 'denmark_da'},
    'finland':      {'gl': 'fi', 'hl': 'fi', '_label': 'finland_fi'},
    'sweden':       {'gl': 'se', 'hl': 'sv', '_label': 'sweden_sv'},
    'switzerland':  {'gl': 'ch', 'hl': 'de', '_label': 'switzerland_de'},
    'netherlands':  {'gl': 'nl', 'hl': 'nl', '_label': 'netherlands_nl'},
    'italy':        {'gl': 'it', 'hl': 'it', '_label': 'italy_it'},
    'israel':       {'gl': 'il', 'hl': 'iw', '_label': 'israel_iw'},
    'south korea':  {'gl': 'kr', 'hl': 'ko', '_label': 'korea_ko'},
    'korea':        {'gl': 'kr', 'hl': 'ko', '_label': 'korea_ko'},
    'japan':        {'gl': 'jp', 'hl': 'ja', '_label': 'japan_ja'},
    'hong kong':    {'gl': 'hk', 'hl': 'zh-tw', '_label': 'hongkong_zh'},
    'china':        {'gl': 'cn', 'hl': 'zh-cn', '_label': 'china_zh'},
    'poland':       {'gl': 'pl', 'hl': 'pl', '_label': 'poland_pl'},
    'brazil':       {'gl': 'br', 'hl': 'pt', '_label': 'brazil_pt'},
    'portugal':     {'gl': 'pt', 'hl': 'pt', '_label': 'portugal_pt'},
    'russia':       {'gl': 'ru', 'hl': 'ru', '_label': 'russia_ru'},
    'turkey':       {'gl': 'tr', 'hl': 'tr', '_label': 'turkey_tr'},
}

ENGLISH_SPEAKING_HQ = {'uk', 'usa', 'canada', 'australia', 'ireland', 'new zealand', 'singapore'}

# Prompt Templates
ANALYSIS_PROMPT_TEMPLATE = """You are a competitive intelligence analyst for {company_name}, operating in the {industry} industry.

Your goal is to identify strategic moves by the competitor: {competitor_name}.

I found these search results:
{articles}

CONTEXT:
Today is {today_date}.
{date_instruction}

{dedup_context}

IMPORTANT: Analyze ALL articles. Always output your title and summary in ENGLISH.

Your job is to find REAL BUSINESS NEWS (including official press releases and blog announcements). Include:
- New contracts, deals, project wins
- Partnerships, acquisitions, mergers, joint ventures
- Product launches and major updates
- Strategic shifts (e.g., new business models, AI integration)
- Financial results, funding rounds, investment news
- Key leadership changes
- Market expansion (new offices, new regions)

STRICTLY EXCLUDE:
- Product catalog pages or sales listings
- Generic company profile descriptions
- Job postings and "Careers" pages
- Social media posts without real news content
- "About us" pages
- Blog posts that are just general advice (content marketing), BUT INCLUDE official company announcements.
- News about individuals unless they are C-level execs and it impacts the company strategy.

If NONE of the articles contain real news events, respond with: {{"no_relevant_news": true}}

Otherwise, return JSON:
{{
  "news_items": [
    {{
      "event_type": "New Project" | "Investment" | "Product Launch" | "Partnership" | "Leadership Change" | "Market Expansion" | "Financial Performance" | "Other",
      "category": "Product" | "Expansion" | "Pricing" | "General",
      "title": "Clear headline in ENGLISH (max 100 chars)",
      "summary": "2-3 sentence summary in ENGLISH (max 500 chars). Focus on the strategic implication.",
      "threat_level": 1-5,
      "impact_score": 0-100,
      "date": "YYYY-MM-DD",
      "source_url": "The actual URL",
      "region": "MENA" | "EUROPE" | "NORTH_AMERICA" | "APAC" | "GLOBAL",
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
1: Routine news
3: Moderate competitive move
5: Critical strategic threat (e.g. major new product in your core market)

Impact Score Guide (0-100):
Start with a base score:
- Routine news / minor updates: base 10
- Moderate business news: base 20-30
- Significant competitive move: base 40-50

Then ADD bonuses (cap total at 100):
- M&A activity (Sales, Mergers, Acquisitions, Major Funding Rounds): +40 points
- Major enterprise contracts (Airports, Malls, Large Enterprise rollouts): +30 points
{vip_competitor_instruction}
{priority_region_instruction}
"""

# Date Logic
# Default to 2025-01-01 for historical scan
DEFAULT_DATE_CUTOFF = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)


DEBRIEF_PROMPT_TEMPLATE = """You are a strategic intelligence analyst for {company_name}, operating in the {industry} industry.

Generate a comprehensive weekly intelligence debrief based on the provided competitor news items.

**Key Context:**
- **Your Role:** Provide actionable competitive intelligence for {company_name}.
- **Primary Markets:** {region_list}

**Instructions:**
1. **Critical Threats:** Identify any major competitor moves that directly threaten {company_name}'s market position in {industry}.
2. **Focus:** Prioritize news about {industry_keywords}.
3. **Reject Noise:** Do NOT include general industry trends or minor updates. Only include items that force strategic rethinking.

**Structure:**
1. **Top 3 Strategic Priorities:** Select the 3 most critical items. Explain WHY they matter.
2. **Executive Summary** (2-3 sentences).
3. **High-Priority Threats** (Items with Threat Level 4-5).
4. **Competitor Movements** (Group by company).
5. **Market Trends & Insights**.
6. **Strategic Recommendations**.

**Tone:** Professional, concise, forward-looking. Use clear markdown formatting."""
