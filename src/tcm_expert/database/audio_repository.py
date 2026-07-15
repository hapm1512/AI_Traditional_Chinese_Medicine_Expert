from __future__ import annotations

import json
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import optional_text, required_text


class AudioAnalysisRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def create(
        self, consultation_id: int, sample_type: str, path: str, result: dict[str, Any]
    ) -> int:
        with self.database.transaction() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM consultations WHERE id=?", (consultation_id,)
                ).fetchone()
                is None
            ):
                raise ValueError("Hồ sơ khám không tồn tại")
            cursor = connection.execute(
                """INSERT INTO audio_analyses
                (consultation_id,sample_type,source_mode,original_audio_path,audio_sha256,
                 duration_seconds,sample_rate,channels,quality_score,quality_issues,rms_level,
                 peak_level,zero_crossing_rate,dominant_frequency,pattern_label,ai_confidence,ai_detail)
                VALUES(?,?,'file',?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    consultation_id,
                    sample_type,
                    required_text(path, "Tệp âm thanh", 2000),
                    result["audio_sha256"],
                    result["duration_seconds"],
                    result["sample_rate"],
                    result["channels"],
                    result["quality_score"],
                    "\n".join(result["quality_issues"]),
                    result["rms_level"],
                    result["peak_level"],
                    result["zero_crossing_rate"],
                    result["dominant_frequency"],
                    result["pattern_label"],
                    result["ai_confidence"],
                    json.dumps(result["metrics"], ensure_ascii=False),
                ),
            )
            analysis_id = int(cursor.lastrowid)
            self.database.audit(connection, "create", "audio_analysis", analysis_id)
            return analysis_id

    def create_manual(self, consultation_id: int, sample_type: str, characteristic: str) -> int:
        characteristic = required_text(characteristic, "Mô tả âm thanh", 1000)
        with self.database.transaction() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM consultations WHERE id=?", (consultation_id,)
                ).fetchone()
                is None
            ):
                raise ValueError("Hồ sơ khám không tồn tại")
            cursor = connection.execute(
                """INSERT INTO audio_analyses
                (consultation_id,sample_type,source_mode,manual_characteristic,pattern_label)
                VALUES(?,?,'manual',?,?)""",
                (consultation_id, sample_type, characteristic, "Nhân viên nhập thủ công"),
            )
            analysis_id = int(cursor.lastrowid)
            self.database.audit(connection, "create", "audio_analysis", analysis_id, "manual")
            return analysis_id

    def list_for_consultation(self, consultation_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM audio_analyses WHERE consultation_id=? ORDER BY id DESC",
                (consultation_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get(self, analysis_id: int) -> dict[str, Any] | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM audio_analyses WHERE id=?", (analysis_id,)
            ).fetchone()
            return dict(row) if row else None

    def review(self, analysis_id: int, reviewer: str, label: str, note: str) -> None:
        reviewer = required_text(reviewer, "Bác sĩ", 150)
        with self.database.transaction() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM audio_analyses WHERE id=?", (analysis_id,)
                ).fetchone()
                is None
            ):
                raise ValueError("Kết quả âm thanh không tồn tại")
            connection.execute(
                """UPDATE audio_analyses SET doctor_pattern_label=?,doctor_note=?,reviewed_by=?,
                reviewed_at=CURRENT_TIMESTAMP WHERE id=?""",
                (optional_text(label, 200), optional_text(note, 3000), reviewer, analysis_id),
            )
            self.database.audit(connection, "review", "audio_analysis", analysis_id, reviewer)
