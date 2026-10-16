"""Opt-in speech for a locally composed, aggregate-only statement briefing.

Uses the existing Vertex client. No free text, tools, microphone, storage, or
model-authored financial conclusions enter this path.
"""
import base64
import io
import logging
import wave

from pydantic import BaseModel, ConfigDict, Field


MODEL = 'gemini-2.5-flash-tts'
SAMPLE_RATE = 24_000
MAX_SECONDS = 30
MAX_PCM_BYTES = SAMPLE_RATE * 2 * MAX_SECONDS


class BriefingAudioRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=0, strict=True)
    workspace_generation: str = Field(min_length=1, max_length=80, strict=True)
    confirm_send_derived_totals_to_google: bool = Field(strict=True)


class SpeechUnavailable(RuntimeError):
    """A provider or output-format failure; never contains provider content."""


def _count(value):
    if type(value) is not int or not 0 <= value <= 1_000_000:
        raise ValueError('Statement briefing figures are unavailable')
    return value


def _rupees(value):
    if type(value) is not int or not 0 <= value <= 1_000_000_000_000_000:
        raise ValueError('Statement briefing figures are unavailable')
    return f'{value // 100:,}.{value % 100:02d}'


def spoken_brief(view):
    """Whitelist only numbers from the included, current statement analysis."""
    summary = view['summary']
    if not _count(summary['statement_count']) or not _count(summary['transaction_count']):
        raise ValueError('Include a saved statement before requesting a briefing')
    totals, checkup = summary['totals'], view['checkup']
    # Reject a damaged aggregate snapshot even for totals omitted from speech.
    for key in ('identified_income_minor','classified_spending_minor','loan_repayments_minor'):
        _rupees(totals[key])
    text = (
        f"{_count(summary['transaction_count'])} supplied entries checked. "
        f"Classified spending: {_rupees(totals['classified_spending_minor'])} rupees. "
        f"{_count(checkup['open_count'])} candidates need review. "
        "Statement totals, not a live balance or confirmed fraud. No money was moved."
    )
    if len(text.split()) > 50:
        raise ValueError('Statement briefing exceeds its word limit')
    return text


def _source(view):
    return (view['revision'], view['workspace_generation'], view['checkup']['source_fingerprint'])


def _pcm(response):
    """Accept only the documented 16-bit, mono, 24 kHz raw PCM format."""
    candidates = getattr(response, 'candidates', None)
    if not candidates or len(candidates) != 1:
        raise SpeechUnavailable('Speech output unavailable')
    finish = getattr(candidates[0], 'finish_reason', None)
    if getattr(finish, 'value', finish) != 'STOP':
        raise SpeechUnavailable('Speech output incomplete')
    content = getattr(candidates[0], 'content', None)
    parts = getattr(content, 'parts', None)
    if not parts or len(parts) != 1:
        raise SpeechUnavailable('Speech output unavailable')
    inline = getattr(parts[0], 'inline_data', None)
    mime = getattr(inline, 'mime_type', '')
    if not isinstance(mime, str):
        raise SpeechUnavailable('Speech format unavailable')
    tokens = [token.strip().lower() for token in mime.split(';')]
    parameters = {}
    for token in tokens[1:]:
        key, separator, value = token.partition('=')
        if not separator or key in parameters:
            raise SpeechUnavailable('Speech format unavailable')
        parameters[key] = value
    # L16 establishes the sample width; mono is the documented TTS default when
    # no channels parameter is emitted. An explicit different format is refused.
    if (tokens[0] != 'audio/l16' or parameters.get('codec') != 'pcm'
            or parameters.get('rate') != '24000' or parameters.get('channels', '1') != '1'
            or parameters.get('bits', '16') != '16'
            or set(parameters) - {'codec', 'rate', 'channels', 'bits'}):
        raise SpeechUnavailable('Speech format unavailable')
    data = getattr(inline, 'data', None)
    if (not isinstance(data, bytes) or not data or len(data) % 2
            or len(data) > MAX_PCM_BYTES or data.startswith((b'RIFF', b'OggS', b'fLaC', b'ID3'))):
        raise SpeechUnavailable('Speech length or format unavailable')
    return data


def briefing_audio(planner, portfolio, tenant, request: BriefingAudioRequest):
    if not request.confirm_send_derived_totals_to_google:
        raise ValueError('Confirm sharing the derived briefing totals with Google first')
    view = portfolio.view(tenant)
    if (view['revision'], view['workspace_generation']) != (request.expected_revision, request.workspace_generation):
        raise ValueError('Statement history changed; reload before requesting a briefing')
    text = spoken_brief(view)
    source = _source(view)
    if planner.mode != 'VERTEX_AI' or getattr(planner, '_client', None) is None:
        raise SpeechUnavailable('Google voice requires the configured Vertex client')
    from google.genai import types
    try:
        response = planner._client.models.generate_content(
            model=MODEL,
            contents='Read the following exactly, calmly and clearly, without additions: ' + text,
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=60_000,
                    retry_options=types.HttpRetryOptions(attempts=1)),
                response_modalities=['AUDIO'], max_output_tokens=1024, tools=[],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                speech_config=types.SpeechConfig(language_code='en-IN',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore')))),
        )
        pcm = _pcm(response)
    except SpeechUnavailable as error:
        logging.getLogger(__name__).warning('friday_speech_output_rejected reason=%s', str(error))
        raise
    except Exception as error:
        code=getattr(error,'code',None)
        logging.getLogger(__name__).warning('friday_speech_provider_rejected type=%s status=%s',
            type(error).__name__, code if type(code) is int else 'unknown')
        raise SpeechUnavailable('Google voice is currently unavailable') from None
    current = portfolio.view(tenant)
    if _source(current) != source or spoken_brief(current) != text:
        raise ValueError('Statement history changed during speech generation; reload before listening')
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(pcm)
    return {'mime': 'audio/wav', 'audio_base64': base64.b64encode(output.getvalue()).decode('ascii'),
            'spoken_text': text, 'source_revision': view['revision'],
            'workspace_generation': view['workspace_generation'], 'money_moved': False,
            'mode': 'VERTEX_AI', 'model': MODEL, 'model_calls': 1}
