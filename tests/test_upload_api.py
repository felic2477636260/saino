from pathlib import Path

from fastapi.testclient import TestClient

from api import server
from config.settings import reset_settings_cache
from services.document_upload import DocumentUploadService
from skills.data_ingest import DataIngestSkill


client = TestClient(server.app)


def test_upload_document_and_list(temp_db, work_tmp_dir, monkeypatch):
    raw_dir = work_tmp_dir / "data" / "raw"
    monkeypatch.setenv("DATA_RAW_DIR", str(raw_dir))
    reset_settings_cache()

    original_db = server.db
    original_upload_service = server.document_upload_service
    server.db = temp_db
    server.document_upload_service = DocumentUploadService(ingestor=DataIngestSkill(db=temp_db))

    try:
        response = client.post(
            "/documents/upload",
            data={
                "company_code": "002555",
                "company_name": "三七互娱",
                "material_type": "research",
                "industry_key": "game",
            },
            files={"files": ("新品跟踪.txt", "这是一个用于测试上传的数据文件。".encode("utf-8"), "text/plain")},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["uploaded_count"] == 1
        assert body["company_code"] == "002555"
        assert body["documents"][0]["report_type"] == "research_report"

        saved_path = Path(body["documents"][0]["source_path"])
        assert saved_path.exists()
        assert raw_dir in saved_path.parents

        list_response = client.get("/documents?company_code=002555")
        assert list_response.status_code == 200
        assert any(item["filename"].endswith(".txt") for item in list_response.json()["data"])
    finally:
        server.db = original_db
        server.document_upload_service = original_upload_service
        reset_settings_cache()
