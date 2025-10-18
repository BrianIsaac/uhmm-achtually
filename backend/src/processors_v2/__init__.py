"""Version 2 processors using modern libraries."""

from .claim_extractor_v2 import ClaimExtractorV2
from .web_fact_checker_v2 import WebFactCheckerV2
from .fact_check_messenger_v2 import FactCheckMessengerV2
from .pipeline_coordinator import FactCheckPipeline

__all__ = [
    "ClaimExtractorV2",
    "WebFactCheckerV2",
    "FactCheckMessengerV2",
    "FactCheckPipeline",
]