"""
Audio Generation Service

Core business logic for transforming blog content into audio.
Coordinates between AI prompts, TTS providers, and data models.
"""
import json
import logging
from urllib import error as urllib_error
from urllib import request as urllib_request
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from .models import AudioFile, AudioQuestion
from .prompts import get_full_prompt, QUESTION_PROMPTS, REEXPLAIN_PROMPTS
from .tts_provider import get_tts_provider, AudioResult, BaseTTSProvider

logger = logging.getLogger(__name__)


@dataclass
class AudioGenerationConfig:
    """Configuration for audio generation."""
    mode: str = 'explain'
    language: str = 'en'
    understanding_level: str = 'intermediate'
    mood: str = 'educational'
    speaking_rate: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'mode': self.mode,
            'language': self.language,
            'understanding_level': self.understanding_level,
            'mood': self.mood,
            'speaking_rate': self.speaking_rate,
        }


@dataclass
class GeneratedContent:
    """Container for AI-generated content."""
    transcript: str
    summary: str
    sections: Dict[str, Dict[str, float]] = field(default_factory=dict)
    suggestions: List[Dict[str, str]] = field(default_factory=list)
    questions: List[Dict[str, Any]] = field(default_factory=list)
    file_extension: str = 'mp3'
    content_type: str = 'audio/mpeg'


