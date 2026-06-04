from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class AutodeskAPSClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def _token(self) -> str:
        if not self.settings.aps_client_id or not self.settings.aps_client_secret:
            raise ValueError("APS credentials are missing. Configure APS_CLIENT_ID and APS_CLIENT_SECRET.")

        payload = {
            "grant_type": "client_credentials",
            "scope": "data:read bucket:read",
        }
        auth = (self.settings.aps_client_id, self.settings.aps_client_secret)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.settings.aps_auth_url, data=payload, auth=auth)
            response.raise_for_status()
            return response.json()["access_token"]

    async def fetch_model_view(self, urn: str) -> dict[str, Any]:
        token = await self._token()
        headers = {"Authorization": f"Bearer {token}"}

        # This endpoint path is an example adaptor point for APS Model Derivative data.
        url = f"{self.settings.aps_api_base_url}/modelderivative/v2/designdata/{urn}/metadata"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def fetch_floorplan_geometry(self, urn: str) -> dict[str, Any]:
        metadata = await self.fetch_model_view(urn)
        logger.info("Fetched APS metadata for geometry extraction.")
        return {"urn": urn, "metadata": metadata}
