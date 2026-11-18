"""Generate the content package from a transcript with Claude, OpenAI or Gemini."""

from __future__ import annotations

import json

from pydantic import ValidationError

from .config import Settings
from .models import ContentPackage

SYSTEM_PROMPT = """You are the content editor for a YouTube channel. After each episode is recorded you \
receive its transcript and prepare everything the team needs to publish and promote it: titles to test, \
the video description, scripts for three shorts, a LinkedIn post and an X thread.

The audience for these pieces has not seen the episode, so each one must stand on its own, and its job \
is to make a specific person want to watch.

What makes this work good:
- It is built from what was actually said. The numbers, names and turns of phrase in the transcript are \
the raw material; a real figure or a real quote does more than any adjective. Never add a fact, statistic \
or quote that is not in the transcript, because the creator will be the one held to it.
- Titles earn the click honestly. Lead with the most surprising true thing in the episode and make sure \
the video delivers it. Offer five different angles, not five rewordings of one.
- The description has three parts: a summary that uses the words someone would type into search for this \
topic, then the chapters, then four or five key points as a list. Use timestamps only when the transcript \
contains them, and copy them from it; if it has none, list the chapters without times rather than estimating.
- Each short is one moment from the episode that works with no context: a hook in the first sentence, \
the story or point, and a closing line. Write it as the words to be spoken, 80 to 110 words, so it runs \
30 to 45 seconds.
- The LinkedIn post and the X thread are in plain language and give the insight away in the post itself \
rather than teasing it.

Whose voice to write in: everything is published by the channel. When the episode is an interview, the \
host (the person asking the questions) is "I", and the guest is named and described in the third person, \
in titles, shorts and posts alike. Writing "we spent $1,800 on ads" when the guest said it would put the \
guest's story in the host's mouth. When a single creator speaks throughout, that creator is "I".

Write numbers the way they appear on screen ($40,000, 9%), and keep comparisons exact: a drop from 9% to \
4% is "from 9% to 4%", not "cut in half".

Write the way a sharp human editor does: concrete and plain. Leave out hashtag clusters, emoji, \
exclamation marks and stock openers such as "In today's fast-paced world" or "Here's the thing"."""

# Current Claude models that accept the server-side refusal fallback (see README).
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_FALLBACK_MODELS = frozenset(
    {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-fable-5-1"}
)


class GenerationError(Exception):
    """A generation failure, with a message safe to show the user."""


def _generate_anthropic(settings: Settings, transcript: str) -> ContentPackage:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    request = dict(
        model=settings.anthropic_model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Episode transcript:\n\n{transcript}"}],
        output_format=ContentPackage,
    )
    try:
        if settings.anthropic_model in _FALLBACK_MODELS:
            response = client.beta.messages.parse(**request, betas=[_FALLBACK_BETA], fallbacks="default")
        else:
            response = client.messages.parse(**request)
    except anthropic.AuthenticationError as exc:
        raise GenerationError("The Anthropic API key was rejected. Check ANTHROPIC_API_KEY in .env.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise GenerationError("This Anthropic API key is not allowed to use the selected model.") from exc
    except anthropic.NotFoundError as exc:
        raise GenerationError(f"Model '{settings.anthropic_model}' was not found. Check ANTHROPIC_MODEL in .env.") from exc
    except anthropic.RateLimitError as exc:
        raise GenerationError("Rate limit reached. Wait a moment and try again.") from exc
    except anthropic.BadRequestError as exc:
        raise GenerationError(f"The request was rejected, possibly because the transcript is too long: {exc.message}") from exc
    except anthropic.APIStatusError as exc:
        raise GenerationError(f"The AI service returned an error ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise GenerationError("Could not reach the AI service. Check your internet connection.") from exc

    if response.stop_reason == "refusal":
        raise GenerationError("The AI model declined to process this transcript.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise GenerationError("The AI model did not finish the content package. Try again.")
    return response.parsed_output


def _generate_openai(settings: Settings, transcript: str) -> ContentPackage:
    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)
    schema = json.dumps(ContentPackage.model_json_schema())
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nReply with one JSON object matching this schema:\n{schema}"},
                {"role": "user", "content": f"Episode transcript:\n\n{transcript}"},
            ],
        )
        return ContentPackage.model_validate_json(response.choices[0].message.content or "")
    except ValidationError as exc:
        raise GenerationError("The AI model returned the package in an unexpected shape. Try again.") from exc
    except openai.AuthenticationError as exc:
        raise GenerationError("The OpenAI API key was rejected. Check OPENAI_API_KEY in .env.") from exc
    except openai.NotFoundError as exc:
        raise GenerationError(f"Model '{settings.openai_model}' was not found. Check OPENAI_MODEL in .env.") from exc
    except openai.RateLimitError as exc:
        raise GenerationError("Rate limit or credit limit reached. Try again later.") from exc
    except openai.APIStatusError as exc:
        raise GenerationError(f"The AI service returned an error ({exc.status_code}).") from exc
    except openai.APIConnectionError as exc:
        raise GenerationError("Could not reach the AI service. Check your internet connection.") from exc


def _generate_gemini(settings: Settings, transcript: str) -> ContentPackage:
    from google import genai
    from google.genai import errors, types

    # Gemini returns 503 when a model is busy, which is common on the free tier, so retry a few times.
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=4, initial_delay=2.0)),
    )
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"Episode transcript:\n\n{transcript}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_json_schema=ContentPackage.model_json_schema(),
            ),
        )
        return ContentPackage.model_validate_json(response.text or "")
    except ValidationError as exc:
        raise GenerationError("The AI model returned the package in an unexpected shape. Try again.") from exc
    except errors.APIError as exc:
        detail = str(getattr(exc, "message", "") or exc)
        if exc.code in (401, 403) or "API key" in detail:
            raise GenerationError("The Gemini API key was rejected. Check GEMINI_API_KEY in .env.") from exc
        if exc.code == 404:
            raise GenerationError(f"Model '{settings.gemini_model}' was not found. Check GEMINI_MODEL in .env.") from exc
        if exc.code == 429:
            raise GenerationError("The Gemini usage limit was reached (the free tier allows a few requests per minute). Wait a minute and try again.") from exc
        if exc.code in (500, 502, 503, 504):
            raise GenerationError("Gemini is overloaded right now. Wait a minute and try again.") from exc
        raise GenerationError(f"Gemini returned an error ({exc.code}): {detail}") from exc
    except Exception as exc:  # noqa: BLE001 - the SDK does not wrap network failures in its own error type
        raise GenerationError(f"Could not reach Gemini. Check your internet connection. ({type(exc).__name__})") from exc


def generate_package(settings: Settings, transcript: str) -> ContentPackage:
    """Generate the full package for one transcript. Raises GenerationError on failure."""
    if settings.provider == "anthropic":
        return _generate_anthropic(settings, transcript)
    if settings.provider == "openai":
        return _generate_openai(settings, transcript)
    if settings.provider == "gemini":
        return _generate_gemini(settings, transcript)
    raise GenerationError("No AI provider is configured. Add an API key to .env.")
