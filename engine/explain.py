"""Plain-language explanations built from the cascade's loss ledger.

*** STUB (task A2) ***
`explain` returns one placeholder sentence so the app can be built against
it. The real sentences (traced from the loss ledger, as described in
docs/ENGINE_RULES.md) are implemented in task A6.
"""

from __future__ import annotations


def explain(result: dict, entity_id: str) -> list[str]:
    """Return up to 3 plain-English sentences explaining one entity's outcome.

    STUB: returns a single placeholder sentence. Real logic comes in task A6.

    Args:
        result: the dict returned by `engine.cascade.run_cascade`.
        entity_id: the entity to explain.
    """
    if entity_id not in set(result["state"]["entity_id"]):
        raise ValueError(f"entity_id '{entity_id}' is not in the result")
    return [f"STUB: no explanation has been implemented yet for {entity_id}."]
