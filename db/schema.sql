CREATE TABLE IF NOT EXISTS company (
    company_code TEXT PRIMARY KEY,
    company_name TEXT,
    industry TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_meta (
    doc_id TEXT PRIMARY KEY,
    company_code TEXT,
    company_name TEXT,
    report_type TEXT,
    filename TEXT,
    source_path TEXT,
    total_pages INTEGER,
    title TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_page (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT,
    page_no INTEGER,
    page_text TEXT
);

CREATE TABLE IF NOT EXISTS evidence_chunk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT,
    company_code TEXT,
    report_type TEXT,
    page_no INTEGER,
    chunk_text TEXT,
    source TEXT,
    chunk_index INTEGER DEFAULT 0,
    section_title TEXT DEFAULT '',
    section_path TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    char_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analysis_task (
    task_id TEXT PRIMARY KEY,
    company_code TEXT,
    query TEXT,
    task_type TEXT,
    status TEXT,
    result_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    risk_level TEXT,
    risk_score INTEGER,
    matched_signals TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_eval_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    metric_name TEXT,
    metric_value TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS baseline_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_code TEXT,
    query TEXT,
    output_path TEXT,
    result_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skill_execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    skill_name TEXT,
    skill_type TEXT,
    status TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_company ON evidence_chunk(company_code);
CREATE INDEX IF NOT EXISTS idx_evidence_doc_page ON evidence_chunk(doc_id, page_no);
