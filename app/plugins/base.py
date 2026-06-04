from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CompliancePlugin(ABC):
    name: str = "base_plugin"

    @abstractmethod
    async def before_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def after_evaluation(self, report: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
