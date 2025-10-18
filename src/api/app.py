"""FastAPI surface for the trip planner agentic workflow."""
from __future__ import annotations

import os
# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file before any other imports that might need environment variables
load_dotenv()


from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from src.api.schemas import PlanRequest, PlanningResponse, ExtraResearchRequest, FinalPlanRequest
import logging
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencies import lifespan, get_workflow_bundle
from src.api.response_builder import _result_to_response

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised through import side effects
    import sentry_sdk
except ImportError:  # pragma: no cover - only triggers in lean environments
    sentry_sdk = None  # type: ignore[assignment]
else:  # pragma: no cover - runtime configuration
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        enable_logs=True,
        send_default_pii=True,
        traces_sample_rate=1.0,
    )

app = FastAPI(title="Trip Planner API", version="0.1.0", lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "http://localhost:3001"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/plan/start", response_model=PlanningResponse)
async def start_planning(payload: PlanRequest) -> PlanningResponse:
    """Start the AI-powered trip planning workflow.
    
    This endpoint initiates the LangGraph-based trip planning process that coordinates
    multiple specialized agents to research and create a personalized itinerary.
    
    The workflow includes:
    - Budget estimation based on destination and travel dates
    - Research planning to determine candidate counts for each category
    - Parallel research by specialized agents (lodging, activities, food, transport)
    - Human-in-the-loop selection process when multiple options are found
    - Final itinerary synthesis
    
    Args:
        payload: Contains the trip context including destination, dates, budget,
                traveller information, and optional thread_id and user_prompt.
                
    Returns:
        PlanningResponse containing:
        - status: Current workflow state ("interrupt", "complete", "needs_follow_up", "no_plan")
        - config: LangGraph configuration with thread_id for resuming
        - estimated_budget: AI-generated budget breakdown by category
        - research_plan: Research strategy for each category
        - agent_outputs: Results from research agents (lodging, activities, etc.)
        - interrupt: Selection options when status is "interrupt"
        - final_plan: Complete itinerary when status is "complete"
        
    Raises:
        HTTPException: 400 for invalid input, 500 for workflow errors
        
    Example JSON payload:
        ```json
        {
            "travellers": [
                {
                    "name": "John",
                    "date_of_birth": "1990-01-01",
                    "spoken_languages": ["english"],
                    "interests": ["culture"]
                }
            ],
            "budget": 1000,
            "currency": "USD",
            "current_location": "Seoul",
            "destination": "Tokyo",
            "destination_country": "Japan",
            "date_from": "2025-10-01",
            "date_to": "2025-10-05",
            "group_type": "alone",
            "trip_purpose": "cultural experience"
        }
        ```
    """

    logger.info("Starting new trip planning request")
    logger.info(f"Destination: {payload.destination}, {payload.destination_country}")
    logger.info(f"Budget: {payload.budget} {payload.currency}")
    logger.info(f"Travel dates: {payload.date_from} to {payload.date_to}")
    logger.info(f"Group size: {payload.adults_num} adults, {payload.children_num} children")
    
    bundle = get_workflow_bundle()
    try:
        config, result = await bundle.plan_trip(
            context=payload
        )
        logger.info("Plan_trip workflow completed successfully")
        logger.debug(f"Result keys: {list(result.keys()) if result else 'None'}")
        logger.info("Converting result to response")

    except RuntimeError as exc:
        logger.error(f"Runtime error during plan: {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        logger.error(f"Value error during plan: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc: 
        logger.error(f"Unexpected error during plan: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _result_to_response(config, result)
    
@app.post("/plan/extra_research", response_model=PlanningResponse)
async def extra_research(payload: ExtraResearchRequest) -> PlanningResponse:
    """Perform extra research for the trip planning workflow."""
    logger.info("Extra research request received")
    logger.debug("Payload: {payload}", payload=payload)

    bundle = get_workflow_bundle()
    try:
        config, result = await bundle.extra_research(
            config=payload.config,
            research_plan=payload.research_plan,
        )
        logger.info("Extra research workflow completed successfully")
        logger.debug("Result: {result}", result=result)
    except ValueError as exc:
        logger.error(f"Value error during extra research: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Unexpected error during extra research: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    
    logger.info("Converting result to response")    
    return _result_to_response(config, result)

@app.post("/plan/final_plan", response_model=PlanningResponse)
async def final_plan(payload: FinalPlanRequest) -> PlanningResponse:
    """Generate the final plan for the trip planning workflow."""
    logger.info("Final plan request received")
    logger.debug("Payload: {payload}", payload=payload)
    
    bundle = get_workflow_bundle()
    try:
        config, result = await bundle.final_plan(
            config=payload.config,
            selections=payload.selections,
        )
        logger.info("Final plan workflow completed successfully")   
        logger.debug("Result: {result}", result=result)
    except Exception as exc:
        logger.error(f"Unexpected error during final plan: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    
    logger.info("Converting result to response")
    response = _result_to_response(config, result)
    logger.debug("Final plan response: {response}", response=response)
    return response

@app.post("/plan/cleanup_threads", response_model=int)
async def cleanup_threads() -> int:
    """Cleanup old threads from the workflow."""
    logger.info("Cleanup threads request received")
    bundle = get_workflow_bundle()
    try:
        return bundle.cleanup_old_threads()
    except Exception as exc:
        logger.error(f"Unexpected error during cleanup threads: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    

@app.get("/sentry-debug")
async def trigger_error():
    raise RuntimeError("This is a test error")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health endpoint used for readiness probes."""

    return {"status": "healthy", "service": "trip-planner-api"}


@app.get("/workflow/info")
async def get_workflow_info() -> Dict[str, Any]:
    """Get detailed information about the workflow configuration."""
    bundle = get_workflow_bundle()
    
    return {
        'workflow_info': {
            'llm_model': getattr(bundle.llm, 'model_name', type(bundle.llm).__name__),
            'recursion_limit': bundle.recursion_limit,
            'active_threads': len(bundle._contexts),
            'pending_interrupts': len(bundle._pending_interrupts)
        }
    }
