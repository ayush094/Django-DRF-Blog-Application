"""
Text-to-Speech Provider Module

This module provides an abstraction layer for TTS services.
Currently implements Google Cloud Text-to-Speech with support for multiple
languages and voice styles.
"""
import os
import logging
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    """Container for TTS generation results."""
    audio_bytes: bytes
    duration_seconds: int
    sample_rate: int
    language_code: str
    voice_name: str
    speaking_rate: float
    file_extension: str = 'mp3'
    content_type: str = 'audio/mpeg'


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    def generate_audio(
        self,
        text: str,
        language: str = 'en',
        voice_style: str = 'neutral',
        speaking_rate: float = 1.0,
        **kwargs
    ) -> AudioResult:
        """
        Generate audio from text.

        Args:
            text: The text to convert to speech
            language: Language code (en, hi, gu)
            voice_style: Voice style (serious, storytelling, educational)
            speaking_rate: Speaking rate multiplier (0.5 to 2.0)
            **kwargs: Additional provider-specific options

        Returns:
            AudioResult containing the generated audio and metadata
        """
        pass

    @abstractmethod
    def get_available_voices(self, language: str) -> list:
        """Return available voices for the given language."""
        pass

    @abstractmethod
    def estimate_duration(self, text: str, speaking_rate: float = 1.0) -> int:
        """Estimate audio duration in seconds based on text length."""
        pass

    def split_text_for_tts(
        self,
        text: str,
        max_chars: int = 5000
    ) -> list:
        """
        Split long text into chunks suitable for TTS processing.

        Providers can override this, but the default logic works well for
        both the Google provider and the mock development provider.
        """
        if len(text) <= max_chars:
            return [text]

        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


