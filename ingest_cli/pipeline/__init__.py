"""Pipeline module for document ingestion.

This module provides the ingestion pipeline orchestrator.
"""

from .orchestrator import (
    BatchResult,
    IngestionPipeline,
    PipelineConfig,
    PipelineError,
    PipelineResult,
    create_pipeline,
)

__all__ = [
    "BatchResult",
    "IngestionPipeline",
    "PipelineConfig",
    "PipelineError",
    "PipelineResult",
    "create_pipeline",
]
