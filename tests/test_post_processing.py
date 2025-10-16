import json
from dataclasses import dataclass

import pytest

from src.core.post_processing import PydanticPostModelHook, create_pydantic_hook
from src.core.schemas import (
    ActivitiesAgentOutput,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    LodgingAgentOutput,
    RecommendationsOutput,
)


@dataclass
class _FakeGeneration:
    text: str | None


@dataclass
class _FakeResponse:
    generations: list[list[_FakeGeneration]]


def test_create_hook_rejects_unknown_type():
    with pytest.raises(ValueError):
        create_pydantic_hook("unknown")


@pytest.mark.parametrize(
    "output_type, raw_payload, expected_cls, collection_attr",
    [
        (
            "lodging",
            {"lodging": [{"id": "h-1", "name": "Lakeside Hotel"}]},
            LodgingAgentOutput,
            "lodging",
        ),
        (
            "activities",
            {"activities": [{"id": "a-1", "name": "Temple Tour"}]},
            ActivitiesAgentOutput,
            "activities",
        ),
        (
            "food",
            {"food": [{"id": "f-1", "name": "Sushi Place"}]},
            FoodAgentOutput,
            "food",
        ),
        (
            "intercity_transport",
            {
                "intercity_transport": [
                    {
                        "name": "Shinkansen",
                        "transfer": [
                            {"name": "Tokyo Station", "place": "Tokyo"}
                        ],
                    }
                ]
            },  
            IntercityTransportAgentOutput,
            "intercity_transport",
        ),
        (
            "recommendations",
            {"safety_level": "safe", "safety_notes": ["Stay alert at night"]},
            RecommendationsOutput,
            None,
        ),
    ],
)
def test_on_chain_end_converts_json_payload(output_type, raw_payload, expected_cls, collection_attr):
    hook = create_pydantic_hook(output_type)

    outputs = {"structured_response": None}
    result = hook.on_chain_end(outputs, raw_output=json.dumps(raw_payload))

    converted = outputs["structured_response"]
    assert converted is result
    assert isinstance(converted, expected_cls)

    if collection_attr:
        items = getattr(converted, collection_attr)
        assert len(items) == 1
        assert getattr(items[0], "name") in {"Lakeside Hotel", "Temple Tour", "Sushi Place", "Shinkansen"}
        if output_type == "intercity_transport":
            assert items[0].transfer and items[0].transfer[0].name == "Tokyo Station"
    else:
        assert converted.safety_level == "safe"


def test_on_chain_end_skips_invalid_candidates():
    hook = create_pydantic_hook("activities")
    raw_payload = json.dumps(
        {
            "activities": [
                {"name": "Valid Activity"},
                {"id": "missing-name"},  # should be skipped
            ]
        }
    )

    outputs = {"structured_response": None}
    result = hook.on_chain_end(outputs, raw_output=raw_payload)

    converted = outputs["structured_response"]
    assert converted is result
    assert isinstance(converted, ActivitiesAgentOutput)
    assert len(converted.activities) == 1
    assert converted.activities[0].name == "Valid Activity"


def test_on_chain_end_ignores_when_no_raw_output():
    hook = create_pydantic_hook("lodging")
    outputs = {"structured_response": None}

    result = hook.on_chain_end(outputs)  # raw_output defaults to None

    assert outputs["structured_response"] is None
    assert result is None


def test_on_chain_start_resets_previous_raw_output():
    hook = create_pydantic_hook("food")
    hook.raw_output = "stale"
    hook.on_chain_start()
    assert hook.raw_output is None


def test_on_llm_end_captures_text_generation():
    hook = create_pydantic_hook("lodging")
    hook.on_llm_end(_FakeResponse(generations=[[ _FakeGeneration(text="payload") ]]))
    assert hook.raw_output == "payload"


def test_on_llm_end_ignores_non_text_generation():
    @dataclass
    class _NoText:
        pass

    hook = create_pydantic_hook("lodging")
    hook.raw_output = None
    hook.on_llm_end(_FakeResponse(generations=[[ _NoText() ]]))
    assert hook.raw_output is None


def test_on_chain_end_leaves_response_none_for_invalid_json():
    hook = create_pydantic_hook("lodging")

    outputs = {"structured_response": None}
    result = hook.on_chain_end(outputs, raw_output="not json")

    assert outputs["structured_response"] is None
    assert result is None


def test_convert_returns_parsed_output():
    hook = create_pydantic_hook("food")
    response = {"structured_response": None, "output": json.dumps({"food": [{"name": "Cafe 21"}]})}

    result = hook.convert(response)

    assert isinstance(result, FoodAgentOutput)
    assert result.food[0].name == "Cafe 21"