class GoogleTTSProvider(BaseTTSProvider):
    """
    Google Cloud Text-to-Speech provider implementation.

    Features:
    - Multi-language support (English, Hindi, Gujarati)
    - Neural voices for natural sounding speech
    - SSML support for enhanced control
    - Multiple voice styles per language
    """

    # Voice configurations per language and style
    # Using Neural2 voices for best quality, falling back to Standard where Neural isn't available
    VOICE_MAPPING: Dict[str, Dict[str, str]] = {
        'en': {
            'serious': 'en-US-Neural2-F',        # Professional female voice
            'storytelling': 'en-US-Neural2-D',   # Expressive male voice
            'educational': 'en-US-Neural2-C',     # Clear narration female voice
            'neutral': 'en-US-Neural2-A',        # Neutral narration
            'default': 'en-US-Neural2-C',
        },
        'hi': {
            'serious': 'hi-IN-Standard-A',       # Female voice
            'storytelling': 'hi-IN-Standard-B',  # Male voice
            'educational': 'hi-IN-Standard-C',   # Female voice
            'neutral': 'hi-IN-Standard-D',      # Male voice
            'default': 'hi-IN-Standard-A',
        },
        'gu': {
            'serious': 'gu-IN-Standard-A',       # Female voice
            'storytelling': 'gu-IN-Standard-B',  # Male voice
            'educational': 'gu-IN-Standard-A',   # Female voice (same as serious)
            'neutral': 'gu-IN-Standard-A',
            'default': 'gu-IN-Standard-A',
        },
    }

    # Language code mapping for Google TTS
    LANGUAGE_CODES = {
        'en': 'en-US',
        'hi': 'hi-IN',
        'gu': 'gu-IN',
    }

    def __init__(self):
        """Initialize Google TTS client."""
        try:
            # Import here to allow graceful degradation if not installed
            from google.cloud import texttospeech

            # Check for credentials
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path:
                logger.warning(
                    "GOOGLE_APPLICATION_CREDENTIALS not set. "
                    "Set this environment variable to your service account JSON file."
                )

            self.client = texttospeech.TextToSpeechClient()
            self._initialized = True
            logger.info("Google Cloud TTS client initialized successfully")

        except ImportError:
            logger.warning(
                "google-cloud-texttospeech not installed. "
                "Install with: pip install google-cloud-texttospeech"
            )
            self._initialized = False
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud TTS: {e}")
            self._initialized = False
            self.client = None

    @property
    def is_available(self) -> bool:
        """Check if the TTS provider is properly initialized."""
        return self._initialized and self.client is not None

    def get_voice_name(self, language: str, voice_style: str) -> str:
        """
        Get the appropriate voice name for the given language and style.

        Args:
            language: Language code (en, hi, gu)
            voice_style: Voice style (serious, storytelling, educational, neutral)

        Returns:
            Voice name string for Google TTS
        """
        language_voices = self.VOICE_MAPPING.get(language, self.VOICE_MAPPING['en'])
        return language_voices.get(voice_style, language_voices['default'])

    def get_language_code(self, language: str) -> str:
        """Get Google TTS language code from our internal language code."""
        return self.LANGUAGE_CODES.get(language, 'en-US')

    def generate_audio(
        self,
        text: str,
        language: str = 'en',
        voice_style: str = 'educational',
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        **kwargs
    ) -> AudioResult:
        """
        Generate audio from text using Google Cloud TTS.

        Args:
            text: The text to convert to speech
            language: Language code (en, hi, gu)
            voice_style: Voice style (serious, storytelling, educational)
            speaking_rate: Speaking rate multiplier (0.25 to 4.0)
            pitch: Pitch modification (-20.0 to 20.0)
            volume_gain_db: Volume gain (-96.0 to 16.0)

        Returns:
            AudioResult with generated audio and metadata

        Raises:
            RuntimeError: If TTS provider is not initialized
        """
        if not self.is_available:
            raise RuntimeError(
                "Google Cloud TTS is not available. "
                "Ensure google-cloud-texttospeech is installed and "
                "GOOGLE_APPLICATION_CREDENTIALS is set."
            )

        voice_name = self.get_voice_name(language, voice_style)
        language_code = self.get_language_code(language)

        # Clamp speaking rate to valid range
        speaking_rate = max(0.25, min(4.0, speaking_rate))
        # Clamp pitch to valid range
        pitch = max(-20.0, min(20.0, pitch))

        logger.info(
            f"Generating audio: language={language}, voice={voice_name}, "
            f"rate={speaking_rate}, text_length={len(text)}"
        )

        try:
            from google.cloud import texttospeech

            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice_params = texttospeech.VoiceSelectionParams(
                name=voice_name,
                language_code=language_code,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db,
                effects_profile_id=['small-bluetooth-speaker-class-device'],
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )

            duration = self.estimate_duration(text, speaking_rate)

            result = AudioResult(
                audio_bytes=response.audio_content,
                duration_seconds=duration,
                sample_rate=24000,  # Default for Neural voices
                language_code=language_code,
                voice_name=voice_name,
                speaking_rate=speaking_rate,
                file_extension='mp3',
                content_type='audio/mpeg',
            )

            logger.info(f"Successfully generated {duration}s of audio")
            return result

        except Exception as e:
            logger.error(f"Google TTS synthesis failed: {e}")
            raise RuntimeError(f"Audio generation failed: {str(e)}")

    def generate_audio_ssml(
        self,
        ssml: str,
        language: str = 'en',
        voice_style: str = 'educational',
        speaking_rate: float = 1.0,
        **kwargs
    ) -> AudioResult:
        """
        Generate audio from SSML markup for enhanced control.

        SSML allows:
        - Pauses: <break time="2s"/>
        - Emphasis: <emphasis>important</emphasis>
        - Speed changes: <prosody rate="fast">text</prosody>
        - Pronunciation hints: <phoneme alphabet="ipa" ph="...">word</phoneme>

        Args:
            ssml: SSML markup string
            language: Language code
            voice_style: Voice style
            speaking_rate: Base speaking rate

        Returns:
            AudioResult with generated audio
        """
        if not self.is_available:
            raise RuntimeError("Google Cloud TTS is not available")

        voice_name = self.get_voice_name(language, voice_style)
        language_code = self.get_language_code(language)

        try:
            from google.cloud import texttospeech

            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

            voice_params = texttospeech.VoiceSelectionParams(
                name=voice_name,
                language_code=language_code,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )

            duration = self.estimate_duration(ssml, speaking_rate)

            return AudioResult(
                audio_bytes=response.audio_content,
                duration_seconds=duration,
                sample_rate=24000,
                language_code=language_code,
                voice_name=voice_name,
                speaking_rate=speaking_rate,
            )

        except Exception as e:
            logger.error(f"SSML audio generation failed: {e}")
            raise

    def get_available_voices(self, language: str) -> list:
        """
        Get available voices for the given language.

        Args:
            language: Language code (en, hi, gu)

        Returns:
            List of available voice names with their styles
        """
        voices = self.VOICE_MAPPING.get(language, self.VOICE_MAPPING['en'])
        return [
            {"style": style, "voice_name": voice}
            for style, voice in voices.items()
            if style != 'default'
        ]

    def estimate_duration(self, text: str, speaking_rate: float = 1.0) -> int:
        """
        Estimate audio duration based on text length and speaking rate.

        This is an approximation. Actual duration depends on:
        - Voice characteristics
        - Punctuation and pauses
        - Language (some languages take longer to speak)

        Args:
            text: The text to estimate duration for
            speaking_rate: Speaking rate multiplier

        Returns:
            Estimated duration in seconds
        """
        # Average speaking rate: ~150 words per minute (2.5 words/second)
        # This varies by language and voice, but gives a reasonable estimate
        words = len(text.split())

        # Adjust for speaking rate
        base_duration = words / 2.5  # seconds at normal speed
        adjusted_duration = base_duration / speaking_rate

        # Add buffer for pauses and natural speech patterns
        # Typically adds 10-20% for natural pauses
        buffered_duration = adjusted_duration * 1.15

        return max(1, int(buffered_duration))

