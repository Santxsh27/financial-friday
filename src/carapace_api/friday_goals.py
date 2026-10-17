"""Read-only goal calculations and explicitly requested model tools."""
from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from carapace_core.friday_goals import GoalScenario, build_goal_scenario
from carapace_ai.friday_goal_intake import GoalIntakeRequest, interpret_goal
from carapace_ai.friday_research import ResearchRequest, research_public_topic


def register_goal_routes(application, service, authenticate):
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
