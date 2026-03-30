import logging
from pathlib import Path

from config.settings import get_settings
from services.db import Database
from skills.data_ingest import DataIngestSkill


logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)


def discover_pdfs() -> list[Path]:
    settings = get_settings()
    raw_dir = settings.data_raw_dir
    pdfs = [path.resolve() for path in list(raw_dir.rglob("*.pdf")) + list(raw_dir.rglob("*.PDF"))]
    root_pdfs = [path.resolve() for path in list(Path.cwd().glob("*.pdf")) + list(Path.cwd().glob("*.PDF"))]

    preferred_names = {path.name.lower() for path in pdfs}
    filtered_root = [path for path in root_pdfs if path.name.lower() not in preferred_names]

    seen: set[Path] = set()
    results: list[Path] = []
    for path in pdfs + filtered_root:
        if path not in seen:
            seen.add(path)
            results.append(path)
    return results


def cleanup_missing_sources(db: Database) -> None:
    rows = db.fetchall("SELECT doc_id, source_path FROM report_meta")
    removed = 0
    for row in rows:
        source_path = row["source_path"]
        if source_path and not Path(source_path).exists():
            doc_id = row["doc_id"]
            db.execute("DELETE FROM evidence_chunk WHERE doc_id = ?", (doc_id,))
            db.execute("DELETE FROM document_page WHERE doc_id = ?", (doc_id,))
            db.execute("DELETE FROM report_meta WHERE doc_id = ?", (doc_id,))
            removed += 1
    if removed:
        logger.info("removed %s orphaned document records", removed)


def main() -> None:
    ingestor = DataIngestSkill()
    cleanup_missing_sources(ingestor.db)
    files = discover_pdfs()
    logger.info("discovered %s pdf files", len(files))
    for file_path in files:
        try:
            doc_id = ingestor.ingest_file(file_path)
            logger.info("ingested %s -> %s", file_path.name, doc_id)
        except Exception as exc:
            logger.exception("failed to ingest %s: %s", file_path, exc)


if __name__ == "__main__":
    main()
