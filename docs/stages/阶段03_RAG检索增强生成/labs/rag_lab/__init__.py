"""Offline, observable RAG teaching pipeline."""

from rag_lab.config import LabConfig, load_config
from rag_lab.pipeline import OfflineRagPipeline, PipelineResult

__all__ = ["LabConfig", "OfflineRagPipeline", "PipelineResult", "load_config"]
__version__ = "1.0.0"
