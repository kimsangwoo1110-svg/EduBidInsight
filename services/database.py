import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime

from services.region_data import ALL, office_filter_values, region_filter_values


DB_NAME = "data/edubid.db"

DEFAULT_RULES = (
    (
        "AI 교육",
        {"any": [
            {"field": "category", "operator": "contains", "value": "AI"},
            {"field": "project_name", "operator": "contains", "value": "AI"},
        ]},
        "AI 교육 솔루션 제안",
        40,
        "AI 관련 교육환경 구축 수요가 확인되었습니다.",
        1,
    ),
    (
        "공간혁신",
        {"any": [
            {"field": "category", "operator": "contains", "value": "공간"},
            {"field": "project_name", "operator": "contains", "value": "공간"},
        ]},
        "공간혁신 기자재 제안",
        35,
        "공간혁신 관련 프로젝트가 확인되었습니다.",
        1,
    ),
    (
        "사업 단계",
        {"field": "status", "operator": "in", "value": ["예정", "진행중"]},
        "사업 담당자 사전 접촉",
        20,
        "제안 활동이 가능한 사업 단계입니다.",
        1,
    ),
    (
        "예산",
        {"field": "budget", "operator": "gte", "value": 100000000},
        "대형 사업 맞춤 제안",
        25,
        "예산 1억원 이상의 대형 프로젝트입니다.",
        1,
    ),
)


def configure_database(file_path):
    """Point database access at a settings-managed SQLite file."""
    global DB_NAME
    selected = str(file_path or "").strip()
    if not selected:
        raise ValueError("database file path is required")
    DB_NAME = os.path.abspath(selected)
    return DB_NAME


