from services.db import Database
from services.retrieval_service import RetrievalService


def test_retrieve_company_filter(temp_db: Database):
    temp_db.executemany(
        "INSERT INTO evidence_chunk(doc_id, company_code, report_type, page_no, chunk_text, source) VALUES(?, ?, ?, ?, ?, ?)",
        [
            ("a", "002555", "annual_report", 1, "新品上线增长", "a.pdf"),
            ("b", "002624", "annual_report", 2, "AI行业趋势", "b.pdf"),
        ],
    )
    service = RetrievalService(db=temp_db)
    rows = service.search("新品", company_code="002555", top_k=5)
    assert len(rows) == 1
    assert rows[0]["company_code"] == "002555"


def test_retrieve_long_query_extracts_terms(temp_db: Database):
    temp_db.executemany(
        "INSERT INTO evidence_chunk(doc_id, company_code, report_type, page_no, chunk_text, source) VALUES(?, ?, ?, ?, ?, ?)",
        [
            ("a", "002555", "annual_report", 1, "新品上线带动增长", "a.pdf"),
            ("b", "002555", "research_report", 2, "AI趋势影响游戏研发", "b.pdf"),
        ],
    )
    service = RetrievalService(db=temp_db)
    rows = service.search("请基于证据生成企业体检报告，覆盖新品进展、经营表现和AI趋势", company_code="002555", top_k=5)
    assert len(rows) >= 1
