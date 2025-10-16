"""LangGraph workflow assembly extracted from the notebook."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Union

from langchain.agents import AgentExecutor
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime
from src.core.prompts import (
    budget_estimate_prompt, 
    research_plan_prompt, 
    lodging_research_prompt, 
    activities_research_prompt, 
    food_research_prompt, 
    intercity_transport_research_prompt, 
    recommendations_research_prompt,
    final_plan_prompt,
)
from src.core.schemas import (
    ActivitiesAgentOutput,
    BudgetEstimate,
    CandidateIntercityTransport,
    CandidateLodging,
    FinalPlan,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    LodgingAgentOutput,
    RecommendationsOutput,
    ResearchPlan,
    Context,
    State,
    CandidateActivity,
    CandidateFood,
    CandidateResearch,
    Traveller,
)
from src.services.geocoding import get_coordinates_nominatim
import logging
import asyncio
from src.core.post_processing import create_pydantic_hook
from langgraph.types import interrupt

logger = logging.getLogger(__name__)

def make_traveller_context(travellers: List[Traveller]) -> str:
    """Make the traveller context for the prompt."""
    traveller_context = ""
    if travellers:
        for traveller in travellers:
            context_parts = [traveller.name, f"age: {traveller.age_group}"]
            
            if traveller.interests:
                context_parts.append(f"interests: {', '.join(traveller.interests)}")
            if traveller.nationality:
                context_parts.append(f"nationality: {traveller.nationality}")
            if traveller.spoken_languages:
                context_parts.append(f"languages: {', '.join(traveller.spoken_languages)}")
                
            traveller_context += f"- {' | '.join(context_parts)}\n"
    return traveller_context

def _extract_agent_output(
    response: Dict[str, Any],
    *,
    key: str,
    default,
) -> Dict[str, Any]:
    """Normalise agent responses into the shared node contract."""

    logger.debug(f"Agent response: {response}")

    payload = response.get("structured_response", default)
    messages = response.get("messages", [AIMessage(content="Empty response")])

    logger.info(f"Agent output: {payload}")
    logger.debug(f"Agent output type: {type(payload)}")

    return {"messages": messages, key: payload}

async def make_research(prompt: str, agent: AgentExecutor, name: str, default: Any):
    """Generic research function for all agent types."""
    
    try:
        agent_input = {'messages': [HumanMessage(content=prompt.strip(), name=name)]}
        logger.debug(f"{name} agent input: {agent_input}")
        
        response = await agent.ainvoke(agent_input)

        raw_output: str | None = None
        response_messages = response.get("messages", []) if isinstance(response, dict) else []

        if isinstance(response_messages, list):
            for message in reversed(response_messages):
                if isinstance(message, AIMessage):
                    content = message.content
                    if isinstance(content, str):
                        raw_output = content
                    elif isinstance(content, dict):
                        try:
                            raw_output = json.dumps(content)
                        except (TypeError, ValueError):
                            raw_output = str(content)
                    elif isinstance(content, list):
                        serialised: str | None = None
                        try:
                            serialised = json.dumps(content)
                        except (TypeError, ValueError):
                            text_chunks: List[str] = []
                            for chunk in content:
                                if isinstance(chunk, dict) and chunk.get("type") == "text":
                                    text_chunks.append(chunk.get("text", ""))
                                elif isinstance(chunk, str):
                                    text_chunks.append(chunk)
                            if text_chunks:
                                serialised = "\n".join(text_chunks)
                        raw_output = serialised
                    elif content is not None:
                        raw_output = str(content)
                    break

        hook = create_pydantic_hook(name)
        processed_response = hook.convert(response, raw_output=raw_output)
        output = {"messages": response.get("messages", [AIMessage(content="Empty response")]), "structured_response": processed_response}
        logger.debug(f"{name} agent response: {output}")
        return _extract_agent_output(output, key=name, default=default)
        
    except Exception as e:
        logger.error(f"Error invoking {name} agent: {e}")

        logger.warning(f"Returning default for {name} due to error")
        return {"messages": [AIMessage(content=f"Error: {e}")], name: default}


def make_budget_estimate_node(llm: BaseChatModel):
    """Return the budget estimation node bound to the provided LLM."""

    structured_llm = llm.with_structured_output(BudgetEstimate)


    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        traveller_context = make_traveller_context(runtime.context.travellers)

        prompt = budget_estimate_prompt.format(
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            budget=runtime.context.budget,
            currency=runtime.context.currency,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            current_location=runtime.context.current_location or 'Not specified',
            traveller_context=traveller_context,
            notes=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )
        try:
            budget = await structured_llm.ainvoke(prompt)
        except Exception as e:
            logger.error(f"Error invoking budget estimate node: {e}")
            raise e
        
        return {
            "messages": [
                AIMessage(
                    content=f"Estimated budget: {budget.model_dump_json()}",
                    name="budget_estimate",
                )
            ],
            "estimated_budget": budget,
        }

    return node


def make_research_plan_node(llm: BaseChatModel):
    """Return the research planning node bound to the LLM."""

    structured_llm = llm.with_structured_output(ResearchPlan)

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        traveller_context = make_traveller_context(runtime.context.travellers)
        prompt = research_plan_prompt.format(
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            adults_num=runtime.context.adults_num if runtime.context.adults_num else 0,
            children_num=runtime.context.children_num if runtime.context.children_num else 0,
            infant_num=runtime.context.infant_num if runtime.context.infant_num else 0,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            budget_level=state.estimated_budget.budget_level if state.estimated_budget else '$$',
            total_budget=state.estimated_budget.total if state.estimated_budget else runtime.context.budget,
            currency=runtime.context.currency,
            intercity_transport=state.estimated_budget.intercity_transport if state.estimated_budget else 0,
            local_transport=state.estimated_budget.local_transport if state.estimated_budget else 0,
            food=state.estimated_budget.food if state.estimated_budget else 0,
            activities=state.estimated_budget.activities if state.estimated_budget else 0,
            lodging=state.estimated_budget.lodging if state.estimated_budget else 0,
            other=state.estimated_budget.other if state.estimated_budget else 0,
            traveller_context=traveller_context,    
            additional_context=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )
        try:
            coordinates_task = get_coordinates_nominatim(
            f"{runtime.context.destination}, {runtime.context.destination_country}"
        )
            plan_task = structured_llm.ainvoke(prompt)

            coordinates, plan = await asyncio.gather(coordinates_task, plan_task)
        except Exception as e:
            logger.error(f"Error invoking research plan node: {e}")
            raise e
        
        
        return {
            "messages": [
                AIMessage(
                    content=f"Research plan: {plan.model_dump_json()}",
                    name="research_plan",
                )
            ],
            "research_plan": plan,
            "destination_coordinates": coordinates,
        }

    return node


def make_lodging_node(agent: AgentExecutor):
    """Return an async node that orchestrates lodging research."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        candidates = state.research_plan.lodging_candidates if state.research_plan else None
        traveller_context = make_traveller_context(runtime.context.travellers)

        prompt = lodging_research_prompt.format(
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            adults_num=runtime.context.adults_num if runtime.context.adults_num else 0,
            children_num=runtime.context.children_num if runtime.context.children_num else 0,
            infant_num=runtime.context.infant_num if runtime.context.infant_num else 0,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            lodging_budget=state.estimated_budget.lodging if state.estimated_budget else runtime.context.budget * 0.3,
            currency=runtime.context.currency,
            traveller_context=traveller_context,
            candidates_number=candidates.candidates_number if candidates and candidates.candidates_number else 4,
            research_name=candidates.name if candidates and candidates.name else "Lodging Research",
            research_description=candidates.description if candidates and candidates.description else "Find suitable accommodations",
            additional_context=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )

        default = LodgingAgentOutput(lodging=[])
        return await make_research(prompt, agent, "lodging", default)

    return node


