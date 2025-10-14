from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import Tool
from typing import Sequence
from src.core.schemas import ResearchAgents, LodgingAgentOutput, ActivitiesAgentOutput, FoodAgentOutput, IntercityTransportAgentOutput, RecommendationsOutput


def build_research_agents(
    llm: BaseChatModel,
    *,
    comprehensive_search_tool: Tool,
    flight_search_tool: Tool,
    search_tools: Sequence[Tool],
) -> ResearchAgents:
    """Instantiate the REACT agents required by the workflow."""

    from langgraph.prebuilt import create_react_agent

    return ResearchAgents(
        lodging=create_react_agent(
            llm,
            tools=[comprehensive_search_tool],
            debug=True,
            response_format=LodgingAgentOutput,
        ),
        activities=create_react_agent(
            llm,
            tools=[comprehensive_search_tool],
            debug=True,
            response_format=ActivitiesAgentOutput,
        ),
        food=create_react_agent(
            llm,
            tools=[comprehensive_search_tool],
            debug=True,
            response_format=FoodAgentOutput,
        ),
        intercity_transport=create_react_agent(
            llm,
            tools=[flight_search_tool],
            debug=True,
            response_format=IntercityTransportAgentOutput,
        ),
        recommendations=create_react_agent(
            llm,
            tools=list(search_tools),
            debug=True,
            response_format=RecommendationsOutput,
        ),
    )
