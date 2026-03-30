import json

from fastapi.testclient import TestClient

from api import server


client = TestClient(server.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "ok"
    assert body["llm_mode"] == "real"
    assert "model_name" in body


def test_prompt_templates():
    response = client.get("/prompt-templates")
    assert response.status_code == 200
    items = response.json()["data"]
    assert any(item["template_id"] == "game" and item["module_group"] == "featured" for item in items)
    assert any(item["template_id"] == "custom" and item["is_custom"] is True for item in items)


def test_analyze_basic(real_llm_required):
    response = client.post("/analyze", json={"company_code": "002555", "query": "新品进展"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["company_code"] == "002555"
    assert "risk_level" in body
    assert "report_payload" in body


def test_report_detail_and_recent(real_llm_required):
    analyze_response = client.post("/analyze", json={"company_code": "002555", "query": "新品进展"})
    assert analyze_response.status_code == 200
    task_id = analyze_response.json()["data"]["task_id"]

    detail_response = client.get(f"/reports/{task_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["task_id"] == task_id
    assert detail["status"] == "completed"
    assert "created_at" in detail

    recent_response = client.get("/reports/recent")
    assert recent_response.status_code == 200
    recent_items = recent_response.json()["data"]
    assert any(item["task_id"] == task_id for item in recent_items)


def test_clear_recent_reports(real_llm_required):
    analyze_response = client.post("/analyze", json={"company_code": "002555", "query": "新品进展"})
    assert analyze_response.status_code == 200
    task_id = analyze_response.json()["data"]["task_id"]

    delete_response = client.delete("/reports/recent")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] >= 1

    recent_response = client.get("/reports/recent")
    assert recent_response.status_code == 200
    assert all(item["task_id"] != task_id for item in recent_response.json()["data"])

    detail_response = client.get(f"/reports/{task_id}")
    assert detail_response.status_code == 404


def test_clear_system_cache_endpoint(temp_db):
    temp_db.execute(
        "INSERT INTO analysis_task(task_id, company_code, query, task_type, status, result_json) VALUES(?, ?, ?, ?, ?, ?)",
        ("task-1", "002555", "新品进展", "analyze", "completed", "{}"),
    )
    temp_db.execute(
        "INSERT INTO risk_result(task_id, risk_level, risk_score, matched_signals) VALUES(?, ?, ?, ?)",
        ("task-1", "中", 55, "signal-a"),
    )
    temp_db.execute(
        "INSERT INTO skill_execution_log(task_id, skill_name, skill_type, status, message) VALUES(?, ?, ?, ?, ?)",
        ("task-1", "RetrieveSkill", "generic", "success", "ok"),
    )
    temp_db.execute(
        "INSERT INTO report_meta(doc_id, company_code, company_name, report_type, filename, source_path, total_pages, title) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        ("doc-1", "002555", "测试公司", "annual_report", "demo.pdf", "data/raw/demo.pdf", 2, "demo"),
    )
    temp_db.execute("INSERT INTO document_page(doc_id, page_no, page_text) VALUES(?, ?, ?)", ("doc-1", 1, "page"))
    temp_db.execute(
        "INSERT INTO evidence_chunk(doc_id, company_code, report_type, page_no, chunk_text, source) VALUES(?, ?, ?, ?, ?, ?)",
        ("doc-1", "002555", "annual_report", 1, "chunk", "demo.pdf"),
    )
    temp_db.execute("INSERT INTO company(company_code, company_name, industry) VALUES(?, ?, ?)", ("002555", "测试公司", "game"))

    original_db = server.db
    server.db = temp_db
    try:
        response = client.delete("/system/cache")
    finally:
        server.db = original_db

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["cleared"]["analysis_tasks"] == 1
    assert body["cleared"]["parsed_documents"] == 1
    assert body["cleared"]["evidence_chunks"] == 1
    assert body["preserved"]["api_configuration"] is True


def test_report_detail_accepts_legacy_chunk_text_evidence(temp_db):
    legacy_report = {
        "task_id": "task-legacy",
        "company_code": "002555",
        "query": "请生成企业体检报告",
        "report_title": "企业体检报告",
        "summary": "整体判断：公司当前处于修复与压力并存状态。",
        "total_score": 52,
        "risk_score": 52,
        "risk_level": "中风险",
        "findings": ["公司当前处于修复与压力并存状态。"],
        "evidence": [
            {
                "source": "年报",
                "page_no": 12,
                "chunk_text": "收入同比增长12%，但费用率仍然承压。",
                "section_title": "经营情况",
                "section_path": "经营情况/主营业务",
                "relevance_score": 26,
                "reason": "量化数据优先",
                "quote": "收入同比增长12%，但费用率仍然承压。",
                "evidence_type": "quantitative",
                "priority_level": 4,
            }
        ],
        "recommendations": ["继续跟踪：费用率变化与现金流兑现。"],
        "activated_skills": {"generic": ["RetrieveSkill"], "custom": []},
        "custom_skill_outputs": {},
        "report_sections": {"conclusion": "整体判断：公司当前处于修复与压力并存状态。"},
        "analysis_plan": [],
        "verification_notes": [],
        "skill_runs": [],
        "report_payload": {
            "cover": {
                "title": "企业体检报告",
                "company_code": "002555",
                "query": "请生成企业体检报告",
            },
            "report_layer": {
                "executive_summary": "整体判断：公司当前处于修复与压力并存状态。",
                "score_breakdown": {
                    "total_score": 52,
                    "risk_level": "中风险",
                    "overall_state": "修复与压力并存",
                    "top_deductions": ["盈利质量是当前主要扣分来源。"],
                    "score_note": "本次评分基于当前已披露材料。",
                    "dimensions": [],
                },
                "key_judgments": [],
                "risk_opportunities": {"risks": [], "opportunities": []},
                "deep_sections": [
                    {
                        "key": "risk_diagnosis",
                        "title": "核心风险诊断",
                        "summary": "每条风险只绑定 1-2 条最强证据。",
                        "body": ["判断标题：盈利质量 / 利润兑现。"],
                        "evidence": [
                            {
                                "source": "年报",
                                "page_no": 12,
                                "chunk_text": "收入同比增长12%，但费用率仍然承压。",
                                "section_title": "经营情况",
                                "section_path": "经营情况/主营业务",
                                "relevance_score": 26,
                                "reason": "量化数据优先",
                                "quote": "收入同比增长12%，但费用率仍然承压。",
                                "evidence_type": "quantitative",
                                "priority_level": 4,
                            }
                        ],
                        "pending_checks": [],
                    }
                ],
                "next_steps": ["继续跟踪：费用率变化与现金流兑现。"],
            },
            "evidence_layer": {
                "key_evidence": [],
                "verification_focus": [],
                "evidence_index": [
                    {
                        "source": "年报",
                        "page_no": 12,
                        "chunk_text": "收入同比增长12%，但费用率仍然承压。",
                        "section_title": "经营情况",
                        "section_path": "经营情况/主营业务",
                        "relevance_score": 26,
                        "reason": "量化数据优先",
                        "quote": "收入同比增长12%，但费用率仍然承压。",
                        "evidence_type": "quantitative",
                        "priority_level": 4,
                    }
                ],
            },
            "machine_layer": {
                "analysis_plan": [],
                "skill_runs": [],
                "activated_skills": {"generic": ["RetrieveSkill"], "custom": []},
                "diagnostics": [],
            },
            "sections": [
                {
                    "key": "risk_diagnosis",
                    "title": "核心风险诊断",
                    "summary": "每条风险只绑定 1-2 条最强证据。",
                    "body": ["判断标题：盈利质量 / 利润兑现。"],
                    "evidence": [
                        {
                            "source": "年报",
                            "page_no": 12,
                            "chunk_text": "收入同比增长12%，但费用率仍然承压。",
                            "section_title": "经营情况",
                            "section_path": "经营情况/主营业务",
                            "relevance_score": 26,
                            "reason": "量化数据优先",
                            "quote": "收入同比增长12%，但费用率仍然承压。",
                            "evidence_type": "quantitative",
                            "priority_level": 4,
                        }
                    ],
                    "pending_checks": [],
                }
            ],
            "appendix": {
                "analysis_plan": [],
                "verification_notes": [],
                "evidence_index": [
                    {
                        "source": "年报",
                        "page_no": 12,
                        "chunk_text": "收入同比增长12%，但费用率仍然承压。",
                        "section_title": "经营情况",
                        "section_path": "经营情况/主营业务",
                        "relevance_score": 26,
                        "reason": "量化数据优先",
                        "quote": "收入同比增长12%，但费用率仍然承压。",
                        "evidence_type": "quantitative",
                        "priority_level": 4,
                    }
                ],
                "skill_runs": [],
            },
            "summary_cards": [{"label": "总分", "value": "52"}],
        },
        "available_exports": ["json", "markdown", "html", "pdf"],
    }

    temp_db.execute(
        "INSERT INTO analysis_task(task_id, company_code, query, task_type, status, result_json) VALUES(?, ?, ?, ?, ?, ?)",
        ("task-legacy", "002555", "请生成企业体检报告", "analyze", "completed", json.dumps(legacy_report, ensure_ascii=False)),
    )

    original_db = server.db
    server.db = temp_db
    try:
        response = client.get("/reports/task-legacy")
    finally:
        server.db = original_db

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["evidence"][0]["text"] == "收入同比增长12%，但费用率仍然承压。"
    assert payload["report_payload"]["sections"][0]["evidence"][0]["text"] == "收入同比增长12%，但费用率仍然承压。"