def make_activities_node(agent: AgentExecutor):
    """Create the activities research node used in the LangGraph flow."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        traveller_context = make_traveller_context(runtime.context.travellers)
        candidates = state.research_plan.activities_candidates if state.research_plan else None
        prompt = activities_research_prompt.format(
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            adults_num=runtime.context.adults_num if runtime.context.adults_num else 0,
            children_num=runtime.context.children_num if runtime.context.children_num else 0,
            infant_num=runtime.context.infant_num if runtime.context.infant_num else 0,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            activities_budget=state.estimated_budget.activities if state.estimated_budget else runtime.context.budget * 0.2,
            currency=runtime.context.currency,
            traveller_context=traveller_context,
            candidates_number=candidates.candidates_number if candidates and candidates.candidates_number else 5,
            research_name=candidates.name if candidates and candidates.name else "Activities Research",
            research_description=candidates.description if candidates and candidates.description else "Find engaging activities and attractions",
            additional_context=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )

    
        default = ActivitiesAgentOutput(activities=[])
        return await make_research(prompt, agent, "activities", default)

    return node


def make_food_node(agent: AgentExecutor):
    """Produce the food research node that queries the cuisine agent."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        candidates = state.research_plan.food_candidates if state.research_plan else None
        traveller_context = make_traveller_context(runtime.context.travellers)

        prompt = food_research_prompt.format(
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            adults_num=runtime.context.adults_num if runtime.context.adults_num else 0,
            children_num=runtime.context.children_num if runtime.context.children_num else 0,
            infant_num=runtime.context.infant_num if runtime.context.infant_num else 0,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            food_budget=state.estimated_budget.food if state.estimated_budget else runtime.context.budget * 0.3,
            currency=runtime.context.currency,
            traveller_context=traveller_context,
            candidates_number=candidates.candidates_number if candidates and candidates.candidates_number else 4,
            research_name=candidates.name if candidates and candidates.name else "Food Research",
            research_description=candidates.description if candidates and candidates.description else "Find suitable food",
            additional_context=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )
        default = FoodAgentOutput(food=[])
        return await make_research(prompt, agent, "food", default)

    return node


