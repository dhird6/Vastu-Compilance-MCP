"""VLM + vector fusion extraction from 2D floor plan images."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.models.schemas import (
    ElementType,
    ExtractedLayoutElement,
    FloorPlanElement,
    FloorPlanPayload,
    LayoutExtractionResult,
    Point2D,
)
from app.services.correction.transforms import compute_plot_boundary

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore[misc, assignment]


class VlmLayoutExtractor:
    """
    Stage 1: Turn a 2D layout image into structured FloorPlanPayload.

    Uses GPT-4o vision when OPENAI_API_KEY is set; otherwise requires direct payload.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.openai_model
        self._enabled = bool(settings.openai_api_key) and OPENAI_AVAILABLE
        self._client: Any = None
        if self._enabled:
            self._client = OpenAI(api_key=settings.openai_api_key)

    @property
    def vision_enabled(self) -> bool:
        return self._enabled

    async def extract(
        self,
        *,
        image_base64: str | None = None,
        image_media_type: str = "image/png",
        payload: FloorPlanPayload | None = None,
        true_north_degrees: float | None = None,
    ) -> LayoutExtractionResult:
        if payload is not None:
            return self._from_payload(payload, true_north_degrees)

        if not image_base64:
            raise ValueError("Provide either image_base64 or payload for layout extraction.")

        if not self._enabled:
            raise ValueError(
                "VLM extraction requires OPENAI_API_KEY. "
                "Alternatively send a structured FloorPlanPayload from CAD."
            )

        return await self._extract_with_vision(image_base64, image_media_type, true_north_degrees)

    def _from_payload(
        self,
        payload: FloorPlanPayload,
        true_north_degrees: float | None,
    ) -> LayoutExtractionResult:
        north = true_north_degrees if true_north_degrees is not None else payload.true_north_degrees
        room_polys = [element.polygon for element in payload.elements if element.element_type == ElementType.room]
        elements = [
            ExtractedLayoutElement(
                id=element.id,
                name=element.name,
                element_type=element.element_type,
                polygon=list(element.polygon),
                confidence=0.98,
                source="cad" if payload.source != "vlm_extraction" else "vlm",
                metadata=dict(element.metadata),
            )
            for element in payload.elements
        ]
        return LayoutExtractionResult(
            extraction_method="direct_payload",
            true_north_degrees=north,
            plot_boundary=compute_plot_boundary(room_polys),
            elements=elements,
            payload=payload.model_copy(update={"true_north_degrees": north}),
            confidence_score=0.98,
            warnings=[],
        )

    async def _extract_with_vision(
        self,
        image_base64: str,
        image_media_type: str,
        true_north_degrees: float | None,
    ) -> LayoutExtractionResult:
        clean_b64 = _strip_data_url(image_base64)
        data_url = f"data:{image_media_type};base64,{clean_b64}"

        prompt = (
            "Analyze this architectural floor plan image. Extract ALL rooms, walls, doors, and windows. "
            "Return JSON with: true_north_degrees (compass if visible, else 0), rooms[] each with "
            "id, name, room_type (kitchen|master_bedroom|pooja|toilet|living_room|entrance|etc), "
            "polygon as [{x,y},...] in plan coordinates (feet, Y=north), confidence 0-1. "
            "Also walls/doors/windows arrays. Infer room types from labels when present."
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AEC floor plan vision parser. "
                            "Output only valid JSON. Rooms must be closed polygons."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("VLM extraction failed: %s", exc)
            raise ValueError(f"VLM layout extraction failed: {exc}") from exc

        return self._parse_vlm_json(parsed, true_north_degrees, model=self._model)

    def _parse_vlm_json(
        self,
        parsed: dict[str, Any],
        true_north_override: float | None,
        *,
        model: str | None,
    ) -> LayoutExtractionResult:
        north = float(
            true_north_override if true_north_override is not None else parsed.get("true_north_degrees", 0.0)
        )
        warnings: list[str] = []
        floor_elements: list[FloorPlanElement] = []
        extracted: list[ExtractedLayoutElement] = []

        for index, room in enumerate(parsed.get("rooms", [])):
            polygon = _parse_polygon(room.get("polygon", []))
            if len(polygon) < 3:
                warnings.append(f"Skipped room with invalid polygon: {room.get('name', index)}")
                continue
            room_id = str(room.get("id") or f"vlm-room-{index}")
            room_type = _normalize_room_type(str(room.get("room_type", room.get("name", "room"))))
            confidence = float(room.get("confidence", 0.8))
            metadata = {"room_type": room_type, "vlm_confidence": confidence}
            floor_elements.append(
                FloorPlanElement(
                    id=room_id,
                    name=str(room.get("name", room_type)),
                    element_type=ElementType.room,
                    polygon=polygon,
                    metadata=metadata,
                )
            )
            extracted.append(
                ExtractedLayoutElement(
                    id=room_id,
                    name=str(room.get("name", room_type)),
                    element_type=ElementType.room,
                    polygon=polygon,
                    confidence=confidence,
                    source="vlm",
                    metadata=metadata,
                )
            )

        for category, element_type in (
            ("walls", ElementType.wall),
            ("doors", ElementType.door),
            ("windows", ElementType.window),
        ):
            for index, item in enumerate(parsed.get(category, [])):
                polygon = _parse_polygon(item.get("polygon") or item.get("points", []))
                if len(polygon) < 2 and isinstance(item.get("line"), dict):
                    polygon = _parse_polygon([item["line"].get("start"), item["line"].get("end")])
                if len(polygon) < 2:
                    continue
                element_id = str(item.get("id") or f"vlm-{element_type.value}-{index}")
                floor_elements.append(
                    FloorPlanElement(
                        id=element_id,
                        name=str(item.get("name", element_type.value)),
                        element_type=element_type,
                        polygon=polygon,
                        metadata={"source": "vlm"},
                    )
                )
                extracted.append(
                    ExtractedLayoutElement(
                        id=element_id,
                        name=str(item.get("name", element_type.value)),
                        element_type=element_type,
                        polygon=polygon,
                        confidence=float(item.get("confidence", 0.75)),
                        source="vlm",
                        metadata={"source": "vlm"},
                    )
                )

        if not floor_elements:
            raise ValueError("VLM extraction returned no usable geometry.")

        payload = FloorPlanPayload(
            source="vlm_extraction",
            true_north_degrees=north,
            elements=floor_elements,
        )
        room_polys = [element.polygon for element in floor_elements if element.element_type == ElementType.room]
        avg_conf = sum(item.confidence for item in extracted) / max(len(extracted), 1)

        return LayoutExtractionResult(
            extraction_method="vlm_vision",
            model=model,
            true_north_degrees=north,
            plot_boundary=compute_plot_boundary(room_polys),
            elements=extracted,
            payload=payload,
            confidence_score=round(avg_conf, 3),
            warnings=warnings,
            raw_vlm_notes={"notes": parsed.get("notes", ""), "request_id": str(uuid4())},
        )


def _strip_data_url(image_base64: str) -> str:
    if "," in image_base64 and image_base64.strip().startswith("data:"):
        return image_base64.split(",", 1)[1]
    return image_base64.strip()


def _parse_polygon(raw: Any) -> list[Point2D]:
    if not isinstance(raw, list):
        return []
    points: list[Point2D] = []
    for item in raw:
        if isinstance(item, dict) and "x" in item and "y" in item:
            points.append(Point2D(x=float(item["x"]), y=float(item["y"])))
    return points


def _normalize_room_type(name: str) -> str:
    lower = name.strip().lower().replace(" ", "_")
    for key, value in (
        ("kitchen", "kitchen"),
        ("master", "master_bedroom"),
        ("bed", "master_bedroom"),
        ("pooja", "pooja"),
        ("puja", "pooja"),
        ("toilet", "toilet"),
        ("bath", "toilet"),
        ("living", "living_room"),
        ("entrance", "entrance"),
        ("foyer", "entrance"),
        ("stair", "staircase"),
    ):
        if key in lower:
            return value
    return lower or "room"
