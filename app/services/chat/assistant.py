"""Compliance chat — template fallback; OpenAI GPT-4o when configured."""

from __future__ import annotations

from app.models.schemas import ComplianceChatRequest, ComplianceChatResponse, ComplianceReport
from app.services.ai.openai_client import OpenAIService


class ComplianceChatAssistant:
    def __init__(self, openai_service: OpenAIService | None = None) -> None:
        self.openai_service = openai_service or OpenAIService()

    def respond(self, request: ComplianceChatRequest, report: ComplianceReport | None) -> ComplianceChatResponse:
        template = self._template_response(request, report)
        return self.openai_service.chat(request, report, template)

    def _template_response(
        self, request: ComplianceChatRequest, report: ComplianceReport | None
    ) -> ComplianceChatResponse:
        message = request.message.strip().lower()

        if report is None:
            return ComplianceChatResponse(
                reply="Run Analyze Vastu first so I can explain your model's compliance results.",
                cited_rule_ids=[],
            )

        if "why" in message and "kitchen" in message:
            kitchen_failures = [
                r for r in report.rule_results if not r.passed and "kitchen" in r.title.lower()
            ]
            if kitchen_failures:
                failure = kitchen_failures[0]
                return ComplianceChatResponse(
                    reply=(
                        f"Kitchen rule {failure.rule_id}: {failure.explanation} "
                        f"Preferred zones: {', '.join(failure.expected_zones) or 'any'}."
                    ),
                    cited_rule_ids=[failure.rule_id],
                )

        if "suggest" in message or "alternative" in message:
            if report.remediation_plan and report.remediation_plan.actions:
                preview = report.remediation_plan.actions[:3]
                lines = [f"- {action.description}" for action in preview]
                return ComplianceChatResponse(
                    reply="Top remediation actions:\n" + "\n".join(lines),
                    cited_rule_ids=list({action.rule_id for action in preview}),
                )

        if "score" in message:
            return ComplianceChatResponse(
                reply=(
                    f"Compliance score: {report.summary.compliance_score:.1f} "
                    f"(grade {report.summary.grade}). "
                    f"Passed {report.summary.passed_rules}, failed {report.summary.failed_rules}."
                ),
                cited_rule_ids=[],
            )

        failed = [r for r in report.rule_results if not r.passed]
        if failed:
            return ComplianceChatResponse(
                reply=(
                    f"You have {len(failed)} violation(s). Example: {failed[0].explanation} "
                    "Use Preview Fixes or Apply Remediation in Revit to act on the remediation plan."
                ),
                cited_rule_ids=[failed[0].rule_id],
            )

        return ComplianceChatResponse(
            reply="Your layout appears compliant with the loaded Vastu rules.",
            cited_rule_ids=[],
        )
