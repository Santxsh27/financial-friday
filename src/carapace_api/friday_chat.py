"""Server-selected, tenant-scoped conversation context; no arbitrary retrieval."""
from carapace_ai.friday_chat import answer_chat


def chat_context(service, review, bank, tenant: str) -> dict:
    board = review.board(tenant)
    evidence = []
    # Limit records, fields and text before model invocation. Do not send source
    # uploads, signatures, credentials or raw ledger account numbers.
    for item in board["cases"][:10]:
        evidence.append({"evidence_id": item["case_id"],
            "source": "USER_SUPPLIED_CLAIM", "supplier": (item.get("supplier") or "")[:160],
            "reference": (item.get("reference") or "")[:120],
            "state": item["state"], "checks": item["checks"],
            "currency": item["currency"], "amount_minor": item["amount_minor"],
            "due_date": item["due_date"], "next_action": item["next_action"][:400]})
    rules = service.mandate(tenant)
    # Anthos is a retired optional developer integration, not customer context.
    # Do not query a separate bank when someone opts into their Friday inbox.
    return {"evidence": evidence, "coverage": "At most 10 cases from the latest 50 review inputs, not a complete statement",
            "unconfirmed_bill_totals": board["unconfirmed_bill_totals"],
            "currency_scales": board["currency_scales"],
            "friday_sandbox": {"scope": "ARTIFICIAL_MONEY", "currency": "INR",
                "balance_minor": rules["sandbox_balance_minor"],
                "protected_balance_minor": rules["mandate"]["protected_balance_minor"]},
            "bank": {"status": "NOT_CONNECTED", "scope": "NO_REAL_BANK_ACCESS"}}


