from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from tcm_expert.database.manager import DatabaseManager

DISCLAIMER = (
    "Kết quả chỉ hỗ trợ tham khảo; không phải đơn thuốc. "
    "Bác sĩ phải kiểm tra, quyết định bài thuốc, gia giảm và liều dùng."
)

ACUPOINT_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("tỳ", "kiện tỳ", "mệt", "ăn kém"), ("Túc tam lý (ST36)", "Tỳ du (BL20)")),
    (("can", "sơ can", "uất"), ("Thái xung (LR3)", "Hợp cốc (LI4)")),
    (("tâm", "mất ngủ", "an thần"), ("Thần môn (HT7)", "Nội quan (PC6)")),
    (("thận", "âm hư"), ("Thái khê (KI3)", "Thận du (BL23)")),
    (("phế", "ho", "khí hư"), ("Phế du (BL13)", "Liệt khuyết (LU7)")),
    (("đàm", "thấp"), ("Phong long (ST40)", "Âm lăng tuyền (SP9)")),
)


@dataclass(frozen=True)
class RecommendationContext:
    text: str
    treatment_principles: tuple[str, ...]
    allergies: str
    current_treatment: str
    pregnancy: bool
    liver_risk: bool
    kidney_risk: bool


class FormulaRecommender:
    """Deterministic clinical decision support; never prescribes dosage."""

    def __init__(self, database: DatabaseManager):
        self.database = database

    def recommend(self, consultation_id: int, limit: int = 3) -> dict[str, Any]:
        context = self._context(consultation_id)
        with self.database.transaction() as connection:
            formulas = connection.execute(
                """SELECT * FROM formulas WHERE active=1
                   AND (source_type='system' OR doctor_approved=1) ORDER BY name"""
            ).fetchall()
        ranked: list[dict[str, Any]] = []
        for formula_row in formulas:
            formula = dict(formula_row)
            searchable = " ".join(
                str(formula.get(key, ""))
                for key in ("name", "category", "treatment_principle", "indications")
            ).lower()
            matches = self._matches(context, searchable)
            ranked.append(
                {
                    **formula,
                    "score": min(100, 20 + len(matches) * 18),
                    "matched": matches,
                    "safety": self._safety(formula["id"], context),
                    "acupoints": self._acupoints(context.text + " " + searchable),
                }
            )
        ranked.sort(key=lambda item: (-item["score"], item["name"]))
        principles = list(context.treatment_principles) or ["Chưa có pháp trị được xác nhận"]
        return {
            "principles": principles,
            "recommendations": ranked[:limit],
            "disclaimer": DISCLAIMER,
        }

    def _context(self, consultation_id: int) -> RecommendationContext:
        with self.database.transaction() as connection:
            row = connection.execute(
                """SELECT c.*, p.allergies, p.sex
                   FROM consultations c JOIN patients p ON p.id=c.patient_id
                   WHERE c.id=?""",
                (consultation_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Không tìm thấy lần khám.")
            inquiry = connection.execute(
                "SELECT * FROM inquiry_findings WHERE consultation_id=?", (consultation_id,)
            ).fetchone()
            syndromes = connection.execute(
                """SELECT s.name, s.treatment_principle
                   FROM consultation_syndromes cs
                   JOIN tcm_syndromes s ON s.id=cs.syndrome_id
                   WHERE cs.consultation_id=?
                   ORDER BY cs.is_primary DESC, cs.confidence DESC""",
                (consultation_id,),
            ).fetchall()
        parts = [str(value or "") for value in row]
        if inquiry:
            parts.extend(str(value or "") for value in inquiry)
        parts.extend(str(value or "") for syndrome in syndromes for value in syndrome)
        text = " ".join(parts).lower()
        current_treatment = str(inquiry["current_treatment"] if inquiry else "")
        return RecommendationContext(
            text=text,
            treatment_principles=tuple(s["treatment_principle"] for s in syndromes),
            allergies=str(row["allergies"] or ""),
            current_treatment=current_treatment,
            pregnancy=any(word in text for word in ("mang thai", "thai kỳ", "có thai")),
            liver_risk=any(word in text for word in ("bệnh gan", "suy gan", "viêm gan")),
            kidney_risk=any(word in text for word in ("bệnh thận", "suy thận", "lọc thận")),
        )

    @staticmethod
    def _matches(context: RecommendationContext, searchable: str) -> list[str]:
        candidates = set(re.findall(r"[a-zà-ỹđ]+", context.text))
        for principle in context.treatment_principles:
            candidates.update(re.findall(r"[a-zà-ỹđ]+", principle.lower()))
        ignored = {"và", "có", "không", "theo", "tham", "khảo", "bác", "sĩ"}
        return sorted(
            word
            for word in candidates
            if len(word) >= 3 and word not in ignored and word in searchable
        )[:5]

    def _safety(self, formula_id: int, context: RecommendationContext) -> list[dict[str, str]]:
        alerts: list[dict[str, str]] = []
        with self.database.transaction() as connection:
            ingredients = connection.execute(
                """SELECT h.name_vi, h.toxicity
                   FROM formula_ingredients fi JOIN materia_medica h ON h.id=fi.herb_id
                   WHERE fi.formula_id=?""",
                (formula_id,),
            ).fetchall()
            interactions = connection.execute(
                """SELECT h.name_vi, hi.interacting_drug, hi.severity, hi.effect
                   FROM formula_ingredients fi JOIN materia_medica h ON h.id=fi.herb_id
                   JOIN herb_interactions hi ON hi.herb_id=h.id
                   WHERE fi.formula_id=?""",
                (formula_id,),
            ).fetchall()
        allergy_text = context.allergies.lower()
        for herb in ingredients:
            if herb["name_vi"].lower() in allergy_text:
                alerts.append({"level": "contraindicated", "message": f"Dị ứng: {herb['name_vi']}"})
            if str(herb["toxicity"] or "").strip():
                alerts.append(
                    {"level": "high", "message": f"Độc tính {herb['name_vi']}: {herb['toxicity']}"}
                )
        for active, message in (
            (context.pregnancy, "Thai kỳ: bắt buộc bác sĩ chuyên khoa kiểm tra."),
            (context.liver_risk, "Bệnh gan: cần đánh giá chức năng gan."),
            (context.kidney_risk, "Bệnh thận: cần đánh giá chức năng thận."),
        ):
            if active:
                alerts.append({"level": "high", "message": message})
        treatment = context.current_treatment.lower()
        for item in interactions:
            drug = str(item["interacting_drug"] or "")
            if not drug or drug.lower() in treatment:
                alerts.append(
                    {
                        "level": str(item["severity"]),
                        "message": (
                            f"{item['name_vi']} ↔ {drug or 'thuốc đang dùng'}: {item['effect']}"
                        ),
                    }
                )
        if not context.allergies.strip():
            alerts.append({"level": "unknown", "message": "Chưa khai báo dị ứng."})
        if not context.current_treatment.strip():
            alerts.append({"level": "unknown", "message": "Chưa khai báo thuốc Tây đang dùng."})
        return alerts

    @staticmethod
    def _acupoints(text: str) -> list[str]:
        points: list[str] = []
        lowered = text.lower()
        for keywords, values in ACUPOINT_RULES:
            if any(keyword in lowered for keyword in keywords):
                points.extend(values)
        return list(dict.fromkeys(points))[:4]
