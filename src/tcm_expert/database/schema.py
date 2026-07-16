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
    (
        4,
        """
        CREATE TABLE inquiry_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL UNIQUE,
            cold_heat TEXT NOT NULL DEFAULT '',
            sweating TEXT NOT NULL DEFAULT '',
            head_body TEXT NOT NULL DEFAULT '',
            chest_abdomen TEXT NOT NULL DEFAULT '',
            appetite_taste TEXT NOT NULL DEFAULT '',
            thirst_drink TEXT NOT NULL DEFAULT '',
            sleep TEXT NOT NULL DEFAULT '',
            stool TEXT NOT NULL DEFAULT '',
            urination TEXT NOT NULL DEFAULT '',
            ears_eyes TEXT NOT NULL DEFAULT '',
            gynecology TEXT NOT NULL DEFAULT '',
            onset_progress TEXT NOT NULL DEFAULT '',
            current_treatment TEXT NOT NULL DEFAULT '',
            red_flags TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            recorded_by TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_inquiry_consultation
            ON inquiry_findings(consultation_id);
        """,
    ),
    (
        5,
        """
        CREATE TABLE pulse_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('left','right')),
            position TEXT NOT NULL CHECK(position IN ('cun','guan','chi')),
            depth TEXT NOT NULL DEFAULT '',
            rate TEXT NOT NULL DEFAULT '',
            strength TEXT NOT NULL DEFAULT '',
            rhythm TEXT NOT NULL DEFAULT '',
            quality TEXT NOT NULL DEFAULT '',
            bpm INTEGER CHECK(bpm IS NULL OR bpm BETWEEN 20 AND 250),
            note TEXT NOT NULL DEFAULT '',
            recorded_by TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE,
            UNIQUE(consultation_id, side, position)
        );
        CREATE INDEX idx_pulse_consultation ON pulse_findings(consultation_id);

        CREATE TABLE palpation_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            body_area TEXT NOT NULL,
            finding_type TEXT NOT NULL CHECK(finding_type IN
                ('temperature','tenderness','mass','skin','abdomen','acupoint','other')),
            characteristic TEXT NOT NULL,
            severity INTEGER NOT NULL DEFAULT 0 CHECK(severity BETWEEN 0 AND 10),
            note TEXT NOT NULL DEFAULT '',
            recorded_by TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_palpation_consultation ON palpation_findings(consultation_id);
        """,
    ),
    (
        6,
        """
        CREATE TABLE prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            recommendation_id INTEGER NOT NULL,
            prescription_code TEXT NOT NULL UNIQUE,
            diagnosis TEXT NOT NULL,
            treatment_principle TEXT NOT NULL DEFAULT '',
            directions TEXT NOT NULL,
            modifications TEXT NOT NULL DEFAULT '',
            safety_notes TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft','approved','dispensed','cancelled')),
            approved_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE,
            FOREIGN KEY(recommendation_id) REFERENCES formula_recommendations(id),
            CHECK(status='draft' OR approved_at IS NOT NULL)
        );
        CREATE INDEX idx_prescriptions_consultation ON prescriptions(consultation_id);

        CREATE TABLE prescription_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prescription_id INTEGER NOT NULL,
            herb_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT '',
            dosage REAL NOT NULL CHECK(dosage > 0),
            unit TEXT NOT NULL DEFAULT 'g',
            preparation TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE,
            FOREIGN KEY(herb_id) REFERENCES materia_medica(id),
            UNIQUE(prescription_id, herb_id)
        );
        """,
    ),
    (
        7,
        """
        CREATE TABLE tongue_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            original_image_path TEXT NOT NULL,
            image_sha256 TEXT NOT NULL,
            image_width INTEGER NOT NULL,
            image_height INTEGER NOT NULL,
            quality_score REAL NOT NULL CHECK(quality_score BETWEEN 0 AND 1),
            quality_issues TEXT NOT NULL DEFAULT '',
            segmentation_confidence REAL NOT NULL DEFAULT 0
                CHECK(segmentation_confidence BETWEEN 0 AND 1),
            tongue_color TEXT NOT NULL DEFAULT '',
            coating_color TEXT NOT NULL DEFAULT '',
            coating_thickness TEXT NOT NULL DEFAULT '',
            teeth_marks INTEGER NOT NULL DEFAULT 0 CHECK(teeth_marks IN (0,1)),
            cracks INTEGER NOT NULL DEFAULT 0 CHECK(cracks IN (0,1)),
            ai_confidence REAL NOT NULL DEFAULT 0 CHECK(ai_confidence BETWEEN 0 AND 1),
            ai_detail TEXT NOT NULL DEFAULT '{}',
            doctor_tongue_color TEXT NOT NULL DEFAULT '',
            doctor_coating_color TEXT NOT NULL DEFAULT '',
            doctor_coating_thickness TEXT NOT NULL DEFAULT '',
            doctor_teeth_marks INTEGER
                CHECK(doctor_teeth_marks IS NULL OR doctor_teeth_marks IN (0,1)),
            doctor_cracks INTEGER CHECK(doctor_cracks IS NULL OR doctor_cracks IN (0,1)),
            doctor_note TEXT NOT NULL DEFAULT '',
            reviewed_by TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_tongue_analysis_consultation
            ON tongue_analyses(consultation_id, created_at DESC);
        CREATE INDEX idx_tongue_analysis_sha256 ON tongue_analyses(image_sha256);
        """,
    ),
    (
        8,
        """
        CREATE TABLE audio_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            sample_type TEXT NOT NULL CHECK(sample_type IN ('voice','cough','breathing','other')),
            source_mode TEXT NOT NULL DEFAULT 'file' CHECK(source_mode IN ('file','manual')),
            original_audio_path TEXT NOT NULL DEFAULT '',
            audio_sha256 TEXT NOT NULL DEFAULT '',
            duration_seconds REAL NOT NULL DEFAULT 0 CHECK(duration_seconds >= 0),
            sample_rate INTEGER NOT NULL DEFAULT 0 CHECK(sample_rate >= 0),
            channels INTEGER NOT NULL DEFAULT 0 CHECK(channels >= 0),
            quality_score REAL NOT NULL DEFAULT 0 CHECK(quality_score BETWEEN 0 AND 1),
            quality_issues TEXT NOT NULL DEFAULT '',
            rms_level REAL NOT NULL DEFAULT 0,
            peak_level REAL NOT NULL DEFAULT 0,
            zero_crossing_rate REAL NOT NULL DEFAULT 0,
            dominant_frequency REAL NOT NULL DEFAULT 0,
            pattern_label TEXT NOT NULL DEFAULT '',
            ai_confidence REAL NOT NULL DEFAULT 0 CHECK(ai_confidence BETWEEN 0 AND 1),
            ai_detail TEXT NOT NULL DEFAULT '{}',
            manual_characteristic TEXT NOT NULL DEFAULT '',
            doctor_pattern_label TEXT NOT NULL DEFAULT '',
            doctor_note TEXT NOT NULL DEFAULT '',
            reviewed_by TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_audio_analysis_consultation
            ON audio_analyses(consultation_id, created_at DESC);
        CREATE INDEX idx_audio_analysis_sha256 ON audio_analyses(audio_sha256);
        """,
    ),
    (
        9,
        """
        CREATE TABLE clinical_decision_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            completeness_score REAL NOT NULL CHECK(completeness_score BETWEEN 0 AND 1),
            risk_level TEXT NOT NULL CHECK(risk_level IN ('low','moderate','high')),
            report_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','reviewed')),
            reviewed_by TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_clinical_report_consultation
            ON clinical_decision_reports(consultation_id, created_at DESC);
        """,
    ),
    (
        10,
        """
        ALTER TABLE formulas ADD COLUMN source_type TEXT NOT NULL DEFAULT 'system'
            CHECK(source_type IN ('system','doctor'));
        ALTER TABLE formulas ADD COLUMN created_by TEXT NOT NULL DEFAULT '';
        ALTER TABLE formulas ADD COLUMN doctor_approved INTEGER NOT NULL DEFAULT 1
            CHECK(doctor_approved IN (0,1));
        ALTER TABLE formulas ADD COLUMN ingredients_text TEXT NOT NULL DEFAULT '';
        CREATE INDEX idx_formulas_source ON formulas(source_type,created_by,active);
        """,
    ),
    (
        11,
        """
        CREATE TABLE doctor_profile (
            id INTEGER PRIMARY KEY CHECK(id=1),
            full_name TEXT NOT NULL DEFAULT '',
            license_number TEXT NOT NULL DEFAULT '',
            specialty TEXT NOT NULL DEFAULT '',
            workplace TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT OR IGNORE INTO doctor_profile(id) VALUES(1);

        CREATE TABLE patient_code_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            prefix TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT OR IGNORE INTO patient_code_groups(name,prefix) VALUES('Bệnh nhân chung','BN');
        INSERT OR IGNORE INTO patient_code_groups(name,prefix) VALUES('Tiêu hóa','TH');

        ALTER TABLE consultations ADD COLUMN patient_status TEXT NOT NULL
            DEFAULT 'under_treatment' CHECK(patient_status IN
            ('under_treatment','monitoring','completed'));

        ALTER TABLE materia_medica ADD COLUMN image_path TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN modern_effects TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN combinations TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN processing TEXT NOT NULL DEFAULT '';
        ALTER TABLE materia_medica ADD COLUMN cautions TEXT NOT NULL DEFAULT '';
        """,
    ),
    (12, """
        CREATE TABLE ai_settings (
            id INTEGER PRIMARY KEY CHECK(id=1),
            enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
            translator TEXT NOT NULL DEFAULT 'Vietnamese-Chinese',
            reasoner TEXT NOT NULL DEFAULT 'TCMChat',
            knowledge_sources TEXT NOT NULL DEFAULT 'OpenTCM GraphRAG,TCMBank,SymMap',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT OR IGNORE INTO ai_settings(id,enabled) VALUES(1,0);
    """),
    (13, """
        ALTER TABLE ai_settings ADD COLUMN mode TEXT NOT NULL DEFAULT 'offline';
        ALTER TABLE ai_settings ADD COLUMN chat_base_url TEXT NOT NULL DEFAULT '';
        ALTER TABLE ai_settings ADD COLUMN chat_model TEXT NOT NULL DEFAULT 'tcmchat';
        ALTER TABLE ai_settings ADD COLUMN opentcm_url TEXT NOT NULL DEFAULT '';
        ALTER TABLE ai_settings ADD COLUMN tcmbank_url TEXT NOT NULL DEFAULT '';
        ALTER TABLE ai_settings ADD COLUMN symmap_url TEXT NOT NULL DEFAULT '';
        ALTER TABLE ai_settings ADD COLUMN timeout_seconds INTEGER NOT NULL DEFAULT 20;
    """),
    (14, """
        ALTER TABLE clinical_decision_reports ADD COLUMN report_type TEXT NOT NULL
            DEFAULT 'rule' CHECK(report_type IN ('rule','ai'));
        ALTER TABLE clinical_decision_reports ADD COLUMN ai_confidence REAL NOT NULL
            DEFAULT 0 CHECK(ai_confidence BETWEEN 0 AND 1);
        ALTER TABLE clinical_decision_reports ADD COLUMN doctor_decision TEXT NOT NULL
            DEFAULT 'pending' CHECK(doctor_decision IN
            ('pending','accepted','rejected','edited'));
        ALTER TABLE clinical_decision_reports ADD COLUMN decision_reason TEXT NOT NULL
            DEFAULT '';
        CREATE INDEX idx_clinical_report_type
            ON clinical_decision_reports(consultation_id,report_type,created_at DESC);
    """),
    (15, """
        CREATE TABLE treatment_followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            followup_date TEXT NOT NULL,
            treatment_status TEXT NOT NULL DEFAULT 'monitoring'
                CHECK(treatment_status IN ('improved','stable','worsened','monitoring','completed')),
            symptom_score_before INTEGER NOT NULL DEFAULT 0
                CHECK(symptom_score_before BETWEEN 0 AND 10),
            symptom_score_after INTEGER NOT NULL DEFAULT 0
                CHECK(symptom_score_after BETWEEN 0 AND 10),
            effectiveness TEXT NOT NULL DEFAULT 'not_assessed'
                CHECK(effectiveness IN ('good','partial','none','not_assessed')),
            adverse_reactions TEXT NOT NULL DEFAULT '',
            adherence TEXT NOT NULL DEFAULT '',
            doctor_note TEXT NOT NULL DEFAULT '',
            reviewed_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_treatment_followup_consultation
            ON treatment_followups(consultation_id,followup_date DESC,id DESC);
    """),
    (16, """
        CREATE TABLE treatment_outcome_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            report_json TEXT NOT NULL,
            doctor_conclusion TEXT NOT NULL,
            reviewed_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_outcome_report_period
            ON treatment_outcome_reports(period_start,period_end,created_at DESC);
    """),
    (17, """
        CREATE TABLE followup_appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER NOT NULL,
            scheduled_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'scheduled'
                CHECK(status IN ('scheduled','confirmed','completed','cancelled','no_show')),
            reason TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            responsible_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_followup_appointment_time
            ON followup_appointments(scheduled_at,status,id);
        CREATE INDEX idx_followup_appointment_consultation
            ON followup_appointments(consultation_id,scheduled_at DESC,id DESC);
    """),
    (18, """
        CREATE TABLE appointment_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            reminded_at TEXT NOT NULL,
            reminded_by TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(appointment_id) REFERENCES followup_appointments(id)
                ON DELETE CASCADE
        );
        CREATE INDEX idx_appointment_reminder_appointment
            ON appointment_reminders(appointment_id,reminded_at DESC,id DESC);
    """),
    (19, """
        CREATE TABLE appointment_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL UNIQUE,
            shown_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(appointment_id) REFERENCES followup_appointments(id)
                ON DELETE CASCADE
        );
        CREATE INDEX idx_appointment_alert_shown
            ON appointment_alerts(shown_at DESC,id DESC);
    """),
    (20, """
        ALTER TABLE followup_appointments ADD COLUMN case_state TEXT NOT NULL
            DEFAULT 'active'
            CHECK(case_state IN (
                'active','history_reference','reopened','medical_record','cancelled_90'
            ));
        ALTER TABLE followup_appointments ADD COLUMN overdue_note TEXT NOT NULL DEFAULT '';
        ALTER TABLE followup_appointments ADD COLUMN reviewed_by TEXT NOT NULL DEFAULT '';
        ALTER TABLE followup_appointments ADD COLUMN reviewed_at TEXT;
        CREATE INDEX idx_followup_appointment_case_state
            ON followup_appointments(case_state,scheduled_at,id);
    """),
    (21, """
        ALTER TABLE appointment_alerts ADD COLUMN acknowledged_at TEXT;
        ALTER TABLE appointment_alerts ADD COLUMN acknowledged_by TEXT NOT NULL DEFAULT '';
        CREATE INDEX idx_appointment_alert_acknowledged
            ON appointment_alerts(acknowledged_at,shown_at,id);
    """),
    (22, """
        CREATE TABLE app_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','doctor','nurse')),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
            must_change_password INTEGER NOT NULL DEFAULT 0 CHECK(must_change_password IN (0,1)),
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            last_login_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_app_users_active_role ON app_users(active,role,username);

        CREATE TABLE user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            logged_in_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            logged_out_at TEXT,
            logout_reason TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES app_users(id)
        );
        CREATE INDEX idx_user_sessions_user ON user_sessions(user_id,logged_in_at DESC);

        ALTER TABLE audit_log ADD COLUMN actor_user_id INTEGER REFERENCES app_users(id);
        ALTER TABLE audit_log ADD COLUMN actor_username TEXT NOT NULL DEFAULT '';
    """),
    (23, """
        CREATE INDEX idx_audit_log_created
            ON audit_log(created_at DESC,id DESC);
        CREATE INDEX idx_audit_log_actor
            ON audit_log(actor_username,created_at DESC,id DESC);
        CREATE INDEX idx_audit_log_entity
            ON audit_log(entity_type,action,created_at DESC,id DESC);
    """),
)