class AudioGenerationService:
    """
    Main service for generating audio from blog content.

    This service coordinates:
    1. Content transformation via AI (Anthropic Claude)
    2. Text-to-speech conversion (Google Cloud TTS)
    3. Section extraction and timing
    4. Summary and suggestion generation
    """

    def __init__(self, tts_provider: Optional[BaseTTSProvider] = None):
        """
        Initialize the audio generation service.

        Args:
            tts_provider: Optional TTS provider instance. Uses default if not provided.
        """
        self.tts_provider = tts_provider or get_tts_provider()
        self._anthropic_api_key = (getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
        self._groq_api_key = (getattr(settings, "GROQ_API_KEY", "") or "").strip()

    def _create_ai_message(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Call Anthropic Messages API directly.

        Using an explicit HTTP request avoids SDK auth auto-resolution conflicts
        when both Authorization and X-Api-Key headers are present in the runtime.
        """
        if self._anthropic_api_key:
            return self._create_anthropic_message(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )

        if self._groq_api_key:
            logger.info("ANTHROPIC_API_KEY not set. Falling back to Groq for audio content generation.")
            return self._create_groq_message(
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )

        raise RuntimeError("No AI provider configured. Set ANTHROPIC_API_KEY or GROQ_API_KEY.")

    def _create_anthropic_message(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Call Anthropic Messages API directly."""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        return self._post_json(
            url="https://api.anthropic.com/v1/messages",
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._anthropic_api_key,
                "anthropic-version": "2023-06-01",
            },
            provider_name="Anthropic",
        )

    def _create_groq_message(
        self,
        *,
        max_tokens: int,
        system: str,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Call Groq Chat Completions API directly using the existing GROQ_API_KEY."""
        groq_messages = [{"role": "system", "content": system}, *messages]
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": groq_messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        response = self._post_json(
            url="https://api.groq.com/openai/v1/chat/completions",
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._groq_api_key}",
            },
            provider_name="Groq",
        )

        content = ""
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Invalid Groq API response: %s", response)
            raise RuntimeError("Groq API returned an unexpected response format.") from exc

        return {
            "content": [
                {
                    "type": "text",
                    "text": content or "",
                }
            ]
        }

    def _post_json(
        self,
        *,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        provider_name: str,
    ) -> Dict[str, Any]:
        """POST JSON to an AI provider and return parsed JSON."""
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            url=url,
            data=body,
            method="POST",
            headers=headers,
        )

        try:
            with urllib_request.urlopen(req, timeout=120) as response:
                response_body = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            logger.error("%s API HTTP error %s: %s", provider_name, exc.code, error_body)
            raise RuntimeError(
                f"{provider_name} API request failed with status {exc.code}: {error_body}"
            ) from exc
        except urllib_error.URLError as exc:
            logger.error("%s API network error: %s", provider_name, exc)
            raise RuntimeError(f"{provider_name} API network error: {exc}") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            logger.error("Invalid %s API response: %s", provider_name, response_body)
            raise RuntimeError(f"{provider_name} API returned invalid JSON.") from exc

    def generate_audio(
        self,
        blog_content: str,
        blog_title: str,
        config: AudioGenerationConfig,
    ) -> tuple[bytes, GeneratedContent]:
        """
        Generate audio from blog content.

        This is the main entry point that orchestrates the entire pipeline:
        1. Transform blog content to audio script via AI
        2. Generate audio via TTS
        3. Extract sections and metadata
        4. Generate summary and suggestions

        Args:
            blog_content: The blog text content
            blog_title: The blog title
            config: Audio generation configuration

        Returns:
            Tuple of (audio_bytes, GeneratedContent)

        Raises:
            RuntimeError: If audio generation fails
        """
        logger.info(f"Starting audio generation: mode={config.mode}, lang={config.language}")

        try:
            # Step 1: Transform content to audio script
            generated_content = self._transform_content(
                blog_content=blog_content,
                blog_title=blog_title,
                config=config,
            )

            # Step 2: Generate audio via TTS
            audio_result = self._generate_tts_audio(
                text=generated_content.transcript,
                config=config,
            )

            # Step 3: Calculate sections based on duration
            generated_content.sections = self._calculate_sections(
                transcript=generated_content.transcript,
                duration_seconds=audio_result.duration_seconds,
            )
            generated_content.file_extension = audio_result.file_extension
            generated_content.content_type = audio_result.content_type

            logger.info(f"Audio generation complete: {audio_result.duration_seconds}s")

            return audio_result.audio_bytes, generated_content

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            raise RuntimeError(f"Failed to generate audio: {str(e)}")

    def _transform_content(
        self,
        blog_content: str,
        blog_title: str,
        config: AudioGenerationConfig,
    ) -> GeneratedContent:
        """
        Transform blog content into audio-ready script using AI.

        Args:
            blog_content: Raw blog content
            blog_title: Blog title
            config: Generation configuration

        Returns:
            GeneratedContent with transcript, summary, and metadata
        """
        prompt_config = get_full_prompt(
            mode=config.mode,
            language=config.language,
            understanding_level=config.understanding_level,
            mood=config.mood,
        )

        # Prepare the user message with blog content
        user_message = f"""Blog Title: {blog_title}

Blog Content:
{blog_content}

Please transform this blog content into an engaging audio script following the system instructions.
Include clear section markers for: [INTRO], [MAIN], [CONCLUSION]
End with a brief summary of key takeaways."""

        try:
            response = self._create_ai_message(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=prompt_config['full_system_prompt'],
                messages=[{"role": "user", "content": user_message}],
            )

            # Extract text from response
            transcript = self._extract_text_from_response(response)

            # Generate summary and suggestions
            summary = self._generate_summary(transcript, prompt_config)
            suggestions = self._generate_suggestions(blog_content, blog_title)

            return GeneratedContent(
                transcript=transcript,
                summary=summary,
                sections={},  # Calculated later after TTS
                suggestions=suggestions,
            )

        except Exception as e:
            logger.warning(
                "Content transformation failed, using direct blog-to-audio fallback: %s",
                e,
            )
            return self._build_fallback_content(
                blog_content=blog_content,
                blog_title=blog_title,
                config=config,
            )

    def _build_fallback_content(
        self,
        *,
        blog_content: str,
        blog_title: str,
        config: AudioGenerationConfig,
    ) -> GeneratedContent:
        """
        Build a simple audio transcript directly from the blog content.

        This keeps audio generation usable even when an external AI provider
        is unavailable or blocked.
        """
        cleaned_content = self._normalize_blog_text(blog_content)
        paragraphs = [p for p in cleaned_content.split("\n\n") if p.strip()]

        if not paragraphs:
            paragraphs = [f"This audio version covers the blog titled {blog_title}."]

        intro = (
            f"Welcome. This is the {config.mode} audio version of {blog_title}. "
            f"We'll walk through the key ideas in a {config.mood} style for a "
            f"{config.understanding_level} audience."
        )

        if len(paragraphs) == 1:
            main_body = paragraphs[0]
            ending_source = paragraphs[0]
        else:
            main_body = "\n\n".join(paragraphs[:-1])
            ending_source = paragraphs[-1]

        conclusion = (
            "To wrap up, the main takeaway is: "
            f"{self._truncate_sentence(ending_source, 240)}"
        )

        transcript = "\n\n".join([
            f"[INTRO] {intro}",
            f"[MAIN] {main_body}",
            f"[CONCLUSION] {conclusion}",
        ])

        return GeneratedContent(
            transcript=transcript,
            summary=self._generate_fallback_summary(blog_title, paragraphs),
            sections={},
            suggestions=[{
                "recommended_mode": "summary",
                "recommended_level": config.understanding_level,
                "reason": "Generated from the original blog content without AI rewriting.",
            }],
        )

    def _normalize_blog_text(self, blog_content: str) -> str:
        """Normalize blog text for direct narration fallback."""
        content = (blog_content or "").replace("\r\n", "\n")
        lines = [line.strip() for line in content.split("\n")]

        normalized_lines = []
        blank_pending = False
        for line in lines:
            if not line:
                if normalized_lines:
                    blank_pending = True
                continue

            if blank_pending:
                normalized_lines.append("")
                blank_pending = False

            if line.startswith("#"):
                line = line.lstrip("#").strip()
            elif line[:2] in {"- ", "* "}:
                line = line[2:].strip()

            normalized_lines.append(line)

        return "\n".join(normalized_lines).strip()

    def _truncate_sentence(self, text: str, limit: int) -> str:
        """Trim text to a readable sentence-like snippet."""
        text = " ".join((text or "").split())
        if len(text) <= limit:
            return text
        shortened = text[:limit].rsplit(" ", 1)[0].strip()
        return f"{shortened}..."

    def _generate_fallback_summary(self, blog_title: str, paragraphs: List[str]) -> str:
        """Generate a simple summary without using an AI provider."""
        if not paragraphs:
            return f"Audio overview of {blog_title}."

        first_point = self._truncate_sentence(paragraphs[0], 180)
        if len(paragraphs) == 1:
            return f"This audio covers {blog_title}. {first_point}"

        last_point = self._truncate_sentence(paragraphs[-1], 180)
        return f"This audio covers {blog_title}. It starts with {first_point} and closes with {last_point}"

    def _extract_text_from_response(self, response) -> str:
        """Extract text content from Anthropic API response."""
        parts = []

        if isinstance(response, dict):
            for block in response.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
            return "".join(parts).strip()

        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts).strip()

    def _generate_summary(
        self,
        transcript: str,
        prompt_config: Dict[str, str]
    ) -> str:
        """Generate a brief summary of the audio content."""
        try:
            response = self._create_ai_message(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system="You are a concise summarizer. Create a brief, engaging summary in 2-3 sentences.",
                messages=[{
                    "role": "user",
                    "content": f"Summarize this audio script in 2-3 sentences:\n\n{transcript[:2000]}"
                }],
            )
            return self._extract_text_from_response(response)
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return "Audio content based on the blog."

    def _generate_suggestions(
        self,
        blog_content: str,
        blog_title: str,
    ) -> List[Dict[str, str]]:
        """Generate suggestions for other audio modes/languages."""
        try:
            response = self._create_ai_message(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=QUESTION_PROMPTS['system_prompt'],
                messages=[{
                    "role": "user",
                    "content": f"""Based on this blog content, suggest the best audio mode for this content.

Title: {blog_title}
Content: {blog_content[:1500]}

Respond in JSON format:
{{
    "recommended_mode": "conversation|explain|summary",
    "recommended_level": "beginner|intermediate|expert",
    "reason": "Brief explanation"
}}"""
                }],
            )

            result_text = self._extract_text_from_response(response)

            # Try to parse as JSON
            try:
                # Find JSON in response
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = result_text[start:end]
                    suggestion = json.loads(json_str)
                    return [suggestion]
            except json.JSONDecodeError:
                pass

            return [{
                "recommended_mode": "explain",
                "recommended_level": "intermediate",
                "reason": "Default recommendation for educational content."
            }]

        except Exception as e:
            logger.warning(f"Suggestion generation failed: {e}")
            return [{
                "recommended_mode": "explain",
                "recommended_level": "intermediate",
                "reason": "Default recommendation"
            }]

    def _generate_tts_audio(
        self,
        text: str,
        config: AudioGenerationConfig,
    ) -> AudioResult:
        """
        Generate audio using TTS provider.

        Handles long texts by splitting if necessary.

        Args:
            text: Text to convert to audio
            config: Audio configuration

        Returns:
            AudioResult with audio bytes and metadata
        """
        # Check if text needs splitting
        chunks = self.tts_provider.split_text_for_tts(text, max_chars=4500)

        if len(chunks) == 1:
            # Single chunk, generate directly
            return self.tts_provider.generate_audio(
                text=text,
                language=config.language,
                voice_style=config.mood,
                speaking_rate=config.speaking_rate,
            )

        # Multiple chunks - need to concatenate
        logger.info(f"Splitting text into {len(chunks)} chunks for TTS")

        # For simplicity, we'll process the first chunk
        # In production, you'd concatenate all chunks or use SSML with breaks
        # This is a simplified approach for the MVP

        full_audio = self.tts_provider.generate_audio(
            text=text,
            language=config.language,
            voice_style=config.mood,
            speaking_rate=config.speaking_rate,
        )

        return full_audio

    def _calculate_sections(
        self,
        transcript: str,
        duration_seconds: int,
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate section timestamps based on transcript markers.

        Looks for [INTRO], [MAIN], [CONCLUSION] markers in transcript
        and calculates timing based on character positions.

        Args:
            transcript: The transcript with section markers
            duration_seconds: Total audio duration

        Returns:
            Dictionary of section timestamps
        """
        sections = {}

        # Find marker positions
        intro_pos = transcript.find('[INTRO]')
        main_pos = transcript.find('[MAIN]')
        conclusion_pos = transcript.find('[CONCLUSION]')

        # Clean transcript length (without markers)
        clean_transcript = transcript.replace('[INTRO]', '').replace('[MAIN]', '').replace('[CONCLUSION]', '')
        total_chars = len(clean_transcript)

        if total_chars == 0:
            return {
                'intro': {'start': 0, 'end': duration_seconds * 0.15},
                'main': {'start': duration_seconds * 0.15, 'end': duration_seconds * 0.85},
                'conclusion': {'start': duration_seconds * 0.85, 'end': duration_seconds},
            }

        # Calculate positions proportionally
        def get_time_for_position(pos: int) -> float:
            """Calculate time based on character position."""
            # Adjust for markers in the count
            chars_before = transcript[:pos]
            for marker in ['[INTRO]', '[MAIN]', '[CONCLUSION]']:
                chars_before = chars_before.replace(marker, '')
            proportion = len(chars_before) / total_chars
            return proportion * duration_seconds

        # Determine section boundaries
        if intro_pos != -1 and main_pos != -1 and conclusion_pos != -1:
            sections = {
                'intro': {
                    'start': 0,
                    'end': get_time_for_position(main_pos),
                },
                'main': {
                    'start': get_time_for_position(main_pos),
                    'end': get_time_for_position(conclusion_pos),
                },
                'conclusion': {
                    'start': get_time_for_position(conclusion_pos),
                    'end': duration_seconds,
                },
            }
        else:
            # Default sections if markers not found
            # Intro: 15%, Main: 70%, Conclusion: 15%
            sections = {
                'intro': {'start': 0, 'end': duration_seconds * 0.15},
                'main': {'start': duration_seconds * 0.15, 'end': duration_seconds * 0.85},
                'conclusion': {'start': duration_seconds * 0.85, 'end': duration_seconds},
            }

        return sections

    def generate_questions(
        self,
        transcript: str,
        num_questions: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehension questions based on audio transcript.

        Args:
            transcript: The audio transcript
            num_questions: Number of questions to generate

        Returns:
            List of question dictionaries
        """
        try:
            response = self._create_ai_message(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=QUESTION_PROMPTS['system_prompt'],
                messages=[{
                    "role": "user",
                    "content": f"""Generate {num_questions} comprehension questions based on this audio transcript.

Transcript:
{transcript[:3000]}

Format your response as JSON:
{{
    "questions": [
        {{
            "question": "Question text?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A",
            "explanation": "Why this is correct...",
            "type": "recall|understand|apply|analyze"
        }}
    ]
}}"""
                }],
            )

            result_text = self._extract_text_from_response(response)

            # Parse JSON from response
            try:
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = result_text[start:end]
                    data = json.loads(json_str)
                    return data.get('questions', [])
            except json.JSONDecodeError:
                pass

            return []

        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            return []

    def reexplain_section(
        self,
        transcript: str,
        section: str,
        blog_content: str,
        config: AudioGenerationConfig,
    ) -> str:
        """
        Generate a re-explanation of a specific section.

        Args:
            transcript: The original transcript
            section: Section to re-explain (intro, main, conclusion)
            blog_content: Original blog content for context
            config: Audio configuration

        Returns:
            Re-explained text for the section
        """
        # Extract section content from markers
        section_content = self._extract_section(transcript, section)
        if not section_content:
            section_content = "Section content not found."

        prompt_config = get_full_prompt(
            mode=config.mode,
            language=config.language,
            understanding_level=config.understanding_level,
            mood=config.mood,
        )

        reexplain_prompt = REEXPLAIN_PROMPTS['system_prompt'].format(
            section_name=REEXPLAIN_PROMPTS['sections'].get(section, section),
            section_content=section_content,
        )

        try:
            response = self._create_ai_message(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=f"{prompt_config['full_system_prompt']}\n\n{reexplain_prompt}",
                messages=[{
                    "role": "user",
                    "content": f"""The listener wants you to re-explain this section in more detail.

Original blog for context:
{blog_content[:2000]}

Please provide a clearer, more detailed explanation of this section, as if teaching it to someone who needs extra help understanding."""
                }],
            )

            return self._extract_text_from_response(response)

        except Exception as e:
            logger.error(f"Re-explain generation failed: {e}")
            raise RuntimeError(f"Failed to generate re-explanation: {str(e)}")

    def _extract_section(self, transcript: str, section: str) -> str:
        """Extract content between section markers."""
        markers = ['[INTRO]', '[MAIN]', '[CONCLUSION]']

        if section.lower() == 'intro':
            start = transcript.find('[INTRO]')
            end = transcript.find('[MAIN]')
            if start != -1 and end != -1:
                return transcript[start:end].replace('[INTRO]', '').strip()
        elif section.lower() == 'main':
            start = transcript.find('[MAIN]')
            end = transcript.find('[CONCLUSION]')
            if start != -1 and end != -1:
                return transcript[start:end].replace('[MAIN]', '').strip()
        elif section.lower() == 'conclusion':
            start = transcript.find('[CONCLUSION]')
            if start != -1:
                return transcript[start:].replace('[CONCLUSION]', '').strip()

        return ""


# Singleton instance for convenience
_service_instance = None

def get_audio_service() -> AudioGenerationService:
    """Get or create the audio generation service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AudioGenerationService()
    return _service_instance
