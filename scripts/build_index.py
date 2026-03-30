import json
from pathlib import Path

from config.settings import get_settings
from services.db import Database


def main() -> None:
    db = Database()
    rows = db.fetchall("SELECT id, doc_id, company_code, page_no, source FROM evidence_chunk ORDER BY id LIMIT 1000")
    output_dir = Path(get_settings().data_raw_dir).parent / "index"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "keyword_index_preview.json"
    output_path.write_text(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved preview index to {output_path}")


if __name__ == "__main__":
    main()
