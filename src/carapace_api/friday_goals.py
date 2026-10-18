"""Read-only goal calculations and explicitly requested model tools."""
from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from carapace_core.friday_goals import GoalScenario, build_goal_scenario
from carapace_ai.friday_goal_intake import GoalIntakeRequest, interpret_goal
from carapace_ai.friday_research import ResearchRequest, research_public_topic
from carapace_ai.friday_roadmap import RoadmapIntakeRequest, interpret_roadmap
from carapace_core.friday_roadmap import RoadmapPreview, RoadmapChange, calculate_roadmap
from .friday_roadmap import FridayRoadmap
from .friday_privacy import privacy_generation
from carapace_core.friday_goals import rupees


def register_goal_routes(application, service, authenticate):
    service.roadmap = FridayRoadmap(service)

    @application.get('/v1/friday/goals/budget-hints', tags=['friday-goals'])
    def roadmap_budget_hints(tenant=Depends(authenticate)):
        view = service.portfolio.view(tenant.tenant_id)
        summary = view['summary']
        rows = summary['monthly']
        values = {}
        # These are reviewable historical averages, not disposable cash or a bank balance.
        if rows and not summary['repeated_row_candidates']:
            for source,destination in [('identified_income_minor','monthly_income_inr'),
                ('spending_minor','monthly_essentials_inr'),('loan_repayments_minor','monthly_existing_debt_inr')]:
                total=sum(row[source] for row in rows)
                if source != 'identified_income_minor' or total > 0:
                    values[destination]=rupees(total//len(rows))
        return {'fields':values,'revision':view['revision'],'workspace_generation':view['workspace_generation'],
            'period':summary['period'],'months_with_rows':len(rows),'warnings':summary['warnings'],
            'needs_confirmation':True,'private_statement_context_shared':False,
            'note':'Historical averages of supplied months only. Spending includes discretionary costs; loan payments can be incomplete. Missing accounts, partial months and categories can distort the proposal. Current liquid savings and a protected reserve are not inferred.'}

    @application.get('/v1/friday/goals/roadmap', tags=['friday-goals'])
    def roadmap_read(tenant=Depends(authenticate)):
        return service.roadmap.view(tenant.tenant_id)

    @application.get('/v1/friday/goals/export', tags=['friday-goals'])
    def roadmap_export(tenant=Depends(authenticate)):
        return service.roadmap.export(tenant.tenant_id)

    @application.post('/v1/friday/goals/roadmap', tags=['friday-goals'])
    def roadmap_change(payload: RoadmapChange, tenant=Depends(authenticate)):
        try:
            return service.roadmap.change(tenant.tenant_id,payload)
        except ValueError as error:
            raise HTTPException(409,str(error)) from error

    @application.post('/v1/friday/goals/roadmap-preview', tags=['friday-goals'])
    def roadmap_preview(payload: RoadmapPreview, tenant=Depends(authenticate)):
        return calculate_roadmap(payload.plan)

    @application.post('/v1/friday/goals/conversation', tags=['friday-goals'])
    async def roadmap_intake(payload: RoadmapIntakeRequest, tenant=Depends(authenticate)):
        generation = privacy_generation(service,tenant.tenant_id)
        try:
            result = await run_in_threadpool(interpret_roadmap,service.planner,payload)
        except ValueError as error:
            raise HTTPException(422,'A number or time period needs clarification. Nothing was saved.') from error
        except Exception as error:
            raise HTTPException(503,'Gemini is unavailable. Use Edit numbers to prepare a roadmap without AI.') from error
        if generation != privacy_generation(service,tenant.tenant_id):
            raise HTTPException(409,'Workspace cleared during the reply. Reload Goals.')
        return result

    @application.post('/v1/friday/goals/preview', tags=['friday-goals'])
    def preview_goal(payload: GoalScenario, tenant=Depends(authenticate)):
        try:
            return build_goal_scenario(payload)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @application.post('/v1/friday/goals/interpret', tags=['friday-goals'])
    async def goal_intake(payload: GoalIntakeRequest, tenant=Depends(authenticate)):
        if not payload.confirm_send_to_gemini:
            raise HTTPException(422, 'Confirm sending your goal text to Gemini first')
        try:
            return await run_in_threadpool(interpret_goal, service.planner, payload)
        except ValueError as error:
            raise HTTPException(422, 'A proposed number could not be confirmed. Review or enter the fields directly.') from error
        except Exception as error:
            raise HTTPException(503, 'Gemini goal reading is unavailable. The manual calculator still works.') from error

    @application.post('/v1/friday/research', tags=['friday-research'])
    async def research(payload: ResearchRequest, tenant=Depends(authenticate)):
        if not payload.confirm_public_search:
            raise HTTPException(422, 'Confirm sharing this public question with Google first')
        try:
            return await run_in_threadpool(research_public_topic, service.planner, payload)
        except Exception as error:
            raise HTTPException(503, 'Current-source research is unavailable or lacked attribution. No market figure was substituted.') from error
