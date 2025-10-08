from typing import Any, Dict, List, Mapping, Optional, Literal
from langchain_core.messages import BaseMessage
from src.api.schemas import PlanningResponse


def _messages_to_strings(result: Mapping[str, Any]) -> List[str]:
    raw_messages = result.get("messages", [])
    rendered: List[str] = []
    for message in raw_messages:
        if isinstance(message, BaseMessage):
            content = getattr(message, "content", None)
            if isinstance(content, str):
                rendered.append(content)
            else:
                rendered.append(repr(message))
        else:
            rendered.append(str(message))
    return rendered


def _extract_interrupt(result: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    raw = result.get("__interrupt__")
    if not raw:
        return None
    first = raw[0]
    payload = getattr(first, "value", first)
    if isinstance(payload, Mapping):
        return dict(payload)
    return None


def _determine_status(result: Mapping[str, Any]) -> Literal["interrupt", "complete", "needs_follow_up", "no_plan"]:
    if "__interrupt__" in result:
        return "interrupt"
    final_plan = result.get("final_plan")
    if final_plan and getattr(final_plan, "research_plan", None):
        return "needs_follow_up"
    if final_plan:
        return "complete"
    return "no_plan"


def _result_to_response(
    config: Dict[str, Any],
    result: Mapping[str, Any],
) -> PlanningResponse:
    status = _determine_status(result)
    interrupt_payload = _extract_interrupt(result)

    # Extract lodging list from nested structure
    lodging_data = result.get("lodging")
    lodging_list = None
    if lodging_data and hasattr(lodging_data, 'lodging'):
        lodging_list = lodging_data.lodging
    elif lodging_data and isinstance(lodging_data, dict) and 'lodging' in lodging_data:
        lodging_list = lodging_data['lodging']
    elif lodging_data and isinstance(lodging_data, list):
        lodging_list = lodging_data

    # Extract activities list from nested structure
    activities_data = result.get("activities")
    activities_list = None
    if activities_data and hasattr(activities_data, 'activities'):
        activities_list = activities_data.activities
    elif activities_data and isinstance(activities_data, dict) and 'activities' in activities_data:
        activities_list = activities_data['activities']
    elif activities_data and isinstance(activities_data, list):
        activities_list = activities_data

    # Extract food list from nested structure
    food_data = result.get("food")
    food_list = None
    if food_data and hasattr(food_data, 'food'):
        food_list = food_data.food
    elif food_data and isinstance(food_data, dict) and 'food' in food_data:
        food_list = food_data['food']
    elif food_data and isinstance(food_data, list):
        food_list = food_data

    # Extract intercity_transport list from nested structure
    transport_data = result.get("intercity_transport")
    transport_list = None
    if transport_data and hasattr(transport_data, 'transport'):
        transport_list = transport_data.transport
    elif transport_data and isinstance(transport_data, dict) and 'transport' in transport_data:
        transport_list = transport_data['transport']
    elif transport_data and isinstance(transport_data, list):
        transport_list = transport_data

    return PlanningResponse(    
        status=status,
        config=config,
        estimated_budget=result.get("estimated_budget"),
        research_plan=result.get("research_plan"),
        lodging=lodging_list,
        activities=activities_list,
        food=food_list,
        intercity_transport=transport_list,
        recommendations=result.get("recommendations"),
        final_plan=result.get("final_plan"),
        interrupt=interrupt_payload,
        messages=_messages_to_strings(result),
    )
