"""Shared immutable fixtures for the offline lab tests."""

from pathlib import Path

import pytest

from rag_lab.config import LabConfig, load_config
from rag_lab.pipeline import OfflineRagPipeline, PipelineResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")  # type: ignore[misc]
def config() -> LabConfig:
    """Return the checked-in offline configuration."""

    return load_config(PROJECT_ROOT / "configs/offline.json")


@pytest.fixture(scope="session")  # type: ignore[misc]
def pipeline_result(config: LabConfig) -> PipelineResult:
    """Run one reusable successful pipeline execution."""

    return OfflineRagPipeline(config).run()
