"""Seed-Speech binary WebSocket protocol; audio and transcripts stay in memory."""
import asyncio
import gzip
import io
import json
import logging
import struct
import uuid
import wave
from urllib.parse import urlsplit

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from app.llm_client import LLMResponseError

logger = logging.getLogger(__name__)
MAX_RESPONSE_BYTES = 2_000_000


class SpeechProtocolError(ValueError):
    def __init__(self, code=0):
        self.code = code
        super().__init__("Invalid speech response")


def packet(kind, payload, *, final=False, json_payload=False):
    compressed = gzip.compress(payload)
    header = bytes((0x11, (kind << 4) | (2 if final else 0),
                    0x11 if json_payload else 0x01, 0))
    return header + struct.pack(">I", len(compressed)) + compressed


def response_packet(data):
    if not isinstance(data, bytes) or len(data) < 8 or data[0] >> 4 != 1:
        raise SpeechProtocolError()
    offset = (data[0] & 15) * 4
    kind, flags = data[1] >> 4, data[1] & 15
    serialization, compression = data[2] >> 4, data[2] & 15
    if offset < 4 or kind not in (9, 15) or compression not in (0, 1):
        raise SpeechProtocolError()
    code = 0
    if flags & 1:
        offset += 4
    if kind == 15:
        if len(data) < offset + 4:
            raise SpeechProtocolError()
        code = struct.unpack_from(">I", data, offset)[0]
        raise SpeechProtocolError(code)
    if serialization != 1 or len(data) < offset + 4:
        raise SpeechProtocolError()
    size = struct.unpack_from(">I", data, offset)[0]
    payload = data[offset + 4:]
    if size != len(payload) or size > MAX_RESPONSE_BYTES:
        raise SpeechProtocolError()
    if compression == 1:
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as source:
            payload = source.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise SpeechProtocolError()
    result = json.loads(payload)
    if not isinstance(result, dict):
        raise SpeechProtocolError()
    return result, bool(flags & 2)


def wav_pcm(audio):
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            if (source.getnchannels() != 1 or source.getsampwidth() != 2
                    or source.getframerate() != 16000 or source.getcomptype() != "NONE"
                    or source.getnframes() > 16000 * 30):
                raise ValueError("Expected mono 16kHz PCM16 WAV, at most 30 seconds")
            pcm = source.readframes(source.getnframes())
            if not pcm or len(pcm) != source.getnframes() * 2:
                raise ValueError("Empty or truncated audio")
            return pcm
    except (wave.Error, EOFError) as exc:
        raise ValueError("Invalid WAV") from exc


async def transcribe_seed(settings, audio, language):
    parts = urlsplit(settings.speech_asr_url)
    if parts.scheme != "wss" or not parts.hostname or parts.username or parts.password:
        raise LLMResponseError("SPEECH_ASR_URL 必须是 WSS 接口。")
    try:
        pcm = wav_pcm(audio)
    except ValueError as exc:
        raise LLMResponseError("请提供 30 秒以内的单声道 16kHz PCM16 WAV 音频。") from exc
    request = {
        "user": {"uid": uuid.uuid4().hex},
        "audio": {"format": "pcm", "codec": "raw", "rate": 16000, "bits": 16, "channel": 1},
        "request": {"model_name": "bigmodel", "enable_itn": True, "enable_punc": True},
    }
    # Only nostream supports an explicit language hint.
    if parts.path.endswith("/bigmodel_nostream"):
        request["audio"]["language"] = "en-US" if language == "en" else "zh-CN"

    async def recognize():
        async with connect(
            settings.speech_asr_url,
            additional_headers={
                "X-Api-Key": settings.speech_api_key,
                "X-Api-Resource-Id": settings.speech_resource_id,
                "X-Api-Connect-Id": str(uuid.uuid4()),
            },
            open_timeout=min(settings.asr_timeout_seconds, 10),
            close_timeout=2,
            max_size=MAX_RESPONSE_BYTES,
            proxy=None,
        ) as ws:
            await ws.send(packet(1, json.dumps(request).encode(), json_payload=True))

            async def send_audio():
                for start in range(0, len(pcm), 6400):
                    end = min(start + 6400, len(pcm))
                    await ws.send(packet(2, pcm[start:end], final=end == len(pcm)))
                    await asyncio.sleep(0)

            sender = asyncio.create_task(send_audio())
            text = ""
            try:
                async for data in ws:
                    result, final = response_packet(data)
                    status = result.get("code", 0)
                    if status not in (0, 1000, 20000000):
                        raise SpeechProtocolError(status if isinstance(status, int) else 0)
                    recognized = result.get("result", {})
                    if isinstance(recognized, dict) and isinstance(recognized.get("text"), str):
                        text = recognized["text"]
                    if final:
                        await sender
                        return text.strip()[:6000]
                raise SpeechProtocolError()
            finally:
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)

    try:
        return await asyncio.wait_for(recognize(), timeout=settings.asr_timeout_seconds)
    except (WebSocketException, OSError, asyncio.TimeoutError, ValueError) as exc:
        # Record only diagnostic types/status; no credentials, audio or transcript.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        code = getattr(exc, "code", None)
        logger.warning("Seed ASR failed error=%s status=%s code=%s", type(exc).__name__, status, code)
        raise LLMResponseError("Seed-Speech 语音识别失败，请重试或使用文字补录。") from exc
