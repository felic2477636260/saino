from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile

from config.settings import get_settings
from models.schemas import UploadedDocumentItem
from skills.data_ingest import DataIngestSkill


ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf": "PDF",
    ".txt": "TXT",
    ".md": "Markdown",
    ".docx": "DOCX",
}

MATERIAL_DIRECTORY_MAP = {
    "company": "company",
    "research": "research",
    "industry": "industry",
}

REPORT_TYPE_BY_MATERIAL = {
    "company": "annual_report",
    "research": "research_report",
    "industry": "industry_report",
}


class DocumentUploadService:
    def __init__(self, ingestor: DataIngestSkill | None = None) -> None:
        self.settings = get_settings()
        self.ingestor = ingestor or DataIngestSkill()

    @property
    def allowed_file_types(self) -> list[str]:
        return [ALLOWED_UPLOAD_EXTENSIONS[ext] for ext in self.allowed_extensions]

    @property
    def allowed_extensions(self) -> list[str]:
        extensions = [".pdf", ".txt", ".md"]
        try:
            import docx  # noqa: F401

            extensions.append(".docx")
        except ModuleNotFoundError:
            pass
        return extensions

    @property
    def accept_extensions(self) -> list[str]:
        return list(self.allowed_extensions)

    async def save_and_ingest(
        self,
        *,
        files: list[UploadFile],
        company_code: str,
        company_name: str = "",
        material_type: str,
        industry_key: str = "",
    ) -> list[UploadedDocumentItem]:
        normalized_material_type = material_type if material_type in MATERIAL_DIRECTORY_MAP else "company"
        normalized_company_code = company_code.strip()
        if not normalized_company_code:
            raise ValueError("company_code is required")

        target_dir = self._target_directory(material_type=normalized_material_type, company_code=normalized_company_code)
        target_dir.mkdir(parents=True, exist_ok=True)

        uploaded_items: list[UploadedDocumentItem] = []
        for file in files:
            if not file.filename:
                continue
            suffix = Path(file.filename).suffix.lower()
            if suffix not in self.allowed_extensions:
                raise ValueError(f"unsupported file type: {suffix or 'unknown'}")

            safe_name = self._safe_filename(file.filename)
            destination = self._resolve_unique_path(target_dir / safe_name)
            content = await file.read()
            destination.write_bytes(content)

            try:
                doc_id = self.ingestor.ingest_file(
                    destination,
                    company_code=normalized_company_code,
                    company_name=company_name.strip(),
                    report_type=REPORT_TYPE_BY_MATERIAL.get(normalized_material_type, "company_report"),
                    industry=industry_key.strip() or "generic",
                )
            except ModuleNotFoundError as exc:
                destination.unlink(missing_ok=True)
                missing_name = getattr(exc, "name", "") or "dependency"
                if missing_name == "docx":
                    raise ValueError("当前后端环境未启用 DOCX 解析依赖，请先安装依赖后再上传 DOCX，或改用 PDF/TXT/Markdown。") from exc
                raise ValueError(f"缺少解析依赖：{missing_name}") from exc
            except Exception:
                destination.unlink(missing_ok=True)
                raise

            row = self.ingestor.db.fetchone(
                """
                SELECT
                    doc_id,
                    COALESCE(company_code, '') AS company_code,
                    COALESCE(company_name, '') AS company_name,
                    COALESCE(report_type, '') AS report_type,
                    COALESCE(filename, '') AS filename,
                    COALESCE(source_path, '') AS source_path,
                    COALESCE(total_pages, 0) AS total_pages,
                    COALESCE(title, '') AS title,
                    created_at
                FROM report_meta
                WHERE doc_id = ?
                """,
                (doc_id,),
            )
            if row:
                uploaded_items.append(UploadedDocumentItem(**dict(row)))
        return uploaded_items

    def _target_directory(self, *, material_type: str, company_code: str) -> Path:
        folder_name = MATERIAL_DIRECTORY_MAP.get(material_type, "company")
        return self.settings.data_raw_dir / folder_name / company_code

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename).name
        stem = re.sub(r"[^\w\-.()\u4e00-\u9fff]+", "_", Path(name).stem).strip("._") or "upload"
        return f"{stem}{Path(name).suffix.lower()}"

    @staticmethod
    def _resolve_unique_path(base_path: Path) -> Path:
        if not base_path.exists():
            return base_path
        stem = base_path.stem
        suffix = base_path.suffix
        counter = 2
        while True:
            candidate = base_path.with_name(f"{stem}_{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1
