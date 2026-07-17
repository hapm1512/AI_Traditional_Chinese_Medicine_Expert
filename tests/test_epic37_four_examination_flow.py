from tcm_expert.database import ConsultationRepository, DatabaseManager, PatientRepository
from tcm_expert.database.syndrome_repository import SyndromeRepository


def test_syndrome_context_includes_tongue_and_audio_ai(tmp_path):
    database = DatabaseManager(tmp_path / "four_examinations.db")
    database.initialize()
    patient = PatientRepository(database).create({"code": "BN004", "full_name": "Bốn chẩn"})
    visit = ConsultationRepository(database).create(patient["id"], "")
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO tongue_analyses
               (consultation_id,original_image_path,image_sha256,image_width,image_height,
                quality_score,segmentation_confidence,tongue_color,coating_color,
                coating_thickness,ai_confidence)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (visit["id"], "tongue.png", "hash", 100, 100, 1, 1,
             "Lưỡi nhạt", "Rêu trắng", "Mỏng", 0.9),
        )
        connection.execute(
            """INSERT INTO audio_analyses
               (consultation_id,sample_type,source_mode,pattern_label,ai_confidence)
               VALUES(?,?,'file',?,?)""",
            (visit["id"], "cough", "Ho yếu", 0.8),
        )

    text = SyndromeRepository(database).clinical_text(visit["id"])

    assert "Lưỡi nhạt" in text
    assert "Rêu trắng" in text
    assert "Ho yếu" in text
