from __future__ import annotations

from time import monotonic
from typing import Any

from tcm_expert.ai.models import AIProposal
from tcm_expert.ai.providers import (
    DisabledProvider,
    KnowledgeProvider,
    ProviderUnavailable,
    TCMReasoner,
    Translator,
)
from tcm_expert.services.clinical_decision_support import ClinicalDecisionSupport
from tcm_expert.ai.validation import AIValidationError, assess_input_quality, normalize_evidence, validate_ai_output
from tcm_expert.database.ai_monitoring_repository import AIMonitoringRepository


DISCLAIMER = (
    "Đề xuất chỉ để tham khảo, chưa được bác sĩ duyệt. "
    "Bắt buộc bác sĩ kiểm tra và phê duyệt trước khi sử dụng. "
    "Bác sĩ quyết định và chịu trách nhiệm."
)


class AIWorkflowDisabled(RuntimeError):
    pass


class AIInputInsufficient(AIWorkflowDisabled, AIValidationError):
    pass


class AIWorkflow:
    """Vietnamese -> Chinese AI -> knowledge -> rules -> doctor review."""

    def __init__(
        self,
        database: Any,
        *,
        enabled: bool = False,
        translator: Translator | None = None,
        reasoner: TCMReasoner | None = None,
        knowledge: tuple[KnowledgeProvider, ...] | None = None,
    ):
        self.enabled = bool(enabled)
        self.monitoring = AIMonitoringRepository(database)
        self.clinical = ClinicalDecisionSupport(database)
        self.translator = translator or DisabledProvider("Bộ dịch Việt–Trung")
        self.reasoner = reasoner or DisabledProvider("TCMChat")
        self.knowledge = knowledge or (
            DisabledProvider("OpenTCM GraphRAG"),
            DisabledProvider("TCMBank"),
            DisabledProvider("SymMap"),
        )

    def propose(self, consultation_id: int) -> AIProposal:
        if not self.enabled:
            raise AIWorkflowDisabled("AI đang tắt. Bật trong Cài đặt khi sẵn sàng.")
        report = self.clinical.build(consultation_id)
        quality = assess_input_quality(report)
        if not quality.acceptable:
            missing = ", ".join(quality.missing) or "Tứ chẩn"
            detail = f"Độ đầy đủ {quality.score * 100:.0f}%; thiếu: {missing}"
            self.monitoring.record(consultation_id, "Kiểm định đầu vào", "blocked", 0, detail)
            raise AIInputInsufficient(
                f"Chưa đủ dữ liệu tạo đề xuất AI ({quality.score * 100:.0f}%). "
                f"Cần bổ sung: {missing}."
            )
        context = self._context(report)
        traces: list[str] = ["Rule Engine: sẵn sàng"]
        evidence = [
            f"Độ đầy đủ Tứ chẩn: {report['completeness_score'] * 100:.0f}%",
            *[f"Cảnh báo: {item}" for item in report["red_flags"]],
        ]
        warnings = [item["message"] for item in report["safety_alerts"]]
        ai_summary = ""
        started = monotonic()
        try:
            chinese = self.translator.vi_to_zh(context)
            traces.append(f"{self.translator.name}: hoàn tất")
            result = self.reasoner.suggest(chinese)
            traces.append(f"{self.reasoner.name}: hoàn tất")
            ai_summary = self.translator.zh_to_vi(str(result.get("summary", "")))
            self.monitoring.record(
                consultation_id, self.reasoner.name, "ok", int((monotonic() - started) * 1000)
            )
        except ProviderUnavailable as error:
            traces.append(str(error))
            self.monitoring.record(
                consultation_id, self.reasoner.name, "fallback",
                int((monotonic() - started) * 1000), str(error),
            )
        for provider in self.knowledge:
            provider_started = monotonic()
            try:
                rows = provider.retrieve(context)
                traces.append(f"{provider.name}: {len(rows)} nguồn")
                evidence.extend(normalize_evidence(rows) or (provider.name,))
                self.monitoring.record(
                    consultation_id, provider.name, "ok",
                    int((monotonic() - provider_started) * 1000), f"{len(rows)} nguồn",
                )
            except ProviderUnavailable as error:
                traces.append(str(error))
                self.monitoring.record(
                    consultation_id, provider.name, "fallback",
                    int((monotonic() - provider_started) * 1000), str(error),
                )
        summary = ai_summary.strip() or self._rule_summary(report)
        normalized_evidence = normalize_evidence(evidence)
        if ai_summary.strip():
            try:
                validate_ai_output(summary, normalized_evidence)
            except AIValidationError as error:
                self.monitoring.record(consultation_id, self.reasoner.name, "blocked", 0, str(error))
                raise AIInputInsufficient(str(error)) from error
        return AIProposal(
            consultation_id=consultation_id,
            vietnamese_summary=f"{summary}\n\n{DISCLAIMER}",
            evidence=normalized_evidence,
            warnings=tuple(dict.fromkeys(warnings)),
            provider_trace=tuple(traces),
            confidence=min(0.80, float(report["completeness_score"]) * 0.80),
            metadata={"source": "ai_reference", "requires_doctor_review": True},
        )

    @staticmethod
    def _context(report: dict[str, Any]) -> str:
        syndromes = ", ".join(item["name"] for item in report["syndrome_suggestions"])
        return f"{report['patient']}. Dữ liệu thiếu: {', '.join(report['missing_data'])}. Chứng: {syndromes}"

    @staticmethod
    def _rule_summary(report: dict[str, Any]) -> str:
        names = ", ".join(item["name"] for item in report["syndrome_suggestions"])
        return "Gợi ý chứng cần bác sĩ kiểm tra: " + (names or "chưa đủ dữ liệu")


