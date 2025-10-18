from typing import Optional, TypeVar
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

def reducer(existing: Optional[T], new: Optional[T]) -> Optional[T]:
    """Generic merge function for all agent output types."""
 
    # Handle None cases
    if new is None:
        return existing
    if existing is None:
        logger.info(f"Reducer: No existing items, using new items")
        return new
    
    # Get the type to work with
    output_type = type(new)
    
    # Get the field name dynamically
    fields = list(output_type.model_fields.keys())
    if not fields:
        return new
    
    list_field_name = fields[0]
    
    # Get the existing and new lists
    existing_items = getattr(existing, list_field_name, []) or []
    new_items = getattr(new, list_field_name, []) or []

    logger.info(f"Reducer: Merging {list_field_name} - existing: {len(existing_items)}, new: {len(new_items)}")

    if existing_items and new_items:
        def _candidate_key(item):
            item_id = getattr(item, "id", None)
            if item_id:
                return ("id", item_id)
            name = getattr(item, "name", None)
            url = getattr(item, "url", None)
            address = getattr(item, "address", None)
            return ("fallback", name, url, address)

        existing_ids_with_values = {getattr(item, "id", None) for item in existing_items if getattr(item, "id", None)}
        new_ids_with_values = {getattr(item, "id", None) for item in new_items if getattr(item, "id", None)}

        existing_keys = {_candidate_key(item) for item in existing_items}
        new_keys = [_candidate_key(item) for item in new_items]

        subset_by_id = bool(new_ids_with_values) and new_ids_with_values.issubset(existing_ids_with_values)
        subset_by_key = not new_ids_with_values and all(key in existing_keys for key in new_keys)

        if len(new_items) <= len(existing_items) and (subset_by_id or subset_by_key):
            logger.info("Reducer: New collection is a subset of existing items; replacing existing list")
            return output_type(**{list_field_name: new_items})

    # Build a set of existing IDs for deduplication
    existing_ids = {item.id for item in existing_items if hasattr(item, 'id') and item.id}

    # Start with all existing items
    merged_items = list(existing_items)
    
    # Add new items that don't already exist
    added_count = 0
    for item in new_items:
        item_id = getattr(item, 'id', None)
        if not item_id or item_id not in existing_ids:
            merged_items.append(item)
            added_count += 1
            if item_id:
                existing_ids.add(item_id)
    
    logger.info(f"Reducer: Added {added_count} new items, total: {len(merged_items)}")
    
    # Create and return new output instance with merged items
    return output_type(**{list_field_name: merged_items})
