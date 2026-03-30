import fitz

from skills.data_ingest import DataIngestSkill


def test_ingest_scans_and_writes(temp_db, work_tmp_dir):
    pdf_path = work_tmp_dir / "demo.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "新品上线，业绩改善")
    doc.save(pdf_path)
    doc.close()

    ingestor = DataIngestSkill(db=temp_db)
    ingestor.ingest_file(pdf_path)
    row = temp_db.fetchone("SELECT filename FROM report_meta WHERE filename = ?", (pdf_path.name,))
    assert row is not None
