"""Answer a farmer's question from the knowledge base, using an optional LLM.

The flow for every question:
1. Retrieve the passages closest to the question (retriever.py).
2. Send the passages, the farmer's latest scan or crop result (if any)
   and the question, with instructions to answer only from the passages.
3. Return the answer with the names of the documents it came from.

Without an API key the assistant still works in a reduced way: it returns the
retrieved passages themselves, so the farmer gets the relevant text even
though nothing rewrites it into a direct answer.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from . import retriever

load_dotenv()  # reads chatbot provider settings from the project .env file

MODEL = os.environ.get("KISAN_CHAT_MODEL", "claude-opus-5-5")
MAX_HISTORY_TURNS = 8      # earlier turns are dropped to keep requests small
MAX_MESSAGE_CHARS = 2000
PASSAGE_SCORE_MARGIN = 0.10  # in passages mode, how far below the best match a passage may score

HELPLINE = "1800-180-1551"

SYSTEM_PROMPT = f"""You are the farming assistant inside Kisan Sahayak, an app used by farmers in India. \
Many of the people you talk to farm a few acres, read at a basic level, and will act on what you say \
with their own money and their own crop, so being correct matters more than being complete.

Each question arrives with reference passages taken from the app's knowledge base, and sometimes with \
the result of a leaf scan or crop recommendation the farmer has just received in the app.

Answer from the reference passages and the app result. If they do not contain the answer, say plainly \
that you do not have that information, and suggest asking the local Krishi Vigyan Kendra (KVK) or calling \
the Kisan Call Centre on {HELPLINE} (toll-free). Do not fill the gap from general knowledge: a wrong \
product, dose or scheme detail can cost a farmer a harvest or a payment, and they have no easy way to \
check what you tell them. For the same reason, give a pesticide dose only if a passage states it; \
otherwise tell them to follow the product label.

If the app result is marked as low confidence, tell the farmer not to rely on it and to have the plant \
checked by the KVK before treating the crop.

Write the way a helpful extension worker would talk: short sentences, everyday words, the most important \
action first. Three to six sentences is usually enough; use a short numbered list only when giving steps \
in order. Your reply is shown as plain text and may be read aloud, so do not use headings, bold, tables \
or other formatting marks.

Reply in the language named in the message. For Hindi, write in Devanagari script using words a farmer \
would use, and keep product names, scheme names and numbers as they are."""


class AssistantUnavailable(Exception):
    """An LLM could not be reached or refused; the caller falls back to passages."""


def ai_available() -> bool:
    """True when either supported answer generation provider is configured."""
    provider = os.environ.get("KISAN_CHAT_PROVIDER", "auto").lower()
    has_claude = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    has_groq = bool(os.environ.get("GROQ_API_KEY"))
    if provider == "groq":
        return has_groq
    if provider == "claude":
        return has_claude
    return has_groq or has_claude


def describe_context(context: dict | None) -> str:
    """Turn the farmer's latest app result into a sentence the assistant can use."""
    if not context:
        return ""
    if context.get("type") == "disease":
        confidence = round(float(context.get("confidence", 0)) * 100)
        condition = "a healthy leaf" if context.get("healthy") else context.get("condition", "an unknown condition")
        note = " This result is LOW CONFIDENCE." if context.get("low_confidence") else ""
        return (f"Leaf scan result: crop {context.get('crop', 'unknown')}, {condition}, "
                f"model confidence {confidence}%.{note}")
    if context.get("type") == "crop":
        confidence = round(float(context.get("confidence", 0)) * 100)
        note = " This result is LOW CONFIDENCE." if context.get("low_confidence") else ""
        values = context.get("inputs") or {}
        given = ", ".join(f"{name} {value}" for name, value in values.items())
        return (f"Crop recommendation result: {context.get('crop', 'unknown')}, model confidence {confidence}%."
                f"{note} Values entered: {given}.")
    return ""


def retrieval_query(message: str, context: dict | None) -> str:
    """What to search for: the question, plus the crop and disease it is probably about."""
    if context and context.get("type") == "disease" and not context.get("healthy"):
        return f"{message} {context.get('crop', '')} {context.get('condition', '')}".strip()
    if context and context.get("type") == "crop":
        return f"{message} {context.get('crop', '')}".strip()
    return message


def build_user_turn(message: str, passages: list[dict], context: dict | None, language: str) -> str:
    if passages:
        references = "\n\n".join(
            f'<passage document="{p["title"]}" section="{p["section"]}">\n{p["text"]}\n</passage>' for p in passages)
    else:
        references = "(no passage in the knowledge base matched this question)"
    app_result = describe_context(context) or "(none)"
    language_name = "Hindi" if language == "hi" else "English"
    return (f"<reference_passages>\n{references}\n</reference_passages>\n\n"
            f"<app_result>\n{app_result}\n</app_result>\n\n"
            f"Reply language: {language_name}\n\n"
            f"Farmer's question: {message}")