class MockTTSProvider(BaseTTSProvider):
    """
    Mock TTS provider for development and testing.

    Generates placeholder audio without requiring external API.
    Useful for:
    - Local development
    - Testing without API costs
    - CI/CD pipelines
    """

    def generate_audio(
        self,
        text: str,
        language: str = 'en',
        voice_style: str = 'neutral',
        speaking_rate: float = 1.0,
        **kwargs
    ) -> AudioResult:
        """Generate mock audio (placeholder)."""
        duration = self.estimate_duration(text, speaking_rate)

        # Generate a minimal valid MP3 header (silent placeholder)
        # This is a minimal MP3 frame header that players can recognize
        mock_audio = bytes([
            0xFF, 0xFB, 0x90, 0x00,  # MP3 frame header
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])

        logger.warning("Using mock TTS provider - no actual audio generated")

        return AudioResult(
            audio_bytes=mock_audio,
            duration_seconds=duration,
            sample_rate=24000,
            language_code=language,
            voice_name=f"mock-{voice_style}",
            speaking_rate=speaking_rate,
            file_extension='mp3',
            content_type='audio/mpeg',
        )

    def get_available_voices(self, language: str) -> list:
        """Return mock voice options."""
        return [
            {"style": "serious", "voice_name": "mock-serious"},
            {"style": "storytelling", "voice_name": "mock-storytelling"},
            {"style": "educational", "voice_name": "mock-educational"},
        ]

    def estimate_duration(self, text: str, speaking_rate: float = 1.0) -> int:
        """Estimate duration for mock audio."""
        words = len(text.split())
        return max(1, int(words / 2.5 / speaking_rate))


