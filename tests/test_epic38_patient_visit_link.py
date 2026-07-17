from tcm_expert.ui.diagnosis_page import DiagnosisPage


def test_visit_names_follow_clinical_sequence():
    assert DiagnosisPage._visit_name(1) == "Lần đầu"
    assert DiagnosisPage._visit_name(2) == "Tái khám 1"
    assert DiagnosisPage._visit_name(3) == "Tái khám 2"
    assert DiagnosisPage._visit_name(10) == "Tái khám 9"
