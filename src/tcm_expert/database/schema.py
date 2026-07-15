MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            birth_date TEXT,
            sex TEXT,
            phone TEXT,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            symptoms TEXT NOT NULL DEFAULT '',
            observation TEXT NOT NULL DEFAULT '',
            listening_smelling TEXT NOT NULL DEFAULT '',
            inquiry TEXT NOT NULL DEFAULT '',
            palpation TEXT NOT NULL DEFAULT '',
            assessment TEXT NOT NULL DEFAULT '',
            doctor_approved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        );
        CREATE TABLE IF NOT EXISTS materia_medica (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_vi TEXT NOT NULL UNIQUE,
            name_cn TEXT NOT NULL DEFAULT '',
            properties TEXT NOT NULL DEFAULT '',
            meridians TEXT NOT NULL DEFAULT '',
            functions TEXT NOT NULL DEFAULT '',
            contraindications TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS formula_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            indications TEXT NOT NULL DEFAULT '',
            composition TEXT NOT NULL DEFAULT '',
            cautions TEXT NOT NULL DEFAULT '',
            reference_source TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            detail TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
    (
        2,
        """
        ALTER TABLE patients ADD COLUMN identity_number TEXT NOT NULL DEFAULT '';
        ALTER TABLE patients ADD COLUMN address TEXT NOT NULL DEFAULT '';
        ALTER TABLE patients ADD COLUMN emergency_contact TEXT NOT NULL DEFAULT '';
        ALTER TABLE patients ADD COLUMN allergies TEXT NOT NULL DEFAULT '';
        ALTER TABLE patients ADD COLUMN deleted_at TEXT;

        ALTER TABLE consultations ADD COLUMN visit_code TEXT NOT NULL DEFAULT '';
        ALTER TABLE consultations ADD COLUMN chief_complaint TEXT NOT NULL DEFAULT '';
        ALTER TABLE consultations ADD COLUMN western_history TEXT NOT NULL DEFAULT '';
        ALTER TABLE consultations ADD COLUMN doctor_name TEXT NOT NULL DEFAULT '';
        ALTER TABLE consultations ADD COLUMN approved_at TEXT;
        ALTER TABLE consultations ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';

        CREATE UNIQUE INDEX IF NOT EXISTS idx_consultations_visit_code
            ON consultations(visit_code) WHERE visit_code <> '';
        CREATE INDEX IF NOT EXISTS idx_consultations_patient ON consultations(patient_id);
        CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(full_name);

        CREATE TABLE diagnostic_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            method TEXT NOT NULL CHECK(method IN ('vong','van','van_hoi','thiet')),
            category TEXT NOT NULL,
            finding TEXT NOT NULL,
            severity INTEGER CHECK(severity BETWEEN 0 AND 10),
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_diagnostic_consultation ON diagnostic_entries(consultation_id);

        CREATE TABLE symptoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE consultation_symptoms (
            consultation_id INTEGER NOT NULL,
            symptom_id INTEGER NOT NULL,
            severity INTEGER NOT NULL DEFAULT 0 CHECK(severity BETWEEN 0 AND 10),
            duration TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(consultation_id, symptom_id),
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE,
            FOREIGN KEY(symptom_id) REFERENCES symptoms(id)
        );

        CREATE TABLE organ_systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            system_type TEXT NOT NULL CHECK(system_type IN ('zang','fu','extraordinary')),
            functions TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE meridians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            yin_yang TEXT NOT NULL CHECK(yin_yang IN ('yin','yang')),
            paired_organ_id INTEGER,
            description TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(paired_organ_id) REFERENCES organ_systems(id)
        );
        CREATE TABLE theory_concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            concept_type TEXT NOT NULL CHECK(concept_type IN ('qi','blood','fluid','yin_yang')),
            description TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE tcm_syndromes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            eight_principles TEXT NOT NULL DEFAULT '',
            pathogenesis TEXT NOT NULL DEFAULT '',
            treatment_principle TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE consultation_syndromes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            syndrome_id INTEGER NOT NULL,
            confidence REAL NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 1),
            evidence TEXT NOT NULL DEFAULT '',
            is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN (0,1)),
            doctor_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(doctor_confirmed IN (0,1)),
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE,
            FOREIGN KEY(syndrome_id) REFERENCES tcm_syndromes(id),
            UNIQUE(consultation_id, syndrome_id)
        );

        CREATE TABLE diseases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            medicine_system TEXT NOT NULL CHECK(medicine_system IN ('tcm','western')),
            icd_code TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            UNIQUE(name, medicine_system)
        );
        CREATE TABLE disease_relations (
            tcm_disease_id INTEGER NOT NULL,
            western_disease_id INTEGER NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(tcm_disease_id, western_disease_id),
            FOREIGN KEY(tcm_disease_id) REFERENCES diseases(id),
            FOREIGN KEY(western_disease_id) REFERENCES diseases(id)
        );
        CREATE TABLE consultation_diseases (
            consultation_id INTEGER NOT NULL,
            disease_id INTEGER NOT NULL,
            diagnosis_type TEXT NOT NULL DEFAULT 'differential',
            doctor_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(doctor_confirmed IN (0,1)),
            PRIMARY KEY(consultation_id, disease_id),
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE,
            FOREIGN KEY(disease_id) REFERENCES diseases(id)
        );

        CREATE TABLE herb_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT ''
        );
        ALTER TABLE materia_medica ADD COLUMN code TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN category_id INTEGER;
        ALTER TABLE materia_medica ADD COLUMN pharmaceutical_name TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN nature TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN flavor TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN dosage_min REAL;
        ALTER TABLE materia_medica ADD COLUMN dosage_max REAL;
        ALTER TABLE materia_medica ADD COLUMN dosage_unit TEXT NOT NULL DEFAULT 'g';
        ALTER TABLE materia_medica ADD COLUMN preparation TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN toxicity TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN reference_source TEXT NOT NULL DEFAULT '';
        CREATE UNIQUE INDEX idx_materia_code ON materia_medica(code) WHERE code <> '';

        CREATE TABLE formulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            name_cn TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            treatment_principle TEXT NOT NULL DEFAULT '',
            indications TEXT NOT NULL DEFAULT '',
            dosage_form TEXT NOT NULL DEFAULT '',
            directions TEXT NOT NULL DEFAULT '',
            modifications TEXT NOT NULL DEFAULT '',
            contraindications TEXT NOT NULL DEFAULT '',
            interactions TEXT NOT NULL DEFAULT '',
            reference_source TEXT NOT NULL DEFAULT '',
            disclaimer TEXT NOT NULL DEFAULT 'Bài thuốc chỉ mang tính tham khảo.',
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
        );
        CREATE TABLE formula_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formula_id INTEGER NOT NULL,
            herb_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT '',
            dosage REAL NOT NULL CHECK(dosage > 0),
            unit TEXT NOT NULL DEFAULT 'g',
            preparation TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(formula_id) REFERENCES formulas(id) ON DELETE CASCADE,
            FOREIGN KEY(herb_id) REFERENCES materia_medica(id),
            UNIQUE(formula_id, herb_id)
        );
        CREATE TABLE herb_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            herb_id INTEGER NOT NULL,
            interacting_herb_id INTEGER,
            interacting_drug TEXT NOT NULL DEFAULT '',
            severity TEXT NOT NULL CHECK(severity IN ('low','moderate','high','contraindicated')),
            effect TEXT NOT NULL,
            recommendation TEXT NOT NULL DEFAULT '',
            reference_source TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(herb_id) REFERENCES materia_medica(id),
            FOREIGN KEY(interacting_herb_id) REFERENCES materia_medica(id),
            CHECK(interacting_herb_id IS NOT NULL OR interacting_drug <> '')
        );
        CREATE TABLE formula_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            formula_id INTEGER NOT NULL,
            custom_directions TEXT NOT NULL DEFAULT '',
            modifications TEXT NOT NULL DEFAULT '',
            safety_notes TEXT NOT NULL DEFAULT '',
            doctor_approved INTEGER NOT NULL DEFAULT 0 CHECK(doctor_approved IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE,
            FOREIGN KEY(formula_id) REFERENCES formulas(id)
        );
        """,
    ),
    (
        3,
        """
        CREATE TABLE listening_smelling_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            finding_type TEXT NOT NULL CHECK(finding_type IN
                ('voice','breathing','cough','sputum','hiccup','pathological_sound','odor','other')),
            characteristic TEXT NOT NULL,
            frequency TEXT NOT NULL DEFAULT '',
            severity INTEGER NOT NULL DEFAULT 0 CHECK(severity BETWEEN 0 AND 10),
            duration TEXT NOT NULL DEFAULT '',
            odor TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            recorded_by TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_listening_smelling_consultation
            ON listening_smelling_findings(consultation_id);
        CREATE INDEX idx_listening_smelling_type
            ON listening_smelling_findings(finding_type);
        """,
    ),
)