def reply_to_user(service, review, bank, tenant, request, *, statement_only=False):
    if statement_only and request.include_workspace:
        raise ValueError('The bill inbox is retired here; share statement totals instead')
    from .friday_buddy import FridayBuddy
    from .friday_privacy import privacy_generation
    from carapace_core.friday_trace import record_stage
    private_context=any((request.include_workspace,request.include_cashflow,request.include_diary,request.include_statements,request.include_roadmap))
    generation=privacy_generation(service,tenant) if private_context else None
    context = chat_context(service, review, bank, tenant) if request.include_workspace else {}
    preferences = FridayBuddy(service).model_preferences(tenant, request.include_preferences)
    cashflow = service.cashflow.model_context(tenant) if request.include_cashflow else {}
    diary = service.diary.model_context(tenant) if request.include_diary else {}
    view=service.portfolio.view(tenant) if request.include_statements else None
    statements=service.portfolio.model_context(tenant,view) if view else {}
    if request.roadmap_proposal and not request.include_roadmap:
        raise ValueError('Confirm sharing the proposed roadmap first')
    saved_roadmap=service.roadmap.model_context(tenant) if request.include_roadmap else {}
    roadmap=saved_roadmap
    if request.roadmap_proposal:
        from carapace_core.friday_roadmap import calculate_roadmap
        proposal=calculate_roadmap(request.roadmap_proposal)
        roadmap={'scope':'UNSAVED_USER_PROPOSAL','plan':request.roadmap_proposal.model_dump(),
            'summary':{k:v for k,v in proposal.items() if k!='calendar' and v is not None}}
    result=answer_chat(service.planner, request, context, preferences, cashflow, diary, statements, statement_only=statement_only,roadmap=roadmap)
    # A consented old context must not reappear after cleanup, even when only
    # a diary, forecast or older inbox was shared (not statement totals).
    if private_context and privacy_generation(service,tenant)!=generation:
        record_stage('validation',ok=False,reason='stale_revision')
        raise ValueError('Private context changed during this answer; reload before trying again')
    if ((request.include_cashflow and service.cashflow.model_context(tenant)!=cashflow) or
            (request.include_diary and service.diary.model_context(tenant)!=diary) or
            (request.include_workspace and chat_context(service,review,bank,tenant)!=context) or
            (request.include_roadmap and service.roadmap.model_context(tenant)!=saved_roadmap)):
        record_stage('validation',ok=False,reason='stale_revision')
        raise ValueError('Shared records changed during this answer; reload before relying on it')
    result['context_receipt']={'statement_totals':'SHARED' if statements else 'EMPTY' if request.include_statements else 'NOT_SHARED',
        'financial_inbox':'SHARED' if request.include_workspace else 'NOT_SHARED',
        'saved_roadmap':'SHARED' if roadmap else 'EMPTY' if request.include_roadmap else 'NOT_SHARED',
        'roadmap_scope':'UNSAVED_USER_PROPOSAL' if request.roadmap_proposal else 'SAVED' if roadmap else 'NONE',
        'transaction_descriptions_shared':False,'bank_connected':False,
        'statement_revision':view['revision'] if view else None,
        'included_statement_count':view['summary']['statement_count'] if view else 0,
        'statement_period':view['summary']['period'] if view else None}
    if view:
        current=service.portfolio.view(tenant)
        if (current['revision'],current['workspace_generation'])!=(view['revision'],view['workspace_generation']):
            raise ValueError('Statement history changed during this answer; reload before relying on it')
    result['money_plan']=None
    if result.get('plan') and statements:
        from carapace_core.friday_money_plan import build_money_plan, MoneyPlanDraft
        result['money_plan']=build_money_plan(view,MoneyPlanDraft.model_validate(result['plan']))
        result['money_plan']['proposal_source']='GEMINI_TYPED_GOAL'
    if result.get('visual_request') in {'SPENDING','MONTHLY'} and statements:
        result['statement_visuals']={'source_revision':view['revision'],
            'categories':view['summary']['categories'],'monthly':view['summary']['monthly'],
            'warnings':view['summary']['warnings']}
    if result.get('checkup_action') in {'MONEY_SHIELD','PREPARE_ENQUIRY'} and not statements:
        result['reply']='No personal check was completed. Add and review a statement first, then choose to share its totals and derived findings with Friday. You can also open My money without sharing anything with Gemini.'
    if result.get('checkup_action','NONE')!='NONE' and statements:
        from carapace_core.friday_checkup import prepare_enquiry
        checkup=view['checkup']
        selected=result.get('finding_id')
        finding=next((f for f in checkup['findings'] if f['finding_id']==selected),None) if selected else next((f for f in checkup['findings'] if not f['reviewed']),None)
        result['checkup_view']={'scope':checkup['scope'],'source_revision':view['revision'],
            'workspace_generation':view['workspace_generation'],'action':result['checkup_action'],
            'finding_id':finding['finding_id'] if finding else None,
            'draft':prepare_enquiry(finding) if finding and result['checkup_action']=='PREPARE_ENQUIRY' else None}
        if not finding and result['checkup_action']=='PREPARE_ENQUIRY':
            result['reply']='There is no open checkup finding to fill an enquiry from. You can review Transactions or ask me for a general unsent message template.'
        elif result['checkup_view']['draft']:
            # Completion claims are server-owned, not model-generated authority.
            result['reply']='Your unsent enquiry is ready, with the relevant source dates and amounts. Nothing was sent and no refund is claimed.'
        if result['checkup_action']=='MONEY_SHIELD':
            shield=checkup['money_shield']
            result['reply']=('Your Money Shield is ready. '+str(shield['ambiguous_count'])+
                ' trail(s) have multiple matching explanations; '+str(shield['held_count'])+
                ' could not be linked with the available evidence. Open the visual to see why. No money was moved or recovered.')
    # The freshness reads above may themselves overlap cleanup. Check again
    # after all reads/derived response assembly, not only before those reads.
    if private_context and privacy_generation(service,tenant)!=generation:
        record_stage('validation',ok=False,reason='stale_revision')
        raise ValueError('Private context was cleared while checking this answer; reload first')
    return result
