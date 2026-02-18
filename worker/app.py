
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

async def run_onboarding_logic(competitor_ids: Optional[List[str]], org_id: Optional[str]):
    # Mock args object to pass to existing main logic or call functions directly
    # Ideally, refactor onboarding_agent.main() to accept args directly, but for now we can call the processing logic
    
    # We need to replicate what main() does
    try:
        logger.info(f"Worker starting onboarding for orgId={org_id} competitors={competitor_ids}")
        
        conn = onboarding_agent.get_db_connection()
        cursor = conn.cursor()
        
        competitors = []
        if competitor_ids:
            # Need to format for SQL "ANY"
            cursor.execute("SELECT * FROM \"Competitor\" WHERE id = ANY(%s)", (competitor_ids,))
            competitors = cursor.fetchall()
        elif org_id:
            cursor.execute("SELECT * FROM \"Competitor\" WHERE \"organizationId\" = %s", (org_id,))
            competitors = cursor.fetchall()
        
        conn.close()
        
        if not competitors:
            logger.warning("No competitors found for worker task")
            return

        for comp in competitors:
            try:
                await onboarding_agent.process_competitor(comp)
            except Exception as e:
                logger.error(f"Error processing competitor {comp.get('name')}: {e}")
                
        logger.info("Worker task completed successfully")
        
    except Exception as e:
        logger.error(f"Worker task failed: {e}")

@app.post("/process-onboarding", status_code=202)
async def process_onboarding(request: OnboardingRequest, background_tasks: BackgroundTasks):
    if not request.competitorIds and not request.orgId:
        raise HTTPException(status_code=400, detail="Must provide competitorIds or orgId")
    
    background_tasks.add_task(run_onboarding_logic, request.competitorIds, request.orgId)
    return {"message": "Onboarding started in background"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
