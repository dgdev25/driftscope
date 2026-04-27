"""DriftScope data models — typed contracts between pipeline stages."""

from driftscope.models.commit import Commit
from driftscope.models.blame import BlameLine
from driftscope.models.history import CommitHistory, AttributedCommit, AttributedHistory
from driftscope.models.ast_diff import ASTNodeChange, ASTFileDiff, ASTDiffSet
from driftscope.models.metrics import (
    SurvivalMetrics,
    ComplexityMetrics,
    WeeklyComplexity,
    ChurnMetrics,
    ModuleMetrics,
)
from driftscope.models.report import MetricsResult, ThresholdBreach
from driftscope.models.provenance import ProvenanceEntry

__all__ = [
    "Commit",
    "BlameLine",
    "CommitHistory",
    "AttributedCommit",
    "AttributedHistory",
    "ASTNodeChange",
    "ASTFileDiff",
    "ASTDiffSet",
    "SurvivalMetrics",
    "ComplexityMetrics",
    "WeeklyComplexity",
    "ChurnMetrics",
    "ModuleMetrics",
    "MetricsResult",
    "ThresholdBreach",
    "ProvenanceEntry",
]
