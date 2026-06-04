from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.services.autodesk.client import AutodeskAPSClient

router = APIRouter(prefix="/api/v1/autodesk", tags=["autodesk"])


@router.get("/models/{urn}/metadata")
async def get_model_metadata(urn: str) -> dict:
    client = AutodeskAPSClient(get_settings())
    return await client.fetch_model_view(urn)


@router.get("/models/{urn}/floorplan")
async def get_floorplan_data(urn: str) -> dict:
    client = AutodeskAPSClient(get_settings())
    return await client.fetch_floorplan_geometry(urn)
