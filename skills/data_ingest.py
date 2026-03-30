from __future__ import annotations

import json
import re
from pathlib import Path

from services.db import Database
from services.parser_service import PDFParserService


class DataIngestSkill:
    def __init__(self, db: Database | None = None, parser: PDFParserService | None = None) -> None:
        self.db = db or Database()
        self.parser = parser or PDFParserService()

    def ingest_file(self, file_path: Path) -> str:
        parsed = self.parser.parse_pdf(file_path)
        self.db.execute(
            """
            INSERT OR REPLACE INTO report_meta(doc_id, company_code, company_name, report_type, filename, source_path, total_pages, title)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parsed.doc_id,
                parsed.company_code,
                parsed.company_name,
                parsed.report_type,
                parsed.filename,
                parsed.source_path,
                parsed.total_pages,
                parsed.title,
            ),
        )
        self.db.execute("INSERT OR REPLACE INTO company(company_code, company_name, industry) VALUES(?, ?, ?)", (parsed.company_code, parsed.company_name, "game"))
        self.db.execute("DELETE FROM document_page WHERE doc_id = ?", (parsed.doc_id,))
        self.db.execute("DELETE FROM evidence_chunk WHERE doc_id = ?", (parsed.doc_id,))

        page_rows = []
        chunk_rows = []
        report_year = self._infer_year(parsed.filename) or self._infer_year(parsed.title)
        for page in parsed.pages:
            page_rows.append((parsed.doc_id, page.page_no, page.text))
            if not page.text:
                continue
            for chunk_index, chunk in enumerate(self._chunk_page(page.text), start=1):
                metadata = json.dumps(
                    {
                        "company_code": parsed.company_code,
                        "company_name": parsed.company_name,
                        "report_type": parsed.report_type,
                        "title": parsed.title,
                        "filename": parsed.filename,
                        "year": report_year,
                    },
                    ensure_ascii=False,
                )
                chunk_rows.append(
                    (
                        parsed.doc_id,
                        parsed.company_code,
                        parsed.report_type,
                        page.page_no,
                        chunk["chunk_text"],
                        parsed.filename,
                        chunk_index,
                        chunk["section_title"],
                        chunk["section_path"],
                        metadata,
                        len(chunk["chunk_text"]),
                    )
                )

        self.db.executemany("INSERT INTO document_page(doc_id, page_no, page_text) VALUES(?, ?, ?)", page_rows)
        self.db.executemany(
            """
            INSERT INTO evidence_chunk(
                doc_id,
                company_code,
                report_type,
                page_no,
                chunk_text,
                source,
                chunk_index,
                section_title,
                section_path,
                metadata_json,
                char_count
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            chunk_rows,
        )
        return parsed.doc_id

    @classmethod
    def _chunk_page(cls, text: str, target_size: int = 520) -> list[dict[str, str]]:
        paragraphs = cls._extract_paragraphs(text)
        if not paragraphs:
            normalized = cls._normalize_line(text)
            if not normalized:
                return []
            return [{"chunk_text": normalized, "section_title": "", "section_path": ""}]

        chunks: list[dict[str, str]] = []
        current_lines: list[str] = []
        current_section_title = ""
        current_section_path = ""

        def flush() -> None:
            if not current_lines:
                return
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(
                    {
                        "chunk_text": chunk_text,
                        "section_title": current_section_title,
                        "section_path": current_section_path,
                    }
                )
            current_lines.clear()

        for paragraph in paragraphs:
            prefixed = paragraph["text"]
            section_title = paragraph["section_title"]
            section_path = paragraph["section_path"]
            if section_path and not current_lines:
                prefixed = f"{section_path}\n{prefixed}"

            current_size = sum(len(line) for line in current_lines)
            if current_lines and (
                current_size + len(prefixed) > target_size or section_path != current_section_path
            ):
                flush()

            if len(prefixed) > target_size:
                for piece in cls._split_large_text(prefixed, target_size):
                    chunks.append(
                        {
                            "chunk_text": piece,
                            "section_title": section_title,
                            "section_path": section_path,
                        }
                    )
                current_section_title = ""
                current_section_path = ""
                continue

            if not current_lines:
                current_section_title = section_title
                current_section_path = section_path
            current_lines.append(prefixed)

        flush()
        return chunks

    @classmethod
    def _extract_paragraphs(cls, text: str) -> list[dict[str, str]]:
        lines = [cls._normalize_line(line) for line in text.splitlines()]
        paragraphs: list[dict[str, str]] = []
        current_lines: list[str] = []
        section_stack: list[str] = []

        def flush_paragraph() -> None:
            if not current_lines:
                return
            paragraph_text = " ".join(current_lines).strip()
            if paragraph_text:
                paragraphs.append(
                    {
                        "text": paragraph_text,
                        "section_title": section_stack[-1] if section_stack else "",
                        "section_path": " > ".join(section_stack),
                    }
                )
            current_lines.clear()

        for line in lines:
            if not line:
                flush_paragraph()
                continue
            if cls._looks_like_heading(line):
                flush_paragraph()
                section_stack = cls._update_section_stack(section_stack, line)
                continue
            current_lines.append(line)

        flush_paragraph()
        return paragraphs

    @staticmethod
    def _normalize_line(line: str) -> str:
        return re.sub(r"\s+", " ", (line or "").strip())

    @staticmethod
    def _split_large_text(text: str, target_size: int) -> list[str]:
        sentences = re.split(r"(?<=[。！？；;.!?])", text)
        pieces: list[str] = []
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if current and len(current) + len(sentence) > target_size:
                pieces.append(current)
                current = sentence
            else:
                current = f"{current}{sentence}"
        if current:
            pieces.append(current)
        if pieces:
            return pieces
        normalized = text.strip()
        return [normalized[i:i + target_size] for i in range(0, len(normalized), target_size)]

    @staticmethod
    def _looks_like_heading(line: str) -> bool:
        if len(line) > 36:
            return False
        patterns = (
            r"^第[一二三四五六七八九十\d]+[章节部分]",
            r"^[一二三四五六七八九十]+[、.]",
            r"^\d+(\.\d+){0,2}\s*",
            r"^[（(][一二三四五六七八九十\d]+[）)]",
            r"^[A-Z][\dA-Z.\- ]{0,12}$",
        )
        return any(re.match(pattern, line) for pattern in patterns)

    @staticmethod
    def _update_section_stack(current_stack: list[str], heading: str) -> list[str]:
        level = DataIngestSkill._heading_level(heading)
        next_stack = current_stack[: max(level - 1, 0)]
        next_stack.append(heading)
        return next_stack

    @staticmethod
    def _heading_level(heading: str) -> int:
        if re.match(r"^第[一二三四五六七八九十\d]+[章节部分]", heading) or re.match(r"^[一二三四五六七八九十]+[、.]", heading):
            return 1
        if re.match(r"^\d+\s*[、.]", heading) or re.match(r"^[（(][一二三四五六七八九十\d]+[）)]", heading):
            return 2
        if re.match(r"^\d+\.\d+", heading):
            return 2
        if re.match(r"^\d+\.\d+\.\d+", heading):
            return 3
        return min(len(heading) // 12 + 1, 3)

    @staticmethod
    def _infer_year(value: str) -> int | None:
        match = re.search(r"(20\d{2})", value or "")
        return int(match.group(1)) if match else None
