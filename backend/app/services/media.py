"""Provider-neutral voice/video media abstraction (Phase 16).

Phase 16 ships the ARCHITECTURE, not a production vendor integration:
- ``MediaProfile`` — the provider-neutral session media configuration
  (voice enabled, video enabled, STT/TTS provider names, device
  constraints). No credentials are ever stored.
- ``SpeechToText`` / ``TextToSpeech`` — capability interfaces. Adapters
  are selected by configuration; with no provider configured, calling
  them fails safe with ``AI_MEDIA_UNAVAILABLE`` (never a fabricated
  transcription or audio).
- ``MockMedia`` — deterministic, in-memory implementation used ONLY by
  the test suite to exercise the engine's failure/fallback paths.

Live video transport (WebRTC) stays a frontend concern: signaling,
ICE/TURN and reconnect handling are documented requirements, not
invented server-side media. The backend exposes only the session media
profile and records objective transport failures as integrity signals.

Privacy: no raw audio/video is stored by this module or the engine.
Recording (if ever enabled) is an explicit, consent-governed,
retention-bound feature that does not exist yet — see PHASE_16_PRIVACY.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger("asktrabaajo.media")

AI_MEDIA_UNAVAILABLE = "ai.media_unavailable"
AI_STT_FAILED = "ai.stt_failed"
AI_TTS_FAILED = "ai.tts_failed"


class MediaUnavailableError(AppError):
    status_code = 503
    code = AI_MEDIA_UNAVAILABLE

    def __init__(self, message: str = "Voice/video is not configured for this deployment.") -> None:
        super().__init__(message, status_code=503, code=AI_MEDIA_UNAVAILABLE)


class MediaFailureError(AppError):
    status_code = 502
    code = AI_STT_FAILED

    def __init__(self, message: str, code: str = AI_STT_FAILED) -> None:
        super().__init__(message, status_code=502, code=code)


@dataclass(frozen=True)
class MediaProfile:
    """Provider-neutral session media configuration (never credentials)."""

    voice_enabled: bool = False
    video_enabled: bool = False
    stt_provider: str = "none"
    tts_provider: str = "none"
    language: str = "en"
    device_constraints: Dict = field(default_factory=lambda: {"audio": True, "video": False})

    def as_dict(self) -> dict:
        return {
            "voice_enabled": self.voice_enabled,
            "video_enabled": self.video_enabled,
            "stt_provider": self.stt_provider,
            "tts_provider": self.tts_provider,
            "language": self.language,
            "device_constraints": dict(self.device_constraints),
        }


def build_media_profile(
    *,
    interview_type: str,
    language: str = "en",
    voice_enabled: Optional[bool] = None,
    video_enabled: Optional[bool] = None,
) -> MediaProfile:
    """Resolve the session media profile from settings + interview type.

    Voice/video are opt-in at session creation and default OFF until a
    production provider is configured. ``technical`` interviews default
    to text/voice-optional; nothing here ever requires camera access.
    """
    settings = get_settings()
    stt = getattr(settings, "ai_stt_provider", "none") or "none"
    tts = getattr(settings, "ai_tts_provider", "none") or "none"
    voice = bool(voice_enabled) and stt != "none"
    return MediaProfile(
        voice_enabled=voice,
        video_enabled=bool(video_enabled),
        stt_provider=stt,
        tts_provider=tts,
        language=language,
    )


class SpeechToText:
    """Transcribe audio. Subclasses are provider adapters; none ship wired."""

    provider_name = "none"

    def transcribe(self, audio_ref: str, language: str = "en") -> str:
        raise MediaUnavailableError()


class TextToSpeech:
    """Synthesize speech. Subclasses are provider adapters; none ship wired."""

    provider_name = "none"

    def synthesize(self, text: str, language: str = "en") -> str:
        raise MediaUnavailableError()


class MockMedia(SpeechToText, TextToSpeech):
    """Deterministic test double — never used outside the test suite."""

    provider_name = "mock"

    def __init__(self, transcript: str = "mock transcription of the candidate answer") -> None:
        self._transcript = transcript
        self.calls: List[str] = []

    def transcribe(self, audio_ref: str, language: str = "en") -> str:
        self.calls.append(f"stt:{audio_ref}")
        return self._transcript

    def synthesize(self, text: str, language: str = "en") -> str:
        self.calls.append(f"tts:{len(text)}")
        return f"<mock-audio:{len(text)}>"


_ADAPTERS: Dict[str, Callable[[], object]] = {
    "none": lambda: None,
    "mock": MockMedia,
}


def get_stt(provider: Optional[str] = None) -> SpeechToText:
    name = provider or get_settings().ai_stt_provider or "none"
    if name == "mock":
        return MockMedia()
    if name != "none":
        logger.warning("media.stt_unconfigured provider=%s", name)
    return SpeechToText()


def get_tts(provider: Optional[str] = None) -> TextToSpeech:
    name = provider or get_settings().ai_tts_provider or "none"
    if name == "mock":
        return MockMedia()
    if name != "none":
        logger.warning("media.tts_unconfigured provider=%s", name)
    return TextToSpeech()