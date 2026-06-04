from __future__ import annotations

from app.models.schemas import ComplianceSummary, RuleEvaluationResult, Severity


class ComplianceScoringEngine:
    severity_weight = {
        Severity.critical: 2.0,
        Severity.high: 1.5,
        Severity.medium: 1.0,
        Severity.low: 0.6,
        Severity.info: 0.3,
    }

    def compute_summary(self, room_count: int, results: list[RuleEvaluationResult]) -> ComplianceSummary:
        if not results:
            return ComplianceSummary(
                total_rooms=room_count,
                passed_rules=0,
                failed_rules=0,
                compliance_score=100.0,
                grade="A+",
            )

        penalty = 0.0
        passed = 0
        failed = 0

        for result in results:
            if result.passed:
                passed += 1
                continue
            failed += 1
            penalty += result.score_impact * self.severity_weight[result.severity]

        raw_score = max(0.0, 100.0 - penalty)
        return ComplianceSummary(
            total_rooms=room_count,
            passed_rules=passed,
            failed_rules=failed,
            compliance_score=round(raw_score, 2),
            grade=self._to_grade(raw_score),
        )

    def _to_grade(self, score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"
