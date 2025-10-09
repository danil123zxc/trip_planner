from src.api.workflow_service import WorkflowBundle
from src.core.config import ApiSettings
from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from functools import lru_cache


@lru_cache(maxsize=1)
def get_workflow_bundle() -> WorkflowBundle:
    settings = ApiSettings.from_env()
    return WorkflowBundle(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        bundle = get_workflow_bundle()
        await bundle.close()
