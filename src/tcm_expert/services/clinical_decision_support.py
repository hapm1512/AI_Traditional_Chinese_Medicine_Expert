from __future__ import annotations

from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.services.formula_recommender import FormulaRecommender
from tcm_expert.services.ollama_formula_recommender import FormulaRecommendationOutcome

DISCLAIMER = (
    "Báo cáo hỗ trợ quyết định, không phải chẩn đoán hay đơn thuốc. "
    "Bác sĩ phải kiểm tra toàn bộ căn cứ và phê duyệt."
)

RED_FLAG_RULES = (
    (("đau ngực", "khó thở", "ngất"), "Dấu hiệu tim-phổi cấp; cân nhắc chuyển cấp cứu."),
    (("liệt", "méo miệng", "nói khó"), "Dấu hiệu thần kinh cấp; cân nhắc chuyển cấp cứu."),
    (
        ("nôn ra máu", "đi ngoài ra máu", "xuất huyết"),
        "Nguy cơ xuất huyết; cần đánh giá y khoa ngay.",
    ),
    (("sốt cao", "co giật", "lơ mơ"), "Dấu hiệu toàn thân nặng; cần đánh giá y khoa ngay."),
)


class ClinicalDecisionSupport:
    """Transparent summary layer; it never finalizes diagnosis or treatment."""

    def __init__(self, database: DatabaseManager):
        self.database = database
        self.recommender = FormulaRecommender(database)

    def build(
        self,
        consultation_id: int,
        formula_outcome: FormulaRecommendationOutcome | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as connection:
            consultation = connection.execute(
                """SELECT c.*,p.code patient_code,p.full_name,p.allergies
                   FROM consultations c JOIN patients p ON p.id=c.patient_id WHERE c.id=?""",
                (consultation_id,),
            ).fetchone()
            if consultation is None:
                raise ValueError("Không tìm thấy lần khám.")
            diagnostics = connection.execute(
                "SELECT category,finding,note FROM diagnostic_entries WHERE consultation_id=?",
                (consultation_id,),
            ).fetchall()
            inquiry = connection.execute(
                "SELECT * FROM inquiry_findings WHERE consultation_id=?", (consultation_id,)
            ).fetchone()
            syndromes = connection.execute(
                """SELECT s.name,s.eight_principles,s.pathogenesis,s.treatment_principle,
                          cs.confidence,cs.evidence,cs.is_primary,cs.doctor_confirmed
                   FROM consultation_syndromes cs JOIN tcm_syndromes s ON s.id=cs.syndrome_id
                   WHERE cs.consultation_id=? ORDER BY cs.is_primary DESC,cs.confidence DESC""",
                (consultation_id,),
            ).fetchall()
            counts = {
                "Vọng": connection.execute(
                    "SELECT COUNT(*) FROM diagnostic_entries "
                    "WHERE consultation_id=? AND category='inspection'",
                    (consultation_id,),
                ).fetchone()[0],
                "Văn": connection.execute(
                    "SELECT COUNT(*) FROM listening_smelling_findings WHERE consultation_id=?",
                    (consultation_id,),
                ).fetchone()[0],
                "Vấn": 1 if inquiry else 0,
                "Thiết": connection.execute(
                    """SELECT (SELECT COUNT(*) FROM pulse_findings WHERE consultation_id=?) +
                              (SELECT COUNT(*) FROM palpation_findings WHERE consultation_id=?)""",
                    (consultation_id, consultation_id),
                ).fetchone()[0],
            }

        text = " ".join(
            [str(value or "") for value in consultation]
            + [str(value or "") for row in diagnostics for value in row]
            + ([str(value or "") for value in inquiry] if inquiry else [])
        ).lower()
        red_flags = [
            message for words, message in RED_FLAG_RULES if any(word in text for word in words)
        ]
        missing = [name for name, count in counts.items() if not count]
        completeness = sum(bool(value) for value in counts.values()) / len(counts)
        suggestions = [
            {
                "name": row["name"],
                "confidence": float(row["confidence"]),
                "evidence": row["evidence"],
                "eight_principles": row["eight_principles"],
                "pathogenesis": row["pathogenesis"],
                "treatment_principle": row["treatment_principle"],
                "doctor_confirmed": bool(row["doctor_confirmed"]),
            }
            for row in syndromes
        ]
        formula_result = (
            formula_outcome.result
            if formula_outcome is not None
            else self.recommender.recommend(consultation_id, confirmed_only=True)
        )
        safety_alerts = [
            alert for item in formula_result["recommendations"] for alert in item["safety"]
        ]
        high_alert = any(a["level"] in {"high", "contraindicated"} for a in safety_alerts)
        risk_level = "high" if red_flags or high_alert else "moderate" if missing else "low"
        return {
            "consultation_id": consultation_id,
            "patient": f"{consultation['patient_code']} — {consultation['full_name']}",
            "completeness_score": completeness,
            "four_examinations": counts,
            "missing_data": missing,
            "risk_level": risk_level,
            "red_flags": red_flags,
            "syndrome_suggestions": suggestions,
            "treatment_principles": formula_result["principles"],
            "formula_suggestions": [
                {
                    "name": item["name"],
                    "score": item["score"],
                    "matched": item["matched"],
                    "reason": item.get("ai_reason", ""),
                }
                for item in formula_result["recommendations"]
            ],
            "formula_eligible": formula_result["eligible"],
            "formula_blocked_reason": formula_result["blocked_reason"],
            "formula_source": formula_outcome.source if formula_outcome else "rules",
            "formula_model": formula_outcome.model if formula_outcome else "",
            "formula_fallback_reason": formula_outcome.fallback_reason if formula_outcome else "",
            "safety_alerts": safety_alerts,
            "disclaimer": DISCLAIMER,
        }
