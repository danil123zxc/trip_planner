"""FastAPI surface for the trip planner agentic workflow."""
from __future__ import annotations

import os
# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file before any other imports that might need environment variables
load_dotenv()


from typing import Dict
from fastapi import FastAPI, HTTPException
from src.api.schemas import PlanRequest, ResumeRequest, PlanningResponse
import sentry_sdk
import logging

from src.api.dependencies import lifespan, get_workflow_bundle
from src.api.response_builder import _result_to_response

logger = logging.getLogger(__name__)

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    enable_logs=True,
    send_default_pii=True,
    traces_sample_rate=1.0,
)

app = FastAPI(title="Trip Planner API", version="0.1.0", lifespan=lifespan)


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
        
    Example:
        POST /plan/start with:
        ```json
        {
            "context": {
                "destination": "Tokyo, Japan",
                "date_from": "2025-10-01",
                "date_to": "2025-10-05",
                "budget": 1000,
                "currency": "USD",
                "group_type": "alone",
                "travellers": [{"name": "John", "date_of_birth": "1990-01-01"}]
            }
        }
        ```
    ```json
        {
            "context": 
            {
                "travellers": [
                {
                    "name": "Danil",
                    "date_of_birth": "2002-09-29",
                    "spoken_languages": [
                    "english"
                    ],
                    "interests": [
                    "active sports"
                    ],
                    "nationality": "russian"      }
                ],
                "budget": 1000,
                "currency": "USD",
                "destination": "Tokyo",
                "destination_country": "Japan",
                "date_from": "2025-10-01",
                "date_to": "2025-10-05",
                "group_type": "alone",
                "trip_purpose": "cultural experience",
                "current_location": "Seoul"
            }
        }
    ```
    """

    logger.info("Starting new trip planning request")
    logger.info(f"Destination: {payload.context.destination}, {payload.context.destination_country}")
    logger.info(f"Budget: {payload.context.budget} {payload.context.currency}")
    logger.info(f"Travel dates: {payload.context.date_from} to {payload.context.date_to}")
    logger.info(f"Group size: {payload.context.adults_num} adults, {payload.context.children_num} children")
    
    bundle = get_workflow_bundle()
    try:
        config, result = await bundle.plan_trip(
            context=payload.context
        )
        logger.info("Plan_trip workflow completed successfully")
        logger.debug(f"Result keys: {list(result.keys()) if result else 'None'}")
        logger.info("Converting result to response")
    except RuntimeError as exc:
        logger.error(f"Runtime error during plan: {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguards unexpected graph failures
        logger.error(f"Unexpected error during plan: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _result_to_response(config, result)
    

@app.post("/plan/resume", response_model=PlanningResponse)
async def resume_planning(payload: ResumeRequest) -> PlanningResponse:
    """Resume the trip planning workflow after user selections.
    
    This endpoint continues the planning workflow from where it was interrupted,
    incorporating user selections for lodging, activities, food, and transport options.
    The workflow will proceed to generate the final itinerary or request additional
    selections if needed.
    
    The resume process:
    - Uses the provided config to restore the workflow state
    - Applies user selections to filter down to chosen options
    - Continues with final planning and itinerary generation
    - Can handle research plan overrides for additional research
    
    Args:
        payload: Contains:
            - config: LangGraph configuration with thread_id from previous response
            - selections: User choices for each category (indices or objects)
            - research_plan: Optional overrides for additional research
            
    Returns:
        PlanningResponse with updated workflow state:
        - status: "interrupt" for more selections needed, "complete" for final plan
        - final_plan: Complete day-by-day itinerary when status is "complete"
        - Additional agent outputs and selections as needed
        
    Raises:
        HTTPException: 400 for invalid thread_id or selections, 500 for workflow errors
        
    Note:
        - If config is None, creates a new planning session with provided selections
        - Selections can be indices (integers) or full candidate objects
        - Research plan overrides allow requesting additional candidates
        
    Example:
        POST /plan/resume with:
        ```json
        {
            "config": {"configurable": {"thread_id": "trip_123"}},
            "selections": {
                "lodging": 0,
                "activities": [0, 1, 2],
                "food": [0, 1],
                "intercity_transport": 0
            }
        }
        ```
    """

    logger.info("Resume planning request received")
    logger.debug("Payload config: {config}", config=payload.config)
    logger.debug("Payload selections: {selections}", selections=payload.selections)
    logger.debug("Payload research_plan: {plan}", plan=payload.research_plan)

    bundle = get_workflow_bundle()
    try:
        logger.info("Starting resume_trip workflow")
        config, result = await bundle.resume_trip(
            context=payload.context,
            config=payload.config,
            selections=payload.selections,
            research_plan=payload.research_plan,
        )
        logger.info("Resume_trip workflow completed successfully")
        logger.debug("Result: {result}", result=result)

    except RuntimeError as exc:
        logger.error(f"Runtime error during resume: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguards unexpected graph failures
        logger.error(f"Unexpected error during resume: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Converting result to response")
    response = _result_to_response(config, result)
    logger.info("Resume planning completed successfully")
    return response  

@app.get("/sentry-debug")
async def trigger_error():
    raise RuntimeError("This is a test error")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health endpoint used for readiness probes."""

    return {"status": "healthy", "service": "trip-planner-api"}

