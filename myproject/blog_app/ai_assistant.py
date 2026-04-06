import os
import logging

from django.conf import settings

# Try OpenAI first (for Groq), fall back to anthropic if needed
try:
    from openai import OpenAI, APIConnectionError, RateLimitError, APIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_ai_response(action, content, title=None):
    """
    Get AI response using either Groq (OpenAI-compatible) or Anthropic.

    Priority:
    1. If GROQ_API_KEY is set → use Groq (Llama 3.3 70B) - FREE & FAST
    2. If ANTHROPIC_API_KEY is set → use Anthropic Claude
    3. Raise error if neither is available
    """

    prompts = {
        "improve": "You are a professional blog editor. Improve the grammar, tone, and flow of the given blog content. Return only the improved content, nothing else.",
        "summarize": "You are a blog summarizer. Write a short 2-3 sentence summary of the given blog content. Return only the summary, nothing else.",
        "generate": "You are a professional blog writer. Write a full detailed blog post based on the given title or prompt. Return only the blog content, nothing else.",
        "expand": "You are a professional blog editor. Expand and elaborate on the given blog content by adding more details, examples, explanations, and supporting points while maintaining the original tone. Make it more comprehensive and informative. Return only the expanded content, nothing else.",
    }

    if action not in prompts:
        raise ValueError("Invalid action")

    user_content = title or content

    # Try Groq first (free & fast)
    if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY and OPENAI_AVAILABLE:
        try:
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": prompts[action]},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            # Fall through to try Anthropic if available

    # Fallback to Anthropic if Groq not configured or failed
    if hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY and ANTHROPIC_AVAILABLE:
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=prompts[action],
                messages=[
                    {
                        "role": "user",
                        "content": user_content,
                    }
                ],
            )

            parts = []
            for block in response.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)

            return "".join(parts).strip()

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    # No provider available
    raise RuntimeError(
        "AI service is not configured. Please set GROQ_API_KEY or ANTHROPIC_API_KEY in .env file."
    )