def make_intercity_transport_node(agent: AgentExecutor):
    """Assemble the LangGraph node responsible for intercity transport."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        candidates = state.research_plan.intercity_transport_candidates if state.research_plan else None
        traveller_context = make_traveller_context(runtime.context.travellers)

        prompt = intercity_transport_research_prompt.format(
            current_location=runtime.context.current_location or 'Origin not specified',
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            adults_num=runtime.context.adults_num if runtime.context.adults_num else 0,
            children_num=runtime.context.children_num if runtime.context.children_num else 0,
            infant_num=runtime.context.infant_num if runtime.context.infant_num else 0,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            intercity_budget=state.estimated_budget.intercity_transport if state.estimated_budget else runtime.context.budget * 0.4,
            currency=runtime.context.currency,
            traveller_context=traveller_context,
            candidates_number=candidates.candidates_number if candidates and candidates.candidates_number else 3,
            research_name=candidates.name if candidates and candidates.name else "Intercity Transport Research",
            research_description=candidates.description if candidates and candidates.description else "Find transportation options between cities",
            additional_context=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )
       
        default = IntercityTransportAgentOutput(intercity_transport=[])
        return await make_research(prompt, agent, "intercity_transport", default)

    return node


def make_recommendations_node(agent: AgentExecutor):
    """Build the advisory node that aggregates safety and culture notes."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        traveller_context = make_traveller_context(runtime.context.travellers)
        prompt = recommendations_research_prompt.format(
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            adults_num=runtime.context.adults_num if runtime.context.adults_num else 0,
            children_num=runtime.context.children_num if runtime.context.children_num else 0,
            infant_num=runtime.context.infant_num if runtime.context.infant_num else 0,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            traveller_context=traveller_context,
            research_name="Travel Recommendations and Cultural Advice",
            research_description="Provide comprehensive travel recommendations covering safety, culture, and practical information",
            additional_context=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )
        default = RecommendationsOutput()
        return await make_research(prompt, agent, "recommendations", default)

    return node


def make_planner_node(llm: BaseChatModel):
    """Create the planner node that synthesises all research into a plan."""

    structured_llm = llm.with_structured_output(FinalPlan)

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        traveller_context = make_traveller_context(runtime.context.travellers)
        # Define the prompt
        research_result = "AVAILABLE RESEARCH RESULTS:\n\n"
                
        if state.activities and state.activities.activities:
            research_result+= state.activities.model_dump_json()
        
        if state.food and state.food.food:
            research_result+= state.food.model_dump_json()

        prompt = final_plan_prompt.format(
            destination=runtime.context.destination,
            destination_country=runtime.context.destination_country,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            days_number=runtime.context.days_number,
            group_type=runtime.context.group_type,
            adults_num=runtime.context.adults_num if runtime.context.adults_num else 0,
            children_num=runtime.context.children_num if runtime.context.children_num else 0,
            infant_num=runtime.context.infant_num if runtime.context.infant_num else 0,
            trip_purpose=runtime.context.trip_purpose or 'General travel',
            total_budget=state.estimated_budget.total if state.estimated_budget else runtime.context.budget,
            currency=runtime.context.currency,
            traveller_context=traveller_context,
            research_results_summary=research_result,
            additional_context=f"ADDITIONAL CONTEXT: {runtime.context.notes}" if runtime.context.notes else ""
        )
        try:
            planner = await structured_llm.ainvoke(prompt)

            if state.lodging and state.lodging.lodging:
                planner.lodging = state.lodging.lodging
            
            if state.intercity_transport and state.intercity_transport.intercity_transport:
                planner.intercity_transport = state.intercity_transport.intercity_transport

            if state.recommendations:
                planner.recommendations = state.recommendations

            planner.currency = runtime.context.currency
            logger.debug(f"Final plan: {planner}")
        except Exception as e:
            logger.error(f"Error invoking planner: {e}")
            raise e
        

        return {
            "messages": [
                HumanMessage(content=f"Prompt: {prompt}", name="planner_prompt"),
                AIMessage(content=f"Final plan: {planner}", name="final_plan")
            ],
            "final_plan": planner,
        }

    return node


