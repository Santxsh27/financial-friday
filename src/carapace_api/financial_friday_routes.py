"""Financial Friday demo API: bounded AI planning and artificial-money execution."""
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from carapace_ai.financial_friday import LocalFinancialFridayPlanner
from carapace_core.friday_live import FridayMandate, IncomingFinancialSignal, TestProviderBill
from carapace_integrations.financial_friday_fixtures import CASES
from .auth import TenantContext
from .friday_inbox import FridayInbox
from .financial_friday import FridayUnderstandingUnavailable
from carapace_ai.friday_chat import FridayChatRequest
from carapace_ai.friday_tasks import TaskRequest
from .friday_tasks import FridayTaskService, TaskConfirmation
from carapace_core.friday_cashflow import CashflowRequest


class WatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class StatementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    csv_text: str = Field(min_length=1, max_length=1024 * 1024)


class ReviewStatementRequest(StatementRequest):
    confirm_store_claims: bool = Field(default=False, strict=True)


class FollowThroughRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bill_reference: str = Field(min_length=1, max_length=120)


class FridayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planner: Literal["configured", "local"] = "configured"


class BillHandleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bill_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{3,79}$")
    expected_bill_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirm_sandbox_execution: bool = Field(strict=True)


DOCUMENT_TYPES = {"image/png", "image/jpeg", "image/webp", "application/pdf"}
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024


def _valid_document_signature(mime_type: str, data: bytes) -> bool:
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    return False


async def _read_bounded_document(request: Request) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_DOCUMENT_BYTES:
            raise HTTPException(413, "document exceeds the 8 MB limit")
        chunks.append(chunk)
    if not chunks:
        raise HTTPException(422, "document is empty")
    return b"".join(chunks)


