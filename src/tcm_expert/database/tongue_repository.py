from __future__ import annotations

import json
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import optional_text, required_text


class TongueAnalysisRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def create(self, consultation_id: int, image_path: str, result: dict[str, Any]) -> int:
        with self.database.transaction() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM consultations WHERE id=?", (consultation_id,)
                ).fetchone()
                is None
            ):
                raise ValueError("Hồ sơ khám không tồn tại")
            cursor = connection.execute(
                """INSERT INTO tongue_analyses
                   (consultation_id,original_image_path,image_sha256,image_width,image_height,
                    quality_score,quality_issues,segmentation_confidence,tongue_color,
                    coating_color,coating_thickness,teeth_marks,cracks,ai_confidence,ai_detail)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    consultation_id,
                    required_text(image_path, "Ảnh", 2000),
                    result["image_sha256"],
                    result["image_width"],
                    result["image_height"],
                    result["quality_score"],
                    "\n".join(result["quality_issues"]),
                    result["segmentation_confidence"],
                    result["tongue_color"],
                    result["coating_color"],
                    result["coating_thickness"],
                    int(result["teeth_marks"]),
                    int(result["cracks"]),
                    result["ai_confidence"],
                    json.dumps(result["metrics"], ensure_ascii=False),
                ),
            )
            analysis_id = int(cursor.lastrowid)
            self.database.audit(connection, "create", "tongue_analysis", analysis_id)
            return analysis_id

    def list_for_consultation(self, consultation_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM tongue_analyses WHERE consultation_id=? ORDER BY id DESC",
                (consultation_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get(self, analysis_id: int) -> dict[str, Any] | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tongue_analyses WHERE id=?", (analysis_id,)
            ).fetchone()
            return dict(row) if row else None

    def review(self, analysis_id: int, values: dict[str, Any]) -> None:
        reviewer = required_text(values.get("reviewed_by"), "Bác sĩ", 150)
        with self.database.transaction() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM tongue_analyses WHERE id=?", (analysis_id,)
                ).fetchone()
                is None
            ):
                raise ValueError("Kết quả phân tích không tồn tại")
            connection.execute(
                """UPDATE tongue_analyses SET
                   doctor_tongue_color=?,doctor_coating_color=?,doctor_coating_thickness=?,
                   doctor_teeth_marks=?,doctor_cracks=?,doctor_note=?,reviewed_by=?,
                   reviewed_at=CURRENT_TIMESTAMP WHERE id=?""",
                (
                    optional_text(values.get("tongue_color"), 100),
                    optional_text(values.get("coating_color"), 100),
                    optional_text(values.get("coating_thickness"), 100),
                    int(bool(values.get("teeth_marks"))),
                    int(bool(values.get("cracks"))),
                    optional_text(values.get("note"), 3000),
                    reviewer,
                    analysis_id,
                ),
            )
            self.database.audit(connection, "review", "tongue_analysis", analysis_id, reviewer)