def get_connection():
    """Open a SQLite connection compatible with the existing local database."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_NAME)), exist_ok=True)
    return sqlite3.connect(DB_NAME)


def create_database():
    """Create compatible school, project, and opportunity-rule tables."""
    with closing(get_connection()) as conn, conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schools(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT UNIQUE,
                school_name TEXT NOT NULL,
                office TEXT,
                region TEXT,
                school_type TEXT,
                address TEXT,
                homepage TEXT,
                ai_school INTEGER DEFAULT 0,
                digital_school INTEGER DEFAULT 0,
                space_innovation INTEGER DEFAULT 0,
                green_smart INTEGER DEFAULT 0,
                student_count INTEGER DEFAULT 0,
                class_count INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """
        )
        _ensure_table_columns(
            cursor,
            "schools",
            {
                "school_code": "TEXT",
                "school_name": "TEXT",
                "office": "TEXT",
                "region": "TEXT",
                "school_type": "TEXT",
                "address": "TEXT",
                "homepage": "TEXT",
                "ai_school": "INTEGER DEFAULT 0",
                "digital_school": "INTEGER DEFAULT 0",
                "space_innovation": "INTEGER DEFAULT 0",
                "green_smart": "INTEGER DEFAULT 0",
                "student_count": "INTEGER DEFAULT 0",
                "class_count": "INTEGER DEFAULT 0",
                "updated_at": "TEXT",
            },
        )
        rules_table_exists = cursor.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'rules'
            """
        ).fetchone() is not None
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rules(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                condition TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                description TEXT,
                enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1))
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rules_enabled ON rules(enabled)"
        )
        if not rules_table_exists:
            cursor.executemany(
                """
                INSERT INTO rules(
                    category, condition, recommendation, score, description, enabled
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (category, json.dumps(condition, ensure_ascii=False),
                     recommendation, score, description, enabled)
                    for category, condition, recommendation, score, description, enabled
                    in DEFAULT_RULES
                ],
            )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_school_name ON schools(school_name)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_region ON schools(region)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_office ON schools(office)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_school_type ON schools(school_type)"
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_school_search_filters
            ON schools(region, school_type, office, school_name)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT NOT NULL,
                project_name TEXT NOT NULL,
                category TEXT,
                status TEXT,
                budget REAL DEFAULT 0,
                start_year INTEGER,
                end_year INTEGER,
                source TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_project_school_code
            ON projects(school_code)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_project_school_year
            ON projects(school_code, start_year DESC)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS education_office_import_keys(
                record_key TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                office TEXT,
                region TEXT,
                fiscal_year INTEGER,
                start_date TEXT,
                end_date TEXT,
                imported_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_education_office_project "
            "ON education_office_import_keys(project_id)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS contracts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT NOT NULL,
                school_name TEXT NOT NULL,
                contract_date TEXT NOT NULL,
                product TEXT NOT NULL,
                category TEXT,
                vendor TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                amount REAL NOT NULL DEFAULT 0,
                source_file TEXT,
                imported_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contract_school ON contracts(school_code)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contract_vendor ON contracts(vendor)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contract_product ON contracts(product)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contract_date ON contracts(contract_date DESC)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schoolmarket_import_keys(
                record_key TEXT PRIMARY KEY,
                contract_number TEXT,
                contract_id INTEGER NOT NULL,
                imported_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_schoolmarket_contract_number
            ON schoolmarket_import_keys(contract_number)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS g2b_import_keys(
                record_key TEXT PRIMARY KEY,
                contract_number TEXT,
                notice_number TEXT,
                contract_id INTEGER NOT NULL,
                imported_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_g2b_contract_number "
            "ON g2b_import_keys(contract_number)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_g2b_notice_number "
            "ON g2b_import_keys(notice_number)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                inserted INTEGER NOT NULL DEFAULT 0,
                updated INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                duration REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sync_history_started
            ON sync_history(started_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS import_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imported_at TEXT NOT NULL,
                source_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                result TEXT NOT NULL,
                imported_rows INTEGER NOT NULL DEFAULT 0
                    CHECK(imported_rows >= 0)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_import_history_imported_at
            ON import_history(imported_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                summary TEXT NOT NULL,
                recommended_products TEXT NOT NULL,
                next_action TEXT NOT NULL,
                risk TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recommendation_history_school
            ON recommendation_history(school_code, created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunity_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id TEXT NOT NULL,
                school_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunity_history_school
            ON opportunity_history(school_id, id DESC)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS crm_actions(
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT,
                completed_date TEXT,
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_crm_actions_school
            ON crm_actions(school_id, updated_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_crm_actions_due_status
            ON crm_actions(due_date, status)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS crm_action_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                changed_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                note TEXT,
                completed_at TEXT,
                FOREIGN KEY(action_id) REFERENCES crm_actions(action_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_crm_action_history_action
            ON crm_action_history(action_id, id DESC)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_activity(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT NOT NULL,
                activity_date TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                contact_person TEXT,
                memo TEXT,
                next_action_date TEXT,
                status TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sales_activity_school_date
            ON sales_activity(school_code, activity_date DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sales_activity_next_action
            ON sales_activity(next_action_date, status)
            """
        )


def clear_school_data():
    with closing(get_connection()) as conn, conn:
        conn.execute("DELETE FROM schools")


def _ensure_table_columns(cursor, table_name, columns):
    """Add columns missing from an older compatible SQLite table."""
    existing_columns = {
        row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})")
    }
    for column_name, definition in columns.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
            )


def school_exists(school_code, connection=None):
    """Return whether a non-empty school code already exists."""
    code = str(school_code or "").strip()
    if not code:
        return False

    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        return conn.execute(
            "SELECT 1 FROM schools WHERE school_code = ? LIMIT 1", (code,)
        ).fetchone() is not None
    finally:
        if owns_connection:
            conn.close()


def add_school(
    school_code,
    name,
    office,
    region,
    school_type,
    address,
    homepage="",
    ai_school=0,
    digital_school=0,
    space_innovation=0,
    green_smart=0,
    student_count=0,
    class_count=0,
    connection=None,
    commit=True,
):
    """Insert or update a school while preserving its existing row identity."""
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        conn.execute(
            """
            INSERT INTO schools(
                school_code, school_name, office, region, school_type, address,
                homepage, ai_school, digital_school, space_innovation,
                green_smart, student_count, class_count, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_code) DO UPDATE SET
                school_name = excluded.school_name,
                office = excluded.office,
                region = excluded.region,
                school_type = excluded.school_type,
                address = excluded.address,
                homepage = excluded.homepage,
                ai_school = excluded.ai_school,
                digital_school = excluded.digital_school,
                space_innovation = excluded.space_innovation,
                green_smart = excluded.green_smart,
                student_count = excluded.student_count,
                class_count = excluded.class_count,
                updated_at = excluded.updated_at
            """,
            (
                str(school_code or "").strip(),
                str(name or "").strip(),
                str(office or "").strip(),
                str(region or "").strip(),
                str(school_type or "").strip(),
                str(address or "").strip(),
                str(homepage or "").strip(),
                int(ai_school or 0),
                int(digital_school or 0),
                int(space_innovation or 0),
                int(green_smart or 0),
                int(student_count or 0),
                int(class_count or 0),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()


def add_project(
    school_code,
    project_name,
    category="",
    status="",
    budget=0,
    start_year=None,
    end_year=None,
    source="",
    connection=None,
    commit=True,
):
    """Create a project and return its SQLite identifier."""
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO projects(
                school_code, project_name, category, status, budget,
                start_year, end_year, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(school_code or "").strip(),
                str(project_name or "").strip(),
                str(category or "").strip(),
                str(status or "").strip(),
                float(budget or 0),
                start_year,
                end_year,
                str(source or "").strip(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        if commit:
            conn.commit()
        return cursor.lastrowid
    finally:
        if owns_connection:
            conn.close()


def education_office_key_exists(record_key, connection=None):
    """Return whether an Education Office source identity already exists."""
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        return conn.execute(
            "SELECT 1 FROM education_office_import_keys WHERE record_key = ? LIMIT 1",
            (str(record_key or "").strip(),),
        ).fetchone() is not None
    finally:
        if owns_connection:
            conn.close()


def add_education_office_key(metadata, project_id, connection):
    """Store Education Office metadata in the caller's transaction."""
    connection.execute(
        """
        INSERT INTO education_office_import_keys(
            record_key, project_id, office, region, fiscal_year,
            start_date, end_date, imported_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            metadata["record_key"],
            int(project_id),
            metadata.get("office", ""),
            metadata.get("region", ""),
            metadata.get("fiscal_year"),
            metadata.get("start_date", ""),
            metadata.get("end_date", ""),
            datetime.now().astimezone().isoformat(timespec="seconds"),
        ),
    )


def find_education_office_projects(school_code=""):
    """Return imported Education Office projects with their source metadata."""
    sql = """
        SELECT projects.id, projects.school_code, projects.project_name,
               projects.category, projects.status, projects.budget,
               projects.start_year, projects.end_year, projects.source,
               projects.updated_at, metadata.office, metadata.region,
               metadata.fiscal_year, metadata.start_date, metadata.end_date
        FROM education_office_import_keys AS metadata
        JOIN projects ON projects.id = metadata.project_id
    """
    params = ()
    if str(school_code or "").strip():
        sql += " WHERE projects.school_code = ?"
        params = (str(school_code).strip(),)
    sql += " ORDER BY metadata.fiscal_year DESC, projects.id DESC"
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def find_projects_by_school(
    school_code, project_name="", category="", status="", year=None
):
    """Return filtered projects for one school in newest-first order."""
    conditions = ["school_code = ?"]
    params = [str(school_code or "").strip()]

    name_filter = str(project_name or "").strip()
    if name_filter:
        conditions.append("project_name LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(name_filter)}%")

    if category:
        conditions.append("category = ?")
        params.append(str(category).strip())

    if status:
        conditions.append("status = ?")
        params.append(str(status).strip())

    if year is not None:
        conditions.append("start_year <= ? AND (end_year IS NULL OR end_year >= ?)")
        params.extend((year, year))

    with closing(get_connection()) as conn:
        return conn.execute(
            f"""
            SELECT
                id, school_code, project_name, category, status, budget,
                start_year, end_year, source, updated_at
            FROM projects
            WHERE {' AND '.join(conditions)}
            ORDER BY start_year DESC, project_name
            """,
            params,
        ).fetchall()


def update_project(
    project_id,
    project_name,
    category="",
    status="",
    budget=0,
    start_year=None,
    end_year=None,
    source="",
):
    """Update an existing project and return whether it was found."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE projects
            SET
                project_name = ?, category = ?, status = ?, budget = ?,
                start_year = ?, end_year = ?, source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(project_name or "").strip(),
                str(category or "").strip(),
                str(status or "").strip(),
                float(budget or 0),
                start_year,
                end_year,
                str(source or "").strip(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                project_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_project(project_id):
    """Delete a project and return whether it was found."""
    with closing(get_connection()) as conn:
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        return cursor.rowcount > 0


def add_rule(category, condition, recommendation, score, description="", enabled=True):
    """Create a rule and return its SQLite identifier."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO rules(
                category, condition, recommendation, score, description, enabled
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(category or "").strip(),
                condition,
                str(recommendation or "").strip(),
                int(score),
                str(description or "").strip(),
                int(bool(enabled)),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def find_rules(enabled_only=False):
    """Return rules in stable identifier order."""
    sql = """
        SELECT id, category, condition, recommendation, score, description, enabled
        FROM rules
    """
    params = ()
    if enabled_only:
        sql += " WHERE enabled = ?"
        params = (1,)
    sql += " ORDER BY id"
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def update_rule_enabled(rule_id, enabled):
    """Enable or disable a rule and return whether it exists."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "UPDATE rules SET enabled = ? WHERE id = ?",
            (int(bool(enabled)), rule_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_rule(
    rule_id, category, condition, recommendation, score, description="", enabled=True
):
    """Update every editable field of a rule."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE rules
            SET category = ?, condition = ?, recommendation = ?, score = ?,
                description = ?, enabled = ?
            WHERE id = ?
            """,
            (
                str(category or "").strip(),
                condition,
                str(recommendation or "").strip(),
                int(score),
                str(description or "").strip(),
                int(bool(enabled)),
                rule_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_rule(rule_id):
    """Delete a rule and return whether it existed."""
    with closing(get_connection()) as conn:
        cursor = conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        conn.commit()
        return cursor.rowcount > 0


def add_contract(contract, connection=None, commit=True):
    """Insert a validated contract and return its identifier."""
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO contracts(
                school_code, school_name, contract_date, product, category,
                vendor, quantity, amount, source_file, imported_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contract["school_code"],
                contract["school_name"],
                contract["contract_date"],
                contract["product"],
                contract.get("category", ""),
                contract["vendor"],
                contract.get("quantity", 0),
                contract["amount"],
                contract.get("source_file", ""),
                timestamp,
                timestamp,
            ),
        )
        if commit:
            conn.commit()
        return cursor.lastrowid
    finally:
        if owns_connection:
            conn.close()


def update_contract(contract_id, contract):
    """Update a validated contract."""
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE contracts
            SET school_code = ?, school_name = ?, contract_date = ?, product = ?,
                category = ?, vendor = ?, quantity = ?, amount = ?,
                source_file = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                contract["school_code"],
                contract["school_name"],
                contract["contract_date"],
                contract["product"],
                contract.get("category", ""),
                contract["vendor"],
                contract.get("quantity", 0),
                contract["amount"],
                contract.get("source_file", ""),
                timestamp,
                contract_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def find_contracts(
    keyword="", school_code="", vendor="", product="", limit=None
):
    """Return filtered contracts in most-recent order."""
    conditions = []
    params = []
    if keyword:
        escaped = _escape_like(str(keyword).strip())
        conditions.append(
            "(school_name LIKE ? ESCAPE '\\' OR product LIKE ? ESCAPE '\\' "
            "OR vendor LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\')"
        )
        params.extend([f"%{escaped}%"] * 4)
    for column, value in (
        ("school_code", school_code),
        ("vendor", vendor),
        ("product", product),
    ):
        selected = str(value or "").strip()
        if selected:
            if column == "school_code":
                conditions.append("school_code = ?")
                params.append(selected)
            else:
                conditions.append(f"{column} LIKE ? ESCAPE '\\'")
                params.append(f"%{_escape_like(selected)}%")

    sql = """
        SELECT id, school_code, school_name, contract_date, product, category,
               vendor, quantity, amount, source_file, imported_at, updated_at
        FROM contracts
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY contract_date DESC, id DESC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(max(1, int(limit)))
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def contract_duplicate_exists(contract, exclude_id=None, connection=None):
    """Check the business key used by file imports for duplicate contracts."""
    sql = """
        SELECT 1 FROM contracts
        WHERE school_code = ? AND contract_date = ? AND product = ?
          AND vendor = ? AND amount = ?
    """
    params = [
        contract["school_code"],
        contract["contract_date"],
        contract["product"],
        contract["vendor"],
        contract["amount"],
    ]
    if exclude_id is not None:
        sql += " AND id <> ?"
        params.append(exclude_id)
    sql += " LIMIT 1"
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        return conn.execute(sql, params).fetchone() is not None
    finally:
        if owns_connection:
            conn.close()


def schoolmarket_key_exists(record_key, connection=None):
    """Return whether a SchoolMarket source identity was already imported."""
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        return conn.execute(
            "SELECT 1 FROM schoolmarket_import_keys WHERE record_key = ? LIMIT 1",
            (str(record_key or "").strip(),),
        ).fetchone() is not None
    finally:
        if owns_connection:
            conn.close()


def add_schoolmarket_key(record_key, contract_number, contract_id, connection):
    """Store a SchoolMarket identity in the caller's import transaction."""
    connection.execute(
        """
        INSERT INTO schoolmarket_import_keys(
            record_key, contract_number, contract_id, imported_at
        ) VALUES (?, ?, ?, ?)
        """,
        (
            str(record_key or "").strip(),
            str(contract_number or "").strip(),
            int(contract_id),
            datetime.now().astimezone().isoformat(timespec="seconds"),
        ),
    )


def find_school_by_name(school_name, connection=None):
    """Find one school by a normalized exact name match."""
    normalized = "".join(str(school_name or "").split()).casefold()
    if not normalized:
        return None
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        rows = conn.execute(
            "SELECT school_code, school_name FROM schools ORDER BY id"
        ).fetchall()
        return next(
            (
                {"school_code": row[0], "school_name": row[1]}
                for row in rows
                if "".join(str(row[1] or "").split()).casefold() == normalized
            ),
            None,
        )
    finally:
        if owns_connection:
            conn.close()


def find_school_by_code(school_code, connection=None):
    """Return one complete school row by code, or ``None``."""
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        return conn.execute(
            """
            SELECT school_code, school_name, school_type, office, region, address,
                   homepage, ai_school, digital_school, space_innovation,
                   green_smart, student_count, class_count
            FROM schools
            WHERE school_code = ?
            LIMIT 1
            """,
            (str(school_code or "").strip(),),
        ).fetchone()
    finally:
        if owns_connection:
            conn.close()


def find_schoolmarket_contract_ids(school_code):
    """Return SchoolMarket-created contract IDs for one school."""
    with closing(get_connection()) as conn:
        return [
            row[0]
            for row in conn.execute(
                """
                SELECT keys.contract_id
                FROM schoolmarket_import_keys AS keys
                JOIN contracts ON contracts.id = keys.contract_id
                WHERE contracts.school_code = ?
                ORDER BY keys.imported_at DESC, keys.contract_id DESC
                """,
                (str(school_code or "").strip(),),
            ).fetchall()
        ]


def g2b_key_exists(record_key, connection=None):
    """Return whether a G2B source identity was already imported."""
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        return conn.execute(
            "SELECT 1 FROM g2b_import_keys WHERE record_key = ? LIMIT 1",
            (str(record_key or "").strip(),),
        ).fetchone() is not None
    finally:
        if owns_connection:
            conn.close()


def add_g2b_key(
    record_key, contract_number, notice_number, contract_id, connection
):
    """Store a G2B identity in the caller's import transaction."""
    connection.execute(
        """
        INSERT INTO g2b_import_keys(
            record_key, contract_number, notice_number, contract_id, imported_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(record_key or "").strip(),
            str(contract_number or "").strip(),
            str(notice_number or "").strip(),
            int(contract_id),
            datetime.now().astimezone().isoformat(timespec="seconds"),
        ),
    )


def find_g2b_contract_ids(school_code):
    """Return G2B-created contract IDs for one school."""
    with closing(get_connection()) as conn:
        return [
            row[0]
            for row in conn.execute(
                """
                SELECT keys.contract_id
                FROM g2b_import_keys AS keys
                JOIN contracts ON contracts.id = keys.contract_id
                WHERE contracts.school_code = ?
                ORDER BY keys.imported_at DESC, keys.contract_id DESC
                """,
                (str(school_code or "").strip(),),
            ).fetchall()
        ]


def start_sync_history(source, started_at):
    """Create a running synchronization-history row."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO sync_history(source, started_at, status)
            VALUES (?, ?, 'RUNNING')
            """,
            (str(source or "").strip(), started_at),
        )
        conn.commit()
        return cursor.lastrowid


def finish_sync_history(
    history_id,
    finished_at,
    inserted,
    updated,
    skipped,
    errors,
    duration,
    status,
):
    """Complete a synchronization-history row."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE sync_history
            SET finished_at = ?, inserted = ?, updated = ?, skipped = ?,
                errors = ?, duration = ?, status = ?
            WHERE id = ?
            """,
            (
                finished_at,
                int(inserted or 0),
                int(updated or 0),
                int(skipped or 0),
                int(errors or 0),
                float(duration or 0),
                str(status or "").strip(),
                history_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def find_sync_history(limit=100):
    """Return newest synchronization runs first."""
    selected_limit = max(1, int(limit))
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT id, source, started_at, finished_at, inserted, updated,
                   skipped, errors, duration, status
            FROM sync_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (selected_limit,),
        ).fetchall()


def add_import_history(imported_at, source_type, filename, result, imported_rows):
    """Persist one completed data import and return its identifier."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO import_history(
                imported_at, source_type, filename, result, imported_rows
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                imported_at,
                str(source_type or "").strip(),
                str(filename or "").strip(),
                str(result or "").strip(),
                int(imported_rows or 0),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def find_import_history(limit=100):
    """Return newest import-history entries first."""
    selected_limit = max(1, int(limit))
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT id, imported_at, source_type, filename, result, imported_rows
            FROM import_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (selected_limit,),
        ).fetchall()


def add_recommendation_history(
    school_code,
    created_at,
    score,
    summary,
    recommended_products,
    next_action,
    risk,
):
    """Persist one generated business-intelligence snapshot."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO recommendation_history(
                school_code, created_at, score, summary, recommended_products,
                next_action, risk
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(school_code or "").strip(),
                created_at,
                int(score or 0),
                str(summary or ""),
                str(recommended_products or ""),
                str(next_action or ""),
                str(risk or ""),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def find_recommendation_history(school_code, limit=20):
    """Return the newest BI snapshots for one school."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT id, school_code, created_at, score, summary,
                   recommended_products, next_action, risk
            FROM recommendation_history
            WHERE school_code = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (str(school_code or "").strip(), max(1, int(limit))),
        ).fetchall()


def add_opportunity_history(school_id, school_name, score, generated_at, result_json):
    """Persist one Opportunity Engine score snapshot."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO opportunity_history(
                school_id, school_name, score, generated_at, result_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(school_id or "").strip(),
                str(school_name or "").strip(),
                int(score or 0),
                str(generated_at or "").strip(),
                str(result_json or ""),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def find_opportunity_history(school_id="", limit=1000):
    """Return newest Opportunity Engine snapshots, optionally for one school."""
    sql = """
        SELECT id, school_id, school_name, score, generated_at, result_json
        FROM opportunity_history
    """
    params = []
    if str(school_id or "").strip():
        sql += " WHERE school_id = ?"
        params.append(str(school_id).strip())
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, int(limit)))
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def find_latest_opportunity_history():
    """Return only the newest persisted Opportunity snapshot per school."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT history.id, history.school_id, history.school_name,
                   history.score, history.generated_at, history.result_json
            FROM opportunity_history AS history
            JOIN (
                SELECT school_id, MAX(id) AS latest_id
                FROM opportunity_history GROUP BY school_id
            ) AS latest ON latest.latest_id = history.id
            ORDER BY history.score DESC, history.school_name, history.school_id
            """
        ).fetchall()


def add_crm_action(action, history_note=""):
    """Insert an action and its immutable creation history atomically."""
    with closing(get_connection()) as conn, conn:
        cursor = conn.execute(
            """
            INSERT INTO crm_actions(
                school_id, action_type, title, status, priority, due_date,
                completed_date, note, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action["school_id"], action["action_type"], action["title"],
                action["status"], action["priority"], action.get("due_date"),
                action.get("completed_date"), action.get("note", ""),
                action["created_at"], action["updated_at"],
            ),
        )
        action_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO crm_action_history(
                action_id, changed_at, event_type, old_status, new_status,
                note, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id, action["created_at"], "Created", None,
                action["status"], history_note or action.get("note", ""),
                action.get("completed_date"),
            ),
        )
        return action_id


def get_crm_action(action_id):
    """Return one CRM action row or ``None``."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT action_id, school_id, action_type, title, status, priority,
                   due_date, completed_date, note, created_at, updated_at
            FROM crm_actions WHERE action_id = ?
            """,
            (int(action_id),),
        ).fetchone()


def transition_crm_action(action_id, status, completed_date, updated_at, note=""):
    """Change status and append history in the same transaction."""
    with closing(get_connection()) as conn, conn:
        current = conn.execute(
            "SELECT status FROM crm_actions WHERE action_id = ?",
            (int(action_id),),
        ).fetchone()
        if current is None:
            return False
        conn.execute(
            """
            UPDATE crm_actions
            SET status = ?, completed_date = ?, updated_at = ?
            WHERE action_id = ?
            """,
            (status, completed_date, updated_at, int(action_id)),
        )
        conn.execute(
            """
            INSERT INTO crm_action_history(
                action_id, changed_at, event_type, old_status, new_status,
                note, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(action_id), updated_at,
                "Completed" if status == "Completed" else "Status Changed",
                current[0], status, note, completed_date,
            ),
        )
        return True


def find_crm_actions(
    status="", priority="", school="", action_type="", due_from="", due_to="",
    exact_school=False,
):
    """Search CRM actions using composable indexed filters."""
    conditions = []
    params = []
    for column, value in (("status", status), ("priority", priority), ("action_type", action_type)):
        selected = str(value or "").strip()
        if selected:
            conditions.append(f"{column} = ?")
            params.append(selected)
    selected_school = str(school or "").strip()
    if selected_school:
        if exact_school:
            conditions.append("school_id = ?")
            params.append(selected_school)
        else:
            conditions.append("school_id LIKE ? ESCAPE '\\'")
            params.append(f"%{_escape_like(selected_school)}%")
    if str(due_from or "").strip():
        conditions.append("due_date >= ?")
        params.append(str(due_from).strip())
    if str(due_to or "").strip():
        conditions.append("due_date <= ?")
        params.append(str(due_to).strip())
    sql = """
        SELECT action_id, school_id, action_type, title, status, priority,
               due_date, completed_date, note, created_at, updated_at
        FROM crm_actions
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END, due_date, updated_at DESC"
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def find_crm_action_history(action_id):
    """Return newest-first audit events for one action."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT id, action_id, changed_at, event_type, old_status,
                   new_status, note, completed_at
            FROM crm_action_history WHERE action_id = ? ORDER BY id DESC
            """,
            (int(action_id),),
        ).fetchall()


def find_recent_crm_action_history(limit=50):
    """Return recent action audit events joined to their action details."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT history.id, history.action_id, history.changed_at,
                   history.event_type, history.old_status, history.new_status,
                   history.note, history.completed_at, actions.school_id,
                   actions.action_type, actions.title, actions.priority,
                   actions.due_date
            FROM crm_action_history AS history
            JOIN crm_actions AS actions ON actions.action_id = history.action_id
            ORDER BY history.id DESC LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()


def add_sales_activity(activity):
    """Insert one validated CRM activity."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO sales_activity(
                school_code, activity_date, activity_type, contact_person,
                memo, next_action_date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity["school_code"],
                activity["activity_date"],
                activity["activity_type"],
                activity.get("contact_person", ""),
                activity.get("memo", ""),
                activity.get("next_action_date"),
                activity["status"],
            ),
        )
        conn.commit()
        return cursor.lastrowid


def update_sales_activity(activity_id, activity):
    """Update one CRM activity."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE sales_activity
            SET school_code = ?, activity_date = ?, activity_type = ?,
                contact_person = ?, memo = ?, next_action_date = ?, status = ?
            WHERE id = ?
            """,
            (
                activity["school_code"],
                activity["activity_date"],
                activity["activity_type"],
                activity.get("contact_person", ""),
                activity.get("memo", ""),
                activity.get("next_action_date"),
                activity["status"],
                activity_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_sales_activity(activity_id):
    """Delete one CRM activity."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "DELETE FROM sales_activity WHERE id = ?", (activity_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def find_sales_activities(school_code="", limit=None):
    """Return CRM activities newest first, optionally for one school."""
    sql = """
        SELECT id, school_code, activity_date, activity_type, contact_person,
               memo, next_action_date, status
        FROM sales_activity
    """
    params = []
    selected_school = str(school_code or "").strip()
    if selected_school:
        sql += " WHERE school_code = ?"
        params.append(selected_school)
    sql += " ORDER BY activity_date DESC, id DESC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(max(1, int(limit)))
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def _add_in_filter(sql_parts, params, column, values):
    placeholders = ", ".join("?" for _ in values)
    sql_parts.append(f"{column} IN ({placeholders})")
    params.extend(values)


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_school(keyword="", region=ALL, school_type=ALL, office=ALL):
    """Search schools using indexed equality filters before name matching."""
    conditions = []
    params = []

    search_keyword = str(keyword or "").strip()
    if search_keyword:
        conditions.append("school_name LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(search_keyword)}%")

    if region != ALL:
        _add_in_filter(conditions, params, "region", region_filter_values(region))

    selected_school_type = str(school_type or "").strip()
    if selected_school_type and selected_school_type != ALL:
        conditions.append("school_type = ?")
        params.append(selected_school_type)

    if office != ALL:
        _add_in_filter(conditions, params, "office", office_filter_values(office))

    sql = """
        SELECT
            school_code, school_name, school_type, office, region, address,
            homepage, ai_school, digital_school, space_innovation, green_smart,
            student_count, class_count
        FROM schools
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY school_name"

    with closing(get_connection()) as conn, conn:
        return conn.execute(sql, params).fetchall()
