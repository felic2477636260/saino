from fastapi.testclient import TestClient

from api.server import app


client = TestClient(app)


def test_report_pdf_endpoint(real_llm_required):
    analyze = client.post("/analyze", json={"company_code": "002555", "query": "请生成企业体检报告", "top_k": 2})
    assert analyze.status_code == 200
    task_id = analyze.json()["data"]["task_id"]
    response = client.get(f"/reports/{task_id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_report_markdown_and_html_endpoints(real_llm_required):
    analyze = client.post("/analyze", json={"company_code": "002555", "query": "请生成企业体检报告", "top_k": 2})
    assert analyze.status_code == 200
    task_id = analyze.json()["data"]["task_id"]

    markdown_response = client.get(f"/reports/{task_id}/markdown")
    assert markdown_response.status_code == 200
    assert "## 执行摘要" in markdown_response.text
    assert "## 综合判断" in markdown_response.text
    assert "## 风险与机会" in markdown_response.text
    assert "## 建议动作" in markdown_response.text
    assert "已激活通用 Skill" not in markdown_response.text
    assert "证据条数" not in markdown_response.text

    html_response = client.get(f"/reports/{task_id}/html")
    assert html_response.status_code == 200
    assert "<html" in html_response.text.lower()
    assert "执行摘要" in html_response.text
    assert "综合判断" in html_response.text
    assert "风险与机会" in html_response.text
    assert "已激活通用 Skill" not in html_response.text
