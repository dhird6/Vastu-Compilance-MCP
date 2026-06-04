from __future__ import annotations

import importlib
from typing import Any

from app.plugins.base import CompliancePlugin


class PluginManager:
    def __init__(self) -> None:
        self.plugins: list[CompliancePlugin] = []

    def load(self, dotted_paths: list[str]) -> None:
        for dotted in dotted_paths:
            module_path, class_name = dotted.rsplit(".", 1)
            module = importlib.import_module(module_path)
            plugin_cls = getattr(module, class_name)
            plugin = plugin_cls()
            if not isinstance(plugin, CompliancePlugin):
                raise TypeError(f"{dotted} is not a CompliancePlugin")
            self.plugins.append(plugin)

    async def run_before(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = payload
        for plugin in self.plugins:
            data = await plugin.before_evaluation(data)
        return data

    async def run_after(self, report: dict[str, Any]) -> dict[str, Any]:
        data = report
        for plugin in self.plugins:
            data = await plugin.after_evaluation(data)
        return data
