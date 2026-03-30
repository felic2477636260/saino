import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response

from agent.core import SainoAgent
from config.settings import get_settings
from models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ApiEnvelope,
    AskRequest,
    AskResponse,
    PromptTemplate,
    ReportDetailResponse,
    ReportHistoryItem,
    SkillInfo,
    UploadCapabilityResponse,
    UploadDocumentResponse,
    UploadedDocumentItem,
)
from services.db import Database
from services.document_upload import DocumentUploadService
from services.prompt_templates import list_prompt_templates
from services.report_export import ReportExportService
from services.report_pdf import ReportPDFService
from skills.registry import build_default_registry


settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=f"{settings.app_name} API")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = SainoAgent()
registry = build_default_registry()
db = Database()
pdf_service = ReportPDFService()
export_service = ReportExportService()
document_upload_service = DocumentUploadService()
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.get("/health", response_model=ApiEnvelope)
def health() -> ApiEnvelope:
    return ApiEnvelope(
        data={
            "status": "ok",
            "llm_mode": "real",
            "llm_ready": agent.llm_client.is_ready,
            "ark_base_url": agent.llm_client.settings.ark_base_url,
            "model_name": agent.llm_client.settings.model_name,
            "ark_timeout_seconds": agent.llm_client.settings.ark_timeout_seconds,
            "has_api_key": bool(agent.llm_client.settings.ark_api_key),
            "last_llm_error": agent.llm_client.last_error,
        }
    )


@app.post("/analyze", response_model=ApiEnvelope)
def analyze(request: AnalyzeRequest) -> ApiEnvelope:
    company_code = request.company_code or request.company_name or "macro"
    try:
        result = agent.analyze(
            company_code=company_code,
            query=request.query,
            top_k=request.top_k,
            preference_note=request.preference_note,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ApiEnvelope(data=AnalyzeResponse(**result))


@app.post("/ask", response_model=ApiEnvelope)
def ask(request: AskRequest) -> ApiEnvelope:
    try:
        result = agent.ask(company_code=request.company_code, task_id=request.task_id, question=request.question, top_k=request.top_k)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ApiEnvelope(data=AskResponse(**result))


@app.get("/skills", response_model=ApiEnvelope)
def skills() -> ApiEnvelope:
    items = [
        SkillInfo(
            skill_id=item["skill_id"],
            name=item["name"],
            skill_type=item["skill_type"],
            description=item["description"],
            skill_layer=item.get("skill_layer"),
            skill_category=item.get("skill_category"),
            goal=item.get("goal"),
            version=item.get("version"),
            trigger_condition=item.get("trigger_condition"),
            applicable_when=item.get("applicable_when", []),
            not_applicable_when=item.get("not_applicable_when", []),
            required_inputs=item.get("required_inputs", []),
            optional_inputs=item.get("optional_inputs", []),
            dependencies=item.get("dependencies", []),
            output_schema=item.get("output_schema", {}),
            evidence_requirements=item.get("evidence_requirements"),
            evaluation_criteria=item.get("evaluation_criteria", []),
            failure_handling=item.get("failure_handling"),
            priority=item.get("priority"),
            tags=item.get("tags", []),
            expert_role=item.get("expert_role"),
            domain_focus=item.get("domain_focus"),
            core_questions=item.get("core_questions", []),
            preferred_terms=item.get("preferred_terms", []),
            translation_rule=item.get("translation_rule"),
            reasoning_style=item.get("reasoning_style"),
        )
        for item in registry.describe()
    ]
    return ApiEnvelope(data=items)


@app.get("/prompt-templates", response_model=ApiEnvelope)
def prompt_templates() -> ApiEnvelope:
    items = [PromptTemplate(**item.model_dump()) for item in list_prompt_templates()]
    return ApiEnvelope(data=items)


@app.get("/documents", response_model=ApiEnvelope)
def list_documents(company_code: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=100)) -> ApiEnvelope:
    items = [UploadedDocumentItem(**item) for item in db.list_documents(company_code=company_code, limit=limit)]
    return ApiEnvelope(data=items)


@app.get("/documents/capabilities", response_model=ApiEnvelope)
def document_capabilities() -> ApiEnvelope:
    return ApiEnvelope(
        data=UploadCapabilityResponse(
            allowed_file_types=document_upload_service.allowed_file_types,
            accept_extensions=document_upload_service.accept_extensions,
        )
    )


@app.post("/documents/upload", response_model=ApiEnvelope)
async def upload_documents(
    files: list[UploadFile] = File(...),
    company_code: str = Form(...),
    company_name: str = Form(default=""),
    material_type: str = Form(default="company"),
    industry_key: str = Form(default="generic"),
) -> ApiEnvelope:
    try:
        items = await document_upload_service.save_and_ingest(
            files=files,
            company_code=company_code,
            company_name=company_name,
            material_type=material_type,
            industry_key=industry_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("document upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="上传后处理失败，请查看后端日志或稍后重试。") from exc

    return ApiEnvelope(
        data=UploadDocumentResponse(
            uploaded_count=len(items),
            company_code=company_code.strip(),
            material_type=material_type,
            allowed_file_types=document_upload_service.allowed_file_types,
            documents=items,
        )
    )


@app.get("/reports/recent", response_model=ApiEnvelope)
def recent_reports(limit: int = Query(default=6, ge=1, le=20)) -> ApiEnvelope:
    items = [ReportHistoryItem(**item) for item in db.list_recent_tasks(limit=limit)]
    return ApiEnvelope(data=items)


@app.delete("/reports/recent", response_model=ApiEnvelope)
def clear_recent_reports() -> ApiEnvelope:
    deleted = db.clear_analysis_history()
    return ApiEnvelope(data={"deleted": deleted})


@app.delete("/system/cache", response_model=ApiEnvelope)
def clear_system_cache() -> ApiEnvelope:
    cleared = db.clear_system_cache()
    return ApiEnvelope(
        data={
            "cleared": cleared,
            "preserved": {
                "raw_source_files": True,
                "api_configuration": True,
            },
        }
    )


@app.get("/reports/{task_id}", response_model=ApiEnvelope)
def report_detail(task_id: str) -> ApiEnvelope:
    task = db.get_task(task_id)
    if not task or task.get("task_type") != "analyze":
        raise HTTPException(status_code=404, detail="report task not found")
    result = task.get("result") or None
    if not result:
        raise HTTPException(status_code=404, detail="report result not found")
    return ApiEnvelope(data=ReportDetailResponse(status=task["status"], created_at=task["created_at"], **result))


@app.get("/reports/{task_id}/pdf")
def report_pdf(task_id: str) -> Response:
    result = db.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="report task not found")
    pdf_bytes = pdf_service.build_pdf(result)
    filename = f"{result.get('company_code', 'report')}_{task_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/reports/{task_id}/markdown")
def report_markdown(task_id: str) -> PlainTextResponse:
    result = db.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="report task not found")
    markdown = export_service.build_markdown(result)
    filename = f"{result.get('company_code', 'report')}_{task_id}.md"
    return PlainTextResponse(
        content=markdown,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/reports/{task_id}/html")
def report_html(task_id: str) -> HTMLResponse:
    result = db.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="report task not found")
    html = export_service.build_html(result)
    return HTMLResponse(content=html)


if frontend_dist.exists():

    @app.get("/", include_in_schema=False)
    def frontend_index() -> FileResponse:
        return FileResponse(frontend_dist / "index.html")


    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_assets(full_path: str) -> FileResponse:
        candidate = frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