def make_combined_human_review_node():
    """Return a node that pauses execution to collect human selections."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        """Single node that handles both lodging and transport selection"""
        
        interrupts_needed = []

        if state.lodging and state.lodging.lodging:
            interrupts_needed.append({
                "type": "lodging",
                "task": "Choose lodging option",
                "options": [lodging.model_dump() for lodging in state.lodging.lodging]
            })

        if state.intercity_transport and state.intercity_transport.intercity_transport:
            interrupts_needed.append({
                "type": "intercity_transport",
                "task": "Choose intercity_transport option",
                "options": [transport.model_dump() for transport in state.intercity_transport.intercity_transport]
            })

        if state.activities and state.activities.activities:
            interrupts_needed.append({
                "type": "activities",
                "task": "Choose activity option",
                "options": [activity.model_dump() for activity in state.activities.activities]
            })

        if state.food and state.food.food:
            interrupts_needed.append({
                "type": "food",
                "task": "Choose food option",
                "options": [food.model_dump() for food in state.food.food]
            })


        # Import interrupt RIGHT BEFORE using it to avoid namespace conflicts
        

        # This will either:
        # 1. Pause execution on first run (and store interrupt data)
        # 2. Return the resume data when resumed
        result = interrupt({
            "task": "Make your selections for the following options",
            "selections": interrupts_needed,
            "research_plan": state.research_plan.model_dump() if state.research_plan else None
        })

        # This code runs AFTER resume
        # Initialize response with a message
        
        response = {"messages": [HumanMessage(content="Human review completed")]}

        # Handle research_plan if it's in the result
        if "research_plan" in result and result["research_plan"]:
            
            research_plan_dict = result["research_plan"]
            research_plan_data = {}

            # Convert each category to CandidateResearch objects
            for category_key, category_data in research_plan_dict.items():
                if category_data:
                    research_plan_data[category_key] = CandidateResearch(**category_data)

            # Create ResearchPlan and convert to dict for state update
            research_plan = ResearchPlan(**research_plan_data)
            response["research_plan"] = research_plan.model_dump()
        else:
            response["research_plan"] = None

        # Handle activities - could be single dict or list of dicts
        if "activities" in result and result["activities"]:
            activities_data = result["activities"]
            # Ensure it's a list
            if isinstance(activities_data, dict):
                activities_data = [activities_data]
            selected_activities = [CandidateActivity(**activity) for activity in activities_data]
            response["activities"] = ActivitiesAgentOutput(activities=selected_activities).model_dump()

        # Handle food - could be single dict or list of dicts
        if "food" in result and result["food"]:
            food_data = result["food"]
            # Ensure it's a list
            if isinstance(food_data, dict):
                food_data = [food_data]
            selected_foods = [CandidateFood(**food_item) for food_item in food_data]
            response["food"] = FoodAgentOutput(food=selected_foods).model_dump()

        # Handle lodging - expecting single dict but wrap in list for LodgingAgentOutput
        if "lodging" in result and result["lodging"]:
            lodging_data = result["lodging"]
            # Ensure it's a list for the output model
            if isinstance(lodging_data, dict):
                lodging_data = [lodging_data]
            selected_lodgings = [CandidateLodging(**lodging) for lodging in lodging_data]
            response["lodging"] = LodgingAgentOutput(lodging=selected_lodgings).model_dump()

        # Handle intercity_transport - expecting single dict but wrap in list for IntercityTransportAgentOutput
        if "intercity_transport" in result and result["intercity_transport"]:
            transport_data = result["intercity_transport"]
            # Ensure it's a list for the output model
            if isinstance(transport_data, dict):
                transport_data = [transport_data]
            selected_transport = [CandidateIntercityTransport(**transport) for transport in transport_data]
            response["intercity_transport"] = IntercityTransportAgentOutput(intercity_transport=selected_transport).model_dump()

        return response

    return node


def route_from_human_response(state: State, runtime: Runtime[Context]) -> Union[str, List[str]]:
    """Returns a list of nodes to execute in parallel based on conditions"""
    nodes_to_execute = []
    if not state.research_plan:
        return "planner"

    research_plan = state.research_plan

    # Direct attribute access (works if these are Optional[bool] fields)
    if research_plan.activities_candidates:
        nodes_to_execute.append("research_activities")

    if research_plan.food_candidates:
        nodes_to_execute.append("research_food")

    if research_plan.lodging_candidates:
        nodes_to_execute.append("research_lodging")

    if research_plan.intercity_transport_candidates:
        nodes_to_execute.append("research_intercity_transport")

    return nodes_to_execute if nodes_to_execute else "planner"
