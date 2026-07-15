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
)