def _conversation(message: str, passages: list[dict], context: dict | None, language: str,
                  history: list[dict]) -> list[dict]:
    turns = [{"role": turn["role"], "content": str(turn["content"])[:MAX_MESSAGE_CHARS]}
             for turn in history[-MAX_HISTORY_TURNS:]
             if turn.get("role") in ("user", "assistant") and turn.get("content")]
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    turns.append({"role": "user", "content": build_user_turn(message, passages, context, language)})
    return turns


def ask_claude(message: str, passages: list[dict], context: dict | None, language: str,
               history: list[dict]) -> str:
    import anthropic

    turns = _conversation(message, passages, context, language, history)

    try:
        response = anthropic.Anthropic().messages.create(
            model=MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=turns,
        )
    except anthropic.AuthenticationError as error:
        raise AssistantUnavailable("The API key was rejected.") from error
    except anthropic.RateLimitError as error:
        raise AssistantUnavailable("The assistant is busy. Try again in a minute.") from error
    except anthropic.APIStatusError as error:
        raise AssistantUnavailable(f"The assistant returned an error ({error.status_code}).") from error
    except anthropic.APIConnectionError as error:
        raise AssistantUnavailable("The assistant could not be reached. Check the internet connection.") from error
    except anthropic.AnthropicError as error:  # e.g. no credentials configured
        raise AssistantUnavailable(str(error)) from error

    if response.stop_reason == "refusal":
        raise AssistantUnavailable("The assistant declined to answer this question.")
    answer = "".join(block.text for block in response.content if block.type == "text").strip()
    if not answer:
        raise AssistantUnavailable("The assistant returned an empty answer.")
    return answer


def ask_groq(message: str, passages: list[dict], context: dict | None, language: str,
             history: list[dict]) -> str:
    """Generate a concise answer using Groq's free developer tier."""
    from openai import OpenAI, APIConnectionError, APIStatusError, RateLimitError, AuthenticationError

    turns = [{"role": "system", "content": SYSTEM_PROMPT},
             *_conversation(message, passages, context, language, history)]
    try:
        response = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        ).chat.completions.create(
            model=os.environ.get("KISAN_GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=turns,
            max_tokens=1200,
            temperature=0.2,
        )
    except AuthenticationError as error:
        raise AssistantUnavailable("The Groq API key was rejected.") from error
    except RateLimitError as error:
        raise AssistantUnavailable("The free assistant is busy. Try again in a minute.") from error
    except APIStatusError as error:
        raise AssistantUnavailable(f"The assistant returned an error ({error.status_code}).") from error
    except APIConnectionError as error:
        raise AssistantUnavailable("The assistant could not be reached. Check the internet connection.") from error
    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise AssistantUnavailable("The assistant returned an empty answer.")
    return answer


def ask_llm(message: str, passages: list[dict], context: dict | None, language: str,
            history: list[dict]) -> str:
    """Use configured provider; in auto mode prefer Groq, then Claude."""
    provider = os.environ.get("KISAN_CHAT_PROVIDER", "auto").lower()
    if provider == "groq" or (provider == "auto" and os.environ.get("GROQ_API_KEY")):
        return ask_groq(message, passages, context, language, history)
    if provider == "claude" or (provider == "auto" and (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))):
        return ask_claude(message, passages, context, language, history)
    raise AssistantUnavailable("No chatbot provider is configured.")


def sources_of(passages: list[dict]) -> list[dict]:
    """The distinct documents the passages came from, in order of relevance."""
    seen, sources = set(), []
    for passage in passages:
        key = (passage["title"], passage["section"])
        if key not in seen:
            seen.add(key)
            sources.append({"title": passage["title"], "section": passage["section"]})
    return sources


def answer(message: str, language: str = "en", context: dict | None = None,
           history: list[dict] | None = None) -> dict:
    """Answer one question.

    mode is "ai" (an LLM wrote the answer), "passages" (no key or LLM failed:
    the matching passages are returned as they are) or "no_match" (nothing relevant found
    and no AI to say so in the farmer's language).
    """
    message = message.strip()[:MAX_MESSAGE_CHARS]
    passages = retriever.search(retrieval_query(message, context))
    result = {"sources": sources_of(passages), "passages": [], "notice": ""}

    if ai_available():
        try:
            return {**result, "mode": "ai", "answer": ask_llm(message, passages, context, language, history or [])}
        except AssistantUnavailable as error:
            result["notice"] = str(error)

    if not passages:
        return {**result, "mode": "no_match", "answer": ""}
    # Show only passages about as relevant as the best one, so loosely related text is left out.
    close = [p for p in passages if p["score"] >= passages[0]["score"] - PASSAGE_SCORE_MARGIN][:3]
    return {**result, "mode": "passages", "answer": "", "sources": sources_of(close),
            "passages": [{"title": p["title"], "section": p["section"], "text": p["text"]} for p in close]}
