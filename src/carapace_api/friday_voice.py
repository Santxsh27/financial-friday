"""Private, no-store voice adapters; never load financial records for speech."""
from fastapi import Depends
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from carapace_ai.friday_voice import VoiceInput, VoiceReply, transcribe, speak
from .friday_privacy import privacy_generation


def register_voice_routes(application, service, authenticate):
    async def turn(payload, tenant, operation):
        headers = {'Cache-Control': 'no-store'}
        generation = privacy_generation(service, tenant.tenant_id)
        confirmed = (payload.confirm_send_audio_to_google if isinstance(payload, VoiceInput)
            else payload.confirm_send_text_to_google)
        if not confirmed:
            return JSONResponse({'detail': 'Confirm this voice turn with Google first'}, status_code=422, headers=headers)
        try:
            result = await run_in_threadpool(operation, service.planner, payload)
            if generation != privacy_generation(service, tenant.tenant_id):
                return JSONResponse({'detail': 'Workspace changed; discard this voice turn'}, status_code=409, headers=headers)
            return JSONResponse(result, headers=headers)
        except ValueError:
            return JSONResponse({'detail': 'Use a short, readable voice turn; nothing was performed'}, status_code=422, headers=headers)
        except Exception:
            return JSONResponse({'detail': 'Google voice is unavailable. Typing still works; no action was performed.'}, status_code=503, headers=headers)

    @application.post('/v1/friday/assistant/transcribe', tags=['friday-assistant'])
    async def voice_input(payload: VoiceInput, tenant=Depends(authenticate)):
        return await turn(payload, tenant, transcribe)

    @application.post('/v1/friday/assistant/speak', tags=['friday-assistant'])
    async def voice_reply(payload: VoiceReply, tenant=Depends(authenticate)):
        return await turn(payload, tenant, speak)
