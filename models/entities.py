from dataclasses import dataclass, field


@dataclass
class EvidenceChunk:
    doc_id: str
    company_code: str
    report_type: str
    page_no: int
    chunk_text: str
    source: str


@dataclass
class SkillExecution:
    skill_name: str
    skill_type: str
    status: str
    message: str = ""
    output: dict = field(default_factory=dict)
