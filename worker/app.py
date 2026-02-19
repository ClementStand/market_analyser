
import os
import sys
import logging
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import asyncio

# 1. Initialize the App FIRST
app = FastAPI()
logger = logging.getLogger(__name__)

# 2. Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from scripts import onboarding_agent
from scripts import news_fetcher

# 3. Define Routes AFTER app is initialized
@app.get("/")
def read_root():
    return {"status": "Market-Worker is running", "message": "Ready for discovery"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

class OnboardingRequest(BaseModel):
    competitorIds: Optional[List[str]] = None
    orgId: Optional[str] = None
    jobId: Optional[str] = None

class RefreshNewsRequest(BaseModel):
    orgId: str
    jobId: Optional[str] = None
    days: Optional[int] = None
    competitorName: Optional[str] = None

class EnrichCompetitorRequest(BaseModel):
    competitorId: str

async def run_onboarding_logic(competitor_ids: Optional[List[str]], org_id: Optional[str], job_id: Optional[str] = None):
    try:
        logger.info(f"Worker starting onboarding for orgId={org_id} competitors={competitor_ids}")

        conn = onboarding_agent.get_db_connection()
        cursor = conn.cursor()

        competitors = []
        if competitor_ids:
            cursor.execute("SELECT * FROM \"Competitor\" WHERE id = ANY(%s)", (competitor_ids,))
            competitors = cursor.fetchall()
        elif org_id:
            cursor.execute("SELECT * FROM \"Competitor\" WHERE \"organizationId\" = %s", (org_id,))
            competitors = cursor.fetchall()

        conn.close()

        if not competitors:
            logger.warning("No competitors found for worker task")
            return

        await onboarding_agent.run_onboarding(competitors, org_id=org_id, job_id=job_id)

        logger.info("Worker onboarding task completed successfully")

    except Exception as e:
        logger.error(f"Worker onboarding task failed: {e}")
        if job_id:
            try:
                news_fetcher.write_status('error', error=str(e), job_id=job_id)
            except:
                pass

async def run_refresh_logic(org_id: str, job_id: Optional[str] = None, days: Optional[int] = None, competitor_name: Optional[str] = None):
    try:
        logger.info(f"Worker starting news refresh for orgId={org_id} days={days}")

        await news_fetcher._fetch_all_news_async_inner(
            org_id=org_id,
            days=days,
            competitor_name=competitor_name,
            job_id=job_id,
        )

        logger.info("Worker refresh task completed successfully")

    except Exception as e:
        logger.error(f"Worker refresh task failed: {e}")
        if job_id:
            try:
                news_fetcher.write_status('error', error=str(e), job_id=job_id)
            except:
                pass

async def run_enrich_logic(competitor_id: str):
    try:
        logger.info(f"Worker starting enrichment for competitor={competitor_id}")
        conn = onboarding_agent.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM "Competitor" WHERE id = %s', (competitor_id,))
        competitor = cursor.fetchone()
        conn.close()

        if not competitor:
            logger.warning(f"Competitor {competitor_id} not found")
            return

        await onboarding_agent.enrich_competitor_metadata(competitor)
        logger.info(f"Worker enrichment completed for {competitor.get('name', competitor_id)}")

    except Exception as e:
        logger.error(f"Worker enrichment failed for {competitor_id}: {e}")

@app.post("/enrich-competitor", status_code=202)
async def enrich_competitor(request: EnrichCompetitorRequest, background_tasks: BackgroundTasks):
    if not request.competitorId:
        raise HTTPException(status_code=400, detail="Must provide competitorId")
    background_tasks.add_task(run_enrich_logic, request.competitorId)
    return {"message": "Enrichment started in background"}

@app.post("/process-onboarding", status_code=202)
async def process_onboarding(request: OnboardingRequest, background_tasks: BackgroundTasks):
    if not request.competitorIds and not request.orgId:
        raise HTTPException(status_code=400, detail="Must provide competitorIds or orgId")

    background_tasks.add_task(run_onboarding_logic, request.competitorIds, request.orgId, request.jobId)
    return {"message": "Onboarding started in background"}

@app.post("/refresh-news", status_code=202)
async def refresh_news(request: RefreshNewsRequest, background_tasks: BackgroundTasks):
    if not request.orgId:
        raise HTTPException(status_code=400, detail="Must provide orgId")

    background_tasks.add_task(run_refresh_logic, request.orgId, request.jobId, request.days, request.competitorName)
    return {"message": "News refresh started in background"}