class LocalOfflineTTSProvider(BaseTTSProvider):
    """
    Offline TTS provider powered by espeak-ng/espeak.

    This avoids external API costs and produces a real WAV file that browsers
    can play directly.
    """

    LANGUAGE_CODES = {
        'en': 'en-us',
        'hi': 'hi',
        'gu': 'gu',
    }

    def __init__(self):
        self.binary = shutil.which('espeak-ng') or shutil.which('espeak')
        self._initialized = bool(self.binary)
        if self._initialized:
            logger.info("Local offline TTS provider initialized with %s", self.binary)
        else:
            logger.warning("Local offline TTS provider unavailable: espeak-ng/espeak not installed")

    @property
    def is_available(self) -> bool:
        return self._initialized

    def _voice_for_language(self, language: str) -> str:
        return self.LANGUAGE_CODES.get(language, 'en-us')

    def generate_audio(
        self,
        text: str,
        language: str = 'en',
        voice_style: str = 'neutral',
        speaking_rate: float = 1.0,
        **kwargs
    ) -> AudioResult:
        if not self.is_available:
            raise RuntimeError("Local offline TTS is not available.")

        duration = self.estimate_duration(text, speaking_rate)
        speed_wpm = max(120, min(260, int(175 * speaking_rate)))
        preferred_voice = self._voice_for_language(language)

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            wav_path = tmp_file.name

        mp3_bytes = None
        try:
            try:
                self._run_espeak(
                    text=text,
                    output_path=wav_path,
                    voice=preferred_voice,
                    speed_wpm=speed_wpm,
                )
                selected_voice = preferred_voice
            except subprocess.CalledProcessError:
                logger.warning(
                    "Local TTS voice '%s' unavailable, falling back to English voice.",
                    preferred_voice,
                )
                selected_voice = 'en-us'
                self._run_espeak(
                    text=text,
                    output_path=wav_path,
                    voice=selected_voice,
                    speed_wpm=speed_wpm,
                )

            # Convert WAV to MP3 using ffmpeg
            mp3_bytes = self._convert_wav_to_mp3(wav_path)

        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        if mp3_bytes is None:
            raise RuntimeError("Failed to convert audio to MP3")

        return AudioResult(
            audio_bytes=mp3_bytes,
            duration_seconds=duration,
            sample_rate=22050,
            language_code=language,
            voice_name=f"{os.path.basename(self.binary)}:{selected_voice}",
            speaking_rate=speaking_rate,
            file_extension='mp3',
            content_type='audio/mpeg',
        )

    def _run_espeak(self, *, text: str, output_path: str, voice: str, speed_wpm: int) -> None:
        subprocess.run(
            [self.binary, '-w', output_path, '-v', voice, '-s', str(speed_wpm), '--stdin'],
            input=text.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def _convert_wav_to_mp3(self, wav_path: str) -> bytes:
        """
        Convert WAV file to MP3 using ffmpeg.

        Args:
            wav_path: Path to input WAV file

        Returns:
            MP3 file bytes

        Raises:
            RuntimeError: If conversion fails
        """
        try:
            # Use ffmpeg to convert WAV to MP3 with good quality
            # -i: input file
            # -codec:a libmp3lame: use LAME MP3 encoder
            # -qscale:a 2: variable bitrate, quality 2 (good quality, ~190-250 kbps)
            # -y: overwrite output
            result = subprocess.run(
                [
                    'ffmpeg',
                    '-i', wav_path,
                    '-codec:a', 'libmp3lame',
                    '-qscale:a', '2',
                    '-y',
                    'pipe:1'  # output to stdout
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr.decode()}")
            raise RuntimeError("Failed to convert audio to MP3")
        except FileNotFoundError:
            logger.error("FFmpeg not found. Install ffmpeg to enable MP3 conversion.")
            raise RuntimeError("FFmpeg not available")

    def get_available_voices(self, language: str) -> list:
        voice = self._voice_for_language(language)
        return [
            {"style": "serious", "voice_name": voice},
            {"style": "storytelling", "voice_name": voice},
            {"style": "educational", "voice_name": voice},
        ]

    def estimate_duration(self, text: str, speaking_rate: float = 1.0) -> int:
        words = len(text.split())
        return max(1, int(words / 2.4 / max(speaking_rate, 0.5)))


def get_tts_provider() -> BaseTTSProvider:
    """
    Factory function to get the appropriate TTS provider.

    Returns:
        TTS provider instance based on configuration

    Priority:
    1. Google Cloud TTS if configured
    2. Mock provider for development
    """
    use_mock = getattr(settings, 'TTS_USE_MOCK', False)

    if use_mock:
        logger.info("Using mock TTS provider (development mode)")
        return MockTTSProvider()

    # Try Google Cloud TTS
    provider = GoogleTTSProvider()
    if provider.is_available:
        return provider

    # Fall back to local offline TTS if available
    local_provider = LocalOfflineTTSProvider()
    if local_provider.is_available:
        logger.info("Using local offline TTS provider")
        return local_provider

    # Fall back to mock if Google TTS not available
    logger.warning(
        "No real TTS provider available. Falling back to mock provider. "
        "Set GOOGLE_APPLICATION_CREDENTIALS or install espeak-ng for real audio."
    )
    return MockTTSProvider()
