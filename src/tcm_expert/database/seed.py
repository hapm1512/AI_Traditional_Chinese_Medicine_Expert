from sqlite3 import Connection


def seed_reference_data(connection: Connection) -> None:
    connection.executemany(
        "INSERT OR IGNORE INTO organ_systems(code,name,system_type,functions) VALUES(?,?,?,?)",
        (
            ("TAM", "Tâm", "zang", "Chủ huyết mạch, tàng thần"),
            ("CAN", "Can", "zang", "Tàng huyết, chủ sơ tiết"),
            ("TY", "Tỳ", "zang", "Chủ vận hóa, thống huyết"),
            ("PHE", "Phế", "zang", "Chủ khí, tuyên phát túc giáng"),
            ("THAN", "Thận", "zang", "Tàng tinh, chủ thủy"),
            ("VI", "Vị", "fu", "Thu nạp và làm chín thủy cốc"),
        ),
    )
    connection.executemany(
        "INSERT OR IGNORE INTO theory_concepts(code,name,concept_type,description) VALUES(?,?,?,?)",
        (
            ("KHI", "Khí", "qi", "Nền tảng vận động và chức năng"),
            ("HUYET", "Huyết", "blood", "Dinh dưỡng và nuôi dưỡng cơ thể"),
            ("AM", "Âm", "yin_yang", "Tính tĩnh, trong, mát"),
            ("DUONG", "Dương", "yin_yang", "Tính động, ngoài, ấm"),
        ),
    )
    connection.executemany(
        "INSERT OR IGNORE INTO symptoms(code,name,description,category) VALUES(?,?,?,?)",
        (
            ("DAUDAU", "Đau đầu", "Đau vùng đầu", "đau"),
            ("MATNGU", "Mất ngủ", "Khó ngủ hoặc ngủ không sâu", "thần chí"),
            ("METMOI", "Mệt mỏi", "Cảm giác thiếu sức", "toàn thân"),
        ),
    )
    connection.executemany(
        """INSERT OR IGNORE INTO tcm_syndromes
        (code,name,eight_principles,pathogenesis,treatment_principle,description)
        VALUES(?,?,?,?,?,?)""",
        (
            (
                "TYKHIHU",
                "Tỳ khí hư",
                "Lý - Hư",
                "Tỳ vận hóa suy",
                "Kiện tỳ ích khí",
                "Mẫu tham khảo",
            ),
            (
                "CANUAT",
                "Can khí uất",
                "Lý - Thực",
                "Can mất sơ tiết",
                "Sơ can lý khí",
                "Mẫu tham khảo",
            ),
            ("TAMTYHU", "Tâm Tỳ hư", "Lý - Hư", "Tâm huyết và Tỳ khí đều hư",
             "Bổ ích Tâm Tỳ, dưỡng huyết an thần", "Mẫu tham khảo"),
            ("THANAMHU", "Thận âm hư", "Lý - Hư - Nhiệt", "Thận âm hao tổn",
             "Tư bổ Thận âm", "Mẫu tham khảo"),
            ("PHẾKHIHU", "Phế khí hư", "Lý - Hư", "Phế khí bất túc",
             "Bổ ích Phế khí", "Mẫu tham khảo"),
            ("DAMTHAP", "Đàm thấp", "Lý - Thực", "Tỳ mất kiện vận, đàm thấp nội sinh",
             "Kiện Tỳ hóa đàm, táo thấp", "Mẫu tham khảo"),
        ),
    )
    connection.executemany(
        "INSERT OR IGNORE INTO diseases"
        "(code,name,medicine_system,icd_code,description) VALUES(?,?,?,?,?)",
        (
            ("TCM-TT", "Thất miên", "tcm", "", "Bệnh danh Đông y tham khảo"),
            ("WEST-G47", "Rối loạn giấc ngủ", "western", "G47", "Tham chiếu Tây y"),
        ),
    )
    connection.executemany(
        "INSERT OR IGNORE INTO herb_categories(code,name,description) VALUES(?,?,?)",
        (("BO_KHI", "Bổ khí", "Dược liệu bổ ích khí"), ("LY_KHI", "Lý khí", "Dược liệu điều khí")),
    )
    connection.executemany(
        """INSERT OR IGNORE INTO materia_medica
        (code,name_vi,name_cn,pharmaceutical_name,nature,flavor,properties,meridians,functions,
         dosage_min,dosage_max,dosage_unit,preparation,contraindications,reference_source)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            (
                "NHANSAM",
                "Nhân sâm",
                "人參",
                "Ginseng Radix",
                "ôn",
                "cam, vi khổ",
                "đại bổ nguyên khí",
                "Tỳ, Phế",
                "Bổ khí",
                3,
                9,
                "g",
                "Sắc",
                "Thận trọng theo chuyên môn",
                "Dữ liệu mẫu",
            ),
            (
                "BACHET",
                "Bạch truật",
                "白朮",
                "Atractylodis Macrocephalae Rhizoma",
                "ôn",
                "khổ, cam",
                "kiện tỳ",
                "Tỳ, Vị",
                "Kiện tỳ ích khí",
                6,
                12,
                "g",
                "Sắc",
                "Thận trọng theo chuyên môn",
                "Dữ liệu mẫu",
            ),
        ),
    )
    connection.executemany(
        """INSERT OR IGNORE INTO formulas
        (code,name,name_cn,category,treatment_principle,indications,dosage_form,directions,
         modifications,contraindications,interactions,reference_source)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            (
                "TQTH", "Tứ Quân Tử Thang", "四君子湯", "Bổ khí", "Ích khí kiện tỳ",
                "Tỳ khí hư tham khảo", "Thang", "Bác sĩ quyết định liều và cách dùng",
                "Gia giảm theo biện chứng", "Không tự ý sử dụng",
                "Kiểm tra tương tác trước sử dụng", "Dữ liệu mẫu",
            ),
            (
                "QTT", "Quy Tỳ Thang", "歸脾湯", "Bổ ích", "Bổ ích Tâm Tỳ, dưỡng huyết an thần",
                "Tâm Tỳ hư, mất ngủ tham khảo", "Thang",
                "Bác sĩ quyết định liều và cách dùng", "Gia giảm theo biện chứng",
                "Không tự ý sử dụng", "Kiểm tra tương tác trước sử dụng", "Dữ liệu mẫu",
            ),
            (
                "TSD", "Tiêu Dao Tán", "逍遙散", "Hòa giải", "Sơ can kiện Tỳ, dưỡng huyết",
                "Can khí uất tham khảo", "Tán", "Bác sĩ quyết định liều và cách dùng",
                "Gia giảm theo biện chứng", "Không tự ý sử dụng",
                "Kiểm tra tương tác trước sử dụng", "Dữ liệu mẫu",
            ),
        ),
    )
    formula = connection.execute("SELECT id FROM formulas WHERE code='TQTH'").fetchone()
    for code, role, dosage in (("NHANSAM", "quân", 6), ("BACHET", "thần", 9)):
        herb = connection.execute("SELECT id FROM materia_medica WHERE code=?", (code,)).fetchone()
        if formula and herb:
            connection.execute(
                """INSERT OR IGNORE INTO formula_ingredients
                (formula_id,herb_id,role,dosage,unit,preparation) VALUES(?,?,?,?,?,?)""",
                (formula[0], herb[0], role, dosage, "g", "Sắc"),
            )
