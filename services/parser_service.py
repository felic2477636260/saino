import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import fitz


logger = logging.getLogger(__name__)


@dataclass
class ParsedPage:
    page_no: int
    text: str


@dataclass
class ParsedDocument:
    doc_id: str
    company_code: str
    company_name: str
    report_type: str
    filename: str
    source_path: str
    total_pages: int
    title: str
    pages: list[ParsedPage]


class PDFParserService:
    COMPANY_MAP = {
        "吉比特": "603444",
        "三七互娱": "002555",
        "完美世界": "002624",
    }

    def parse_pdf(self, file_path: Path) -> ParsedDocument:
        doc_id = hashlib.md5(str(file_path).encode("utf-8")).hexdigest()
        company_code, company_name = self._infer_company(file_path)
        report_type = self._infer_report_type(file_path)
        pages: list[ParsedPage] = []
        title = file_path.stem

        pdf = fitz.open(file_path)
        try:
            for index, page in enumerate(pdf, start=1):
                try:
                    text = page.get_text("text").strip()
                except Exception as exc:
                    logger.exception("failed to extract page %s of %s: %s", index, file_path, exc)
                    text = ""
                pages.append(ParsedPage(page_no=index, text=text))
            metadata_title = (pdf.metadata or {}).get("title") or ""
            if metadata_title.strip():
                title = metadata_title.strip()
        finally:
            pdf.close()

        return ParsedDocument(
            doc_id=doc_id,
            company_code=company_code,
            company_name=company_name,
            report_type=report_type,
            filename=file_path.name,
            source_path=str(file_path),
            total_pages=len(pages),
            title=title,
            pages=pages,
        )

    def _infer_company(self, file_path: Path) -> tuple[str, str]:
        path_text = str(file_path)
        for name, code in self.COMPANY_MAP.items():
            if name in path_text:
                return code, name
        match = re.search(r"company[\\/](\w+)", path_text, re.IGNORECASE)
        if match:
            code = match.group(1)
            return code, code
        return "macro", "行业材料"

    def _infer_report_type(self, file_path: Path) -> str:
        name = file_path.name.lower()
        if "年报" in file_path.name or "annual" in name:
            return "annual_report"
        if "季度" in file_path.name or "research" in name:
            return "research_report"
        return "industry_report"
