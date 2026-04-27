"""JSON report renderer — serializes MetricsResult to versioned JSON.

Time Complexity: O(n) where n is the number of modules.
Space Complexity: O(n) for the serialized output string.
"""

from __future__ import annotations

import json

from driftscope.models.provenance import ProvenanceEntry
from driftscope.models.report import MetricsResult


def render_json(
    result: MetricsResult,
    *,
    include_provenance: bool = False,
    provenance: list[ProvenanceEntry] | None = None,
) -> str:
    """Serialize a MetricsResult to a versioned JSON string.

    Args:
        result: The analysis result to serialize.
        include_provenance: If True and provenance is provided, include
            provenance entries in the output.
        provenance: Optional line-level provenance entries.

    Returns:
        Pretty-printed JSON string with indent=2.

    Raises:
        TypeError: If result cannot be serialized to JSON.
    """
    data = result.model_dump(mode="json")

    if include_provenance and provenance is not None:
        data["provenance"] = [entry.model_dump(mode="json") for entry in provenance]

    return json.dumps(data, indent=2, default=str)