def register_financial_friday_routes(application, service, authenticate):
    from .friday_review import FridayReviewService
    review = FridayReviewService(service)
    application.state.friday_reviews = review
    tasks = FridayTaskService(service, review)
    application.state.friday_tasks = tasks
    from .friday_buddy import FridayBuddy, BuddyPreferences
    buddy = FridayBuddy(service)
    application.state.friday_buddy = buddy
    from .friday_followups import FridayFollowups, FollowupRequest
    service.followups = FridayFollowups(service)
    from .friday_cashflow import FridayCashflow
    service.cashflow = FridayCashflow(service)
    from .friday_diary import FridayDiary
    from carapace_core.friday_diary import DiaryChange
    from carapace_ai.friday_diary import DiaryParseRequest, parse_diary, diagnose_diary_error
    service.diary = FridayDiary(service)
    from .friday_portfolio import FridayPortfolio
    from carapace_core.friday_portfolio import SaveStatement, StatementVisibility, summarize_statements
    service.portfolio = FridayPortfolio(service)

    class PrepareStatement(BaseModel):
        model_config = ConfigDict(extra='forbid')
        data_base64: str = Field(min_length=4, max_length=5_592_408)
        mime: Literal['text/csv','application/pdf']
        account_alias: str = Field(min_length=1,max_length=40,pattern=r'^[A-Za-z][A-Za-z0-9 _-]*$')
        account_type: Literal['BANK','CREDIT_CARD']
        confirm_cloud_processing: bool = Field(strict=True)

    @application.get('/v1/friday/statements',tags=['friday-statements'])
    def statement_portfolio(tenant: TenantContext = Depends(authenticate)):
        return service.portfolio.view(tenant.tenant_id)

    @application.post('/v1/friday/statements',tags=['friday-statements'])
    def statement_save(payload: SaveStatement, tenant: TenantContext = Depends(authenticate)):
        try:return service.portfolio.save(tenant.tenant_id,payload)
        except ValueError as error:raise HTTPException(409,str(error)) from error

    @application.post('/v1/friday/statements/visibility',tags=['friday-statements'])
    def statement_visibility(payload: StatementVisibility,tenant: TenantContext=Depends(authenticate)):
        try:return service.portfolio.set_visibility(tenant.tenant_id,payload)
        except ValueError as error:raise HTTPException(409,str(error)) from error

    @application.post('/v1/friday/statements/prepare',tags=['friday-statements'])
    async def statement_prepare(payload: PrepareStatement,tenant: TenantContext = Depends(authenticate)):
        import base64
        import binascii
        from carapace_ai.friday_statements import extract_statement
        from carapace_ai.friday_document_grounding import configured_grounder
        from .friday_resource_limits import reserve_resource
        from .friday_privacy import privacy_generation
        if not payload.confirm_cloud_processing:
            raise HTTPException(422,'Confirm temporary server processing; PDFs also use Google AI')
        try:
            data=base64.b64decode(payload.data_base64,validate=True)
            if not 0<len(data)<=4*1024*1024:raise ValueError('Choose a file of at most 4 MB')
            generation=str(privacy_generation(service,tenant.tenant_id))
            statement,provenance=await run_in_threadpool(extract_statement,service.planner,data=data,mime=payload.mime,
                account_alias=payload.account_alias,account_type=payload.account_type,use_ai=True,
                grounder=configured_grounder() if payload.mime=='application/pdf' else None,
                reserve=lambda pages:reserve_resource(service,'ocr_pages',pages))
            return {'statement':statement.model_dump(mode='json'),'summary':summarize_statements([statement.model_dump(mode='json')]),
                'workspace_generation':generation,'provenance':provenance,'saved':False,'raw_file_stored':False,'money_moved':False,
                'review_required':True,'warning':'Check the row count, amounts and labels against the original before saving. Extraction may omit or misread rows.'}
        except (ValueError,UnicodeError,binascii.Error) as error:raise HTTPException(422,str(error)) from error
        except Exception as error:
            from carapace_ai.friday_observability import LOG
            LOG.warning('statement_prepare_failed type=%s',type(error).__name__)
            raise HTTPException(503,'Statement reading unavailable. Nothing was saved. Try a clearer PDF or INR CSV export.') from error

    @application.get('/v1/friday/diary', tags=['friday-diary'])
    def diary_read(tenant: TenantContext = Depends(authenticate)):
        return service.diary.view(tenant.tenant_id)

    @application.post('/v1/friday/diary', tags=['friday-diary'])
    def diary_change(payload: DiaryChange, tenant: TenantContext = Depends(authenticate)):
        try: return service.diary.change(tenant.tenant_id, payload)
        except ValueError as error: raise HTTPException(409, str(error)) from error

    @application.post('/v1/friday/diary/prepare', tags=['friday-diary'])
    async def diary_prepare(payload: DiaryParseRequest, tenant: TenantContext = Depends(authenticate)):
        if not payload.confirm_cloud_processing:
            raise HTTPException(422, 'Permission to send this check-in to Gemini is required')
        try: return await run_in_threadpool(parse_diary, service.planner, payload)
        except Exception as error:
            diagnose_diary_error(error)
            raise HTTPException(503, 'Friday could not reliably read that update. Use manual entry; nothing was saved.') from error

    @application.get('/v1/friday/cashflow', tags=['friday-cashflow'])
    def cashflow_read(tenant: TenantContext = Depends(authenticate)):
        return {'snapshot': service.cashflow.get(tenant.tenant_id), 'money_moved': False, 'ai_called': False}

    @application.post('/v1/friday/cashflow', tags=['friday-cashflow'])
    def cashflow_create(payload: CashflowRequest, tenant: TenantContext = Depends(authenticate)):
        try: return service.cashflow.create(tenant.tenant_id, payload)
        except ValueError as error: raise HTTPException(409, str(error)) from error

    @application.post('/v1/friday/obligations/{obligation_id}/followup', tags=['financial-obligations'])
    def obligation_followup(obligation_id: str, payload: FollowupRequest, tenant: TenantContext = Depends(authenticate)):
        try: return service.followups.update(tenant.tenant_id, review, obligation_id, payload)
        except KeyError as error: raise HTTPException(404, 'Saved obligation not found in this workspace') from error
        except ValueError as error: raise HTTPException(409, str(error)) from error

    @application.get('/v1/friday/buddy', tags=['friday-buddy'])
    def buddy_overview(tenant: TenantContext = Depends(authenticate)):
        try: return buddy.snapshot(tenant.tenant_id, review)
        except ValueError as error: raise HTTPException(409, str(error)) from error

    @application.get('/v1/friday/buddy/preferences', tags=['friday-buddy'])
    def buddy_preferences(tenant: TenantContext = Depends(authenticate)):
        return {'preferences': buddy.preferences(tenant.tenant_id), 'scope':'COMMUNICATION_ONLY'}

    @application.put('/v1/friday/buddy/preferences', tags=['friday-buddy'])
    def buddy_save(payload: BuddyPreferences, tenant: TenantContext = Depends(authenticate)):
        return buddy.save(tenant.tenant_id, payload)
    @application.post('/internal/friday/recover', include_in_schema=False)
    async def recover_task(request: Request):
        from .friday_recovery import verify_task_identity, recover_journal
        if not tasks.recovery.enabled:raise HTTPException(404,'Recovery worker is disabled')
        try:
            await run_in_threadpool(verify_task_identity,request.headers.get('Authorization'),tasks.recovery)
        except Exception as error:raise HTTPException(403,'Recovery worker authentication failed') from error
        import json
        body=bytearray()
        async for chunk in request.stream():
            if len(body)+len(chunk)>8192:raise HTTPException(413,'Recovery envelope too large')
            body.extend(chunk)
        try:return await run_in_threadpool(recover_journal,tasks,json.loads(body))
        except (ValueError,TypeError,KeyError) as error:raise HTTPException(409,'Recovery evidence rejected; no payment retry performed') from error
    @application.get('/v1/friday/obligations', tags=['financial-obligations'])
    def obligation_inbox(tenant: TenantContext = Depends(authenticate)):
        from .friday_obligations import financial_obligations
        try:
            return financial_obligations(service, review, tenant.tenant_id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    @application.get('/v1/friday/obligations/{obligation_id}/result', tags=['financial-obligations'])
    def obligation_result(obligation_id: str, tenant: TenantContext = Depends(authenticate)):
        from .friday_obligations import recorded_obligation_result
        try:
            return recorded_obligation_result(service, review, tenant.tenant_id, obligation_id)
        except KeyError as error:
            raise HTTPException(404, 'Obligation not found in this workspace') from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    from .friday_privacy import FridayPrivacyService, PrivacyPolicy, DeleteReviews
    privacy=FridayPrivacyService(service)
    application.state.friday_privacy=privacy

    @application.get('/v1/friday/privacy',tags=['friday-privacy'])
    def privacy_read(tenant:TenantContext=Depends(authenticate)):
        return privacy.policy(tenant.tenant_id)

    @application.put('/v1/friday/privacy',tags=['friday-privacy'])
    def privacy_save(payload:PrivacyPolicy,tenant:TenantContext=Depends(authenticate)):
        return privacy.save(tenant.tenant_id,payload)

    @application.post('/v1/friday/privacy/reviews/delete',tags=['friday-privacy'])
    def privacy_delete(payload:DeleteReviews,tenant:TenantContext=Depends(authenticate)):
        try:return privacy.delete(tenant.tenant_id,payload)
        except ValueError as error:raise HTTPException(409,str(error)) from error

    @application.post("/v1/friday/tasks", tags=["friday-assistant"])
    async def prepare_task(payload: TaskRequest, tenant: TenantContext = Depends(authenticate)):
        try:
            return await run_in_threadpool(tasks.prepare, tenant.tenant_id, payload)
        except ValidationError as error:
            raise HTTPException(503, "AI task output failed validation. No payment was performed.") from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        except Exception as error:
            raise HTTPException(503, "Live task planning unavailable. No payment was performed.") from error

    @application.get("/v1/friday/tasks/{task_id}", tags=["friday-assistant"])
    def read_task(task_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return tasks.get(tenant.tenant_id, task_id)
        except KeyError as error:
            raise HTTPException(404, "Task not found in this workspace") from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @application.post("/v1/friday/tasks/{task_id}/confirm", tags=["friday-assistant"])
    async def confirm_task(task_id: str, payload: TaskConfirmation, tenant: TenantContext = Depends(authenticate)):
        try:
            return await run_in_threadpool(tasks.confirm, tenant.tenant_id, task_id, payload)
        except KeyError as error:
            raise HTTPException(404, "Task not found in this workspace") from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        except Exception as error:
            raise HTTPException(503, "Confirmation unavailable. Check Activity before trying again; do not assume success or failure.") from error

    @application.post('/v1/friday/tasks/{task_id}/reconcile',tags=['friday-assistant'])
    def reconcile_task(task_id:str,tenant:TenantContext=Depends(authenticate)):
        try:return tasks.reconcile(tenant.tenant_id,task_id)
        except KeyError as error:raise HTTPException(404,'Task not found in this workspace') from error
        except ValueError as error:raise HTTPException(409,str(error)) from error
    from .friday_bank import FridayAnthosBank
    from .friday_chat import reply_to_user
    bank = FridayAnthosBank.from_env()
    application.state.friday_bank = bank

    @application.get("/v1/friday/bank", tags=["sandbox-bank"])
    async def bank_snapshot(tenant: TenantContext = Depends(authenticate)):
        return await run_in_threadpool(bank.snapshot, tenant.tenant_id)

    @application.post("/v1/friday/chat", tags=["friday-assistant"])
    async def chat(payload: FridayChatRequest, tenant: TenantContext = Depends(authenticate)):
        try:
            return await run_in_threadpool(reply_to_user,service,review,bank,tenant.tenant_id,payload)
        except Exception as error:
            raise HTTPException(503,"Friday chat is unavailable. No payment or other action was performed.") from error

    class ReviewTextRequest(BaseModel):
        model_config = ConfigDict(extra="forbid")
        text: str = Field(min_length=5, max_length=12000)

    @application.get("/v1/friday/reviews", tags=["financial-review"])
    def review_board(tenant: TenantContext = Depends(authenticate)):
        return review.board(tenant.tenant_id)

    @application.post("/v1/friday/reviews/statement", tags=["financial-review"])
    async def review_statement(payload: ReviewStatementRequest, tenant: TenantContext = Depends(authenticate)):
        if not payload.confirm_store_claims:
            raise HTTPException(422,"Confirm storage of parsed transaction claims first")
        try:
            return await run_in_threadpool(review.import_statement,tenant.tenant_id,payload.csv_text)
        except ValueError as error:
            raise HTTPException(422,str(error)) from error

    @application.post("/v1/friday/reviews", tags=["financial-review"])
    async def review_text(payload: ReviewTextRequest, tenant: TenantContext = Depends(authenticate)):
        try:
            return await run_in_threadpool(review.ingest, tenant.tenant_id, text=payload.text)
        except Exception as error:
            raise HTTPException(503, "Read-only understanding unavailable; no payment was requested") from error

    @application.post("/v1/friday/reviews/documents", tags=["financial-review"])
    async def review_document(request: Request, filename: str = Query(min_length=1, max_length=160),
                              tenant: TenantContext = Depends(authenticate)):
        mime = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if mime not in DOCUMENT_TYPES:
            raise HTTPException(415, "Use PNG, JPEG, WebP or PDF")
        data = await _read_bounded_document(request)
        if not _valid_document_signature(mime, data):
            raise HTTPException(422, "File signature does not match document type")
        name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
        if not name:
            raise HTTPException(422, "Invalid filename")
        try:
            return await run_in_threadpool(review.ingest, tenant.tenant_id, data=data, mime=mime, filename=name)
        except Exception as error:
            raise HTTPException(503, "Read-only document understanding unavailable; no payment was requested") from error

    inbox = FridayInbox(service)
    application.state.friday_inbox = inbox

    @application.get("/v1/friday/inbox", tags=["financial-friday"])
    def inbox_read(tenant: TenantContext = Depends(authenticate)):
        return inbox.read(tenant.tenant_id)

    @application.post("/v1/friday/inbox/{event_id}/retry", tags=["financial-friday"])
    def retry(event_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return inbox.retry(tenant.tenant_id, event_id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @application.post("/v1/friday/watch", tags=["financial-friday"])
    def watch(request: WatchRequest, tenant: TenantContext = Depends(authenticate)):
        return inbox.watch(tenant.tenant_id, request.enabled)

    @application.post("/v1/friday/arrivals/{case_id}", tags=["financial-friday"])
    def arrive(case_id: str, tenant: TenantContext = Depends(authenticate)):
        if case_id not in CASES:
            raise HTTPException(404, "scenario not found")
        return inbox.arrive(tenant.tenant_id, case_id)

    @application.get("/v1/friday/today", tags=["financial-friday"])
    def today(tenant: TenantContext = Depends(authenticate)):
        return service.daily_brief(tenant.tenant_id)

    @application.get("/v1/friday/workspace", tags=["financial-friday"])
    def workspace(tenant: TenantContext = Depends(authenticate)):
        from .friday_workspace import financial_workspace
        return financial_workspace(service, tenant.tenant_id)

    @application.post("/v1/friday/statements/analyze", tags=["financial-friday"])
    async def statement_analysis(request: StatementRequest, tenant: TenantContext = Depends(authenticate)):
        from carapace_core.friday_statement import analyze_statement
        try:
            return await run_in_threadpool(analyze_statement, request.csv_text)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @application.get("/v1/friday/bill-plan", tags=["financial-friday"])
    def bill_plan(tenant: TenantContext = Depends(authenticate)):
        from .friday_workspace import financial_workspace
        from carapace_core.friday_bill_plan import plan_bills
        return plan_bills(financial_workspace(service, tenant.tenant_id))

    @application.post("/v1/friday/follow-through", tags=["financial-friday"])
    def follow_through(request: FollowThroughRequest, tenant: TenantContext = Depends(authenticate)):
        from .friday_followthrough import acknowledge_recorded_bill
        return acknowledge_recorded_bill(service, tenant.tenant_id, request.bill_reference)

    @application.post("/v1/friday/bills/handle", tags=["financial-friday"])
    async def handle_bill(request: BillHandleRequest, tenant: TenantContext = Depends(authenticate)):
        from .friday_bill_handle import handle_reviewed_bill
        if not request.confirm_sandbox_execution:
            raise HTTPException(422, "Explicit artificial-money execution confirmation required")
        try:
            return await run_in_threadpool(handle_reviewed_bill, service, tenant.tenant_id,
                                          request.bill_reference, request.expected_bill_sha256)
        except KeyError as error:
            raise HTTPException(404, "Bill not found in this workspace") from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        except FridayUnderstandingUnavailable as error:
            raise HTTPException(503, "Understanding unavailable; no payment submitted") from error

    @application.get("/v1/friday/storage-status", tags=["financial-friday"])
    def storage_status(tenant: TenantContext = Depends(authenticate)):
        del tenant
        return service.storage_status()

    @application.get("/v1/friday/mandate", tags=["financial-friday"])
    def read_mandate(tenant: TenantContext = Depends(authenticate)):
        return service.mandate(tenant.tenant_id)

    @application.put("/v1/friday/mandate", tags=["financial-friday"])
    def save_mandate(request: FridayMandate, tenant: TenantContext = Depends(authenticate)):
        return service.save_mandate(tenant.tenant_id, request)

    @application.post("/v1/friday/test-provider/bills", tags=["financial-friday"])
    def publish_test_bill(request: TestProviderBill, tenant: TenantContext = Depends(authenticate)):
        return service.publish_test_bill(tenant.tenant_id, request)

    @application.get("/v1/friday/test-provider/bills", tags=["financial-friday"])
    def household_bills(tenant: TenantContext = Depends(authenticate)):
        return service.household_bills(tenant.tenant_id)

    @application.get("/v1/friday/live-input", tags=["financial-friday"])
    def live_inputs(tenant: TenantContext = Depends(authenticate)):
        return service.live_signals(tenant.tenant_id)

    @application.post("/v1/friday/live-input", tags=["financial-friday"])
    async def ingest_live_input(
        request: IncomingFinancialSignal, tenant: TenantContext = Depends(authenticate)
    ):
        try:
            return await run_in_threadpool(service.ingest_live_signal, tenant.tenant_id, request)
        except FridayUnderstandingUnavailable as error:
            raise HTTPException(503, "Financial understanding is unavailable; no payment was submitted", headers={"Retry-After": "10"}) from error

    @application.post("/v1/friday/documents", tags=["financial-friday"])
    async def ingest_document(
        request: Request,
        filename: str = Query(min_length=1, max_length=160),
        tenant: TenantContext = Depends(authenticate),
    ):
        mime_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if mime_type not in DOCUMENT_TYPES:
            raise HTTPException(415, "use a PNG, JPEG, WebP or PDF document")
        data = await _read_bounded_document(request)
        if not _valid_document_signature(mime_type, data):
            raise HTTPException(422, "file signature does not match its declared document type")
        safe_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
        if not safe_name:
            raise HTTPException(422, "filename is invalid")
        try:
            return await run_in_threadpool(
                service.ingest_document, tenant.tenant_id, safe_name, mime_type, data
            )
        except FridayUnderstandingUnavailable as error:
            raise HTTPException(503, "document understanding is unavailable; no action was taken") from error
        except Exception as error:
            raise HTTPException(503, "document outcome is unavailable; check activity before retrying") from error

    @application.post("/v1/friday/live-input/{event_id}/run", tags=["financial-friday"])
    async def run_live_input(event_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return await run_in_threadpool(service.run_live_signal, tenant.tenant_id, event_id)
        except KeyError as error:
            raise HTTPException(404, "live input not found") from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @application.get("/v1/friday/scenarios", tags=["financial-friday"])
    def scenarios(tenant: TenantContext = Depends(authenticate)):
        return {
            "product": "Financial Friday",
            "promise": "Delegate the goal. AI plans. The safety kernel proves. The executor acts once.",
            "scenarios": [
                {"id": key, "name": value[0], "description": value[1]}
                for key, value in CASES.items()
            ],
            "configured_mode": service.planner.mode,
            "model": service.planner.model_name,
            "storage": service.storage_status(),
            "scope": "Authorized fixtures and artificial money only",
        }

    @application.post("/v1/friday/scenarios/{case_id}/run", tags=["financial-friday"])
    async def run(case_id: str, request: FridayRunRequest, tenant: TenantContext = Depends(authenticate)):
        if case_id not in CASES:
            raise HTTPException(404, "scenario not found")
        planner = LocalFinancialFridayPlanner() if request.planner == "local" else None
        return await run_in_threadpool(service.run, tenant.tenant_id, case_id, planner)

    @application.get("/v1/friday/runs/{run_id}", tags=["financial-friday"])
    def get_run(run_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return service.get(tenant.tenant_id, run_id)
        except KeyError as error:
            raise HTTPException(404, "run not found") from error
