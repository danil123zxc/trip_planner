import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, TypeVar, Union

from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel, ValidationError

from src.core.schemas import (
    ActivitiesAgentOutput,
    CandidateActivity,
    CandidateFood,
    CandidateIntercityTransport,
    CandidateLodging,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    LodgingAgentOutput,
    RecommendationsOutput,
    Transfer,
)

logger = logging.getLogger(__name__)

CandidateModelT = TypeVar("CandidateModelT", bound=BaseModel)
_CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class PydanticPostModelHook(BaseCallbackHandler):
    """Post-model hook that converts raw LLM output into proper Pydantic models."""
    
    def __init__(self, output_type: str):
        self.output_type = output_type  # "lodging", "activities", "food", "intercity_transport", "recommendations"
        self.raw_output: Optional[str] = None

        if self.output_type not in {"lodging", "activities", "food", "intercity_transport", "recommendations"}:
            raise ValueError(f"Unsupported output_type '{self.output_type}' for PydanticPostModelHook")

    def on_chain_start(self, *args, **kwargs) -> None:
        """Reset captured state before each chain execution."""
        self.raw_output = None
    
    def on_llm_end(self, response, **kwargs):
        """Capture the raw LLM output."""
        generations = getattr(response, "generations", None)
        if not generations:
            logger.debug("No generations present in LLM response; skipping raw capture")
            return

        first_generation = generations[0][0] if generations and generations[0] else None
        text = getattr(first_generation, "text", None)
        if text is None:
            logger.debug("LLM generation does not contain text attribute; skipping raw capture")
            return

        self.raw_output = text
        logger.debug("Raw LLM output for %s: %s", self.output_type, self.raw_output)
    
    def on_chain_end(self, outputs: Dict[str, Any], *, raw_output: Optional[str] = None, **kwargs):
        """Convert raw output to Pydantic models when structured_response is None.

        Returns the structured response (original or converted) so callers can use the hook manually.
        """
        if raw_output is not None:
            self.raw_output = raw_output
        elif not self.raw_output:
            possible_raw = outputs.get("output")
            if isinstance(possible_raw, str):
                self.raw_output = possible_raw

        structured = outputs.get("structured_response")

        if structured is None and self.raw_output:
            logger.warning("Detected None structured_response for %s, attempting conversion...", self.output_type)
            
            # Try to convert raw output to proper Pydantic model
            converted_output = self._convert_to_pydantic_model(self.raw_output)
            if converted_output is not None:
                outputs["structured_response"] = converted_output
                structured = converted_output
            else:
                logger.error("Failed to convert %s raw output to Pydantic model", self.output_type)
        return structured

    def convert(self, response: Dict[str, Any], *, raw_output: Optional[str] = None) -> Optional[Any]:
        """Convert an agent response dict to a structured Pydantic model if possible."""
        structured = response.get("structured_response")
        if structured is not None:
            return structured

        if raw_output is None:
            possible_raw = response.get("output")
            if isinstance(possible_raw, str):
                raw_output = possible_raw

        outputs = {"structured_response": structured}
        return self.on_chain_end(outputs, raw_output=raw_output)

    def _convert_to_pydantic_model(self, raw_output: str) -> Optional[Any]:
        """Convert raw output to the appropriate Pydantic model."""
        try:
            # Extract JSON from raw output
            json_data = self._extract_json_from_output(raw_output)
            if json_data is None:
                return None
            
            # Convert based on output type
            if self.output_type == "lodging":
                return self._convert_to_lodging_output(json_data)
            elif self.output_type == "activities":
                return self._convert_to_activities_output(json_data)
            elif self.output_type == "food":
                return self._convert_to_food_output(json_data)
            elif self.output_type == "intercity_transport":
                return self._convert_to_intercity_transport_output(json_data)
            elif self.output_type == "recommendations":
                return self._convert_to_recommendations_output(json_data)
            
        except Exception as e:
            logger.exception("Error converting %s output: %s", self.output_type, e)
            return None
    
    def _extract_json_from_output(self, raw_output: str) -> Optional[Any]:
        """Extract JSON from raw LLM output with tolerant parsing of extra wrappers."""
        if not raw_output:
            return None

        candidates: List[str] = []
        stripped = raw_output.strip()
        if stripped:
            candidates.append(stripped)

        # Extract code-fenced JSON blocks if present (```json ... ```)
        for match in _CODE_BLOCK_PATTERN.finditer(raw_output):
            block = match.group(1).strip()
            if block:
                candidates.append(block)

        # Attempt to isolate the first JSON object/array within the text
        start_positions = [
            idx for idx in (stripped.find("{"), stripped.find("[")) if idx != -1
        ]
        if start_positions:
            start_idx = min(start_positions)
            opening_char = stripped[start_idx]
            closing_char = "}" if opening_char == "{" else "]"
            end_idx = stripped.rfind(closing_char)
            if end_idx != -1 and end_idx >= start_idx:
                candidates.append(stripped[start_idx : end_idx + 1].strip())

        last_error: Optional[json.JSONDecodeError] = None
        for candidate in dict.fromkeys(candidates):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue

        if last_error:
            logger.warning("Failed to parse raw LLM output as JSON: %s", last_error)
        return None
    
    def _build_output_from_items(
        self,
        json_data: Any,
        *,
        collection_key: Optional[Union[str, Sequence[str]]],
        candidate_model: Type[CandidateModelT],
        wrap_output: Type[BaseModel],
        item_transform: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        output_field: str,
    ) -> BaseModel:
        """Shared helper to build agent outputs while tolerating partial failures."""
        entries = self._normalise_collection(json_data, collection_key)
        candidates: List[CandidateModelT] = []

        for idx, item in enumerate(entries):
            if item is None:
                continue

            item_data = dict(item) if isinstance(item, dict) else item
            if not isinstance(item_data, dict):
                logger.debug(
                    "Skipping %s candidate at position %s; expected dict-like structure, got %s",
                    candidate_model.__name__,
                    idx,
                    type(item_data).__name__,
                )
                continue

            if item_transform is not None:
                try:
                    item_data = item_transform(item_data)
                except Exception as exc:
                    logger.warning(
                        "Failed to transform %s candidate at position %s: %s",
                        candidate_model.__name__,
                        idx,
                        exc,
                    )
                    continue

            try:
                candidates.append(candidate_model(**item_data))
            except ValidationError as exc:
                logger.warning(
                    "Skipping %s candidate at position %s due to validation error: %s",
                    candidate_model.__name__,
                    idx,
                    exc,
                )

        return wrap_output(**{output_field: candidates})

    @staticmethod
    def _normalise_collection(json_data: Any, key: Optional[Union[str, Sequence[str]]]) -> Sequence[Any]:
        candidate_keys: Tuple[str, ...] = ()
        if isinstance(key, str):
            candidate_keys = (key,)
        elif key:
            candidate_keys = tuple(key)

        if isinstance(json_data, dict):
            for candidate_key in candidate_keys:
                if candidate_key in json_data:
                    value = json_data[candidate_key]
                    if isinstance(value, (list, tuple)):
                        return value
                    if value is None:
                        return []
                    return [value]
            return [json_data]
        if isinstance(json_data, (list, tuple)):
            return json_data
        if json_data is None:
            return []
        return [json_data]
    
    def _convert_to_lodging_output(self, json_data: Dict[str, Any]) -> LodgingAgentOutput:
        """Convert JSON to LodgingAgentOutput."""
        return self._build_output_from_items(
            json_data,
            collection_key="lodging",
            candidate_model=CandidateLodging,
            wrap_output=LodgingAgentOutput,
            output_field="lodging",
        )
    
    def _convert_to_activities_output(self, json_data: Dict[str, Any]) -> ActivitiesAgentOutput:
        """Convert JSON to ActivitiesAgentOutput."""
        return self._build_output_from_items(
            json_data,
            collection_key="activities",
            candidate_model=CandidateActivity,
            wrap_output=ActivitiesAgentOutput,
            output_field="activities",
        )
    
    def _convert_to_food_output(self, json_data: Dict[str, Any]) -> FoodAgentOutput:
        """Convert JSON to FoodAgentOutput."""
        return self._build_output_from_items(
            json_data,
            collection_key="food",
            candidate_model=CandidateFood,
            wrap_output=FoodAgentOutput,
            output_field="food",
        )
    
    def _convert_to_intercity_transport_output(self, json_data: Dict[str, Any]) -> IntercityTransportAgentOutput:
        """Convert JSON to IntercityTransportAgentOutput."""
        def transform(item: Dict[str, Any]) -> Dict[str, Any]:
            mutated = dict(item)
            transfers = mutated.get("transfer")
            if transfers:
                normalised_transfers: List[Transfer] = []
                for leg in transfers:
                    if isinstance(leg, Transfer):
                        normalised_transfers.append(leg)
                        continue
                    if not isinstance(leg, dict):
                        logger.debug("Skipping non-dict transfer leg: %s", leg)
                        continue
                    try:
                        normalised_transfers.append(Transfer(**leg))
                    except ValidationError as exc:
                        logger.warning("Skipping transfer leg due to validation error: %s", exc)
                mutated["transfer"] = normalised_transfers
            return mutated

        return self._build_output_from_items(
            json_data,
            collection_key=("intercity_transport", "transport"),
            candidate_model=CandidateIntercityTransport,
            wrap_output=IntercityTransportAgentOutput,
            item_transform=transform,
            output_field="intercity_transport",
        )
    
    def _convert_to_recommendations_output(self, json_data: Dict[str, Any]) -> RecommendationsOutput:
        """Convert JSON to RecommendationsOutput."""
        return RecommendationsOutput(**json_data)

# Factory function to create the appropriate hook
def create_pydantic_hook(output_type: str) -> PydanticPostModelHook:
    """Create a post-model hook for the specified output type."""
    return PydanticPostModelHook(output_type)
