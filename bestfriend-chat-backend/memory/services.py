# memory/services.py
import os
import asyncio
from django.utils import timezone
from openai import OpenAI
from chat.utils_openai import extract_text_from_response


# Configuration
SUMMARIZE_AFTER_MESSAGES = int(os.getenv("SUMMARIZE_AFTER_MESSAGES", "25"))
MAX_RAW_MESSAGES_KEEP = int(os.getenv("MAX_RAW_MESSAGES_KEEP", "200"))
MEMORY_MODEL = os.getenv("MEMORY_MODEL", "gpt-5-nano")
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "gpt-5-nano")


def get_client():
    """Create OpenAI client (blocking)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


# -------------------------
# Synchronous DB helpers
# -------------------------'


    """
    Safely extract assistant text from a Responses API response.

    Looks for the first output item of type 'message', then returns
    its first content.text. Falls back to string(resp) if needed.
    """
    try:
        # New Responses API: resp.output is a list of items
        # We want the one with type == "message"
        for item in getattr(resp, "output", []) or []:
            if getattr(item, "type", None) == "message":
                content_list = getattr(item, "content", []) or []
                if content_list and hasattr(content_list[0], "text"):
                    return content_list[0].text

        # Fallback: try the last output item
        if getattr(resp, "output", None):
            last = resp.output[-1]
            content_list = getattr(last, "content", []) or []
            if content_list and hasattr(content_list[0], "text"):
                return content_list[0].text
    except Exception:
        pass

    # Last resort: stringified response
    return str(resp)

def get_or_create_user_memory_sync(external_id):
    from .models import UserMemory
    um, _ = UserMemory.objects.get_or_create(external_id=external_id)
    return um


def append_message_to_memory_sync(external_id, role, content, metadata=None):
    """
    Create a ConversationMessage and prune old ones.
    """
    from .models import ConversationMessage
    um = get_or_create_user_memory_sync(external_id)

    msg = ConversationMessage.objects.create(
        user_memory=um,
        role=role,
        content=content,
        metadata=metadata or {},
    )

    # prune older messages, keep newest MAX_RAW_MESSAGES_KEEP
    qs = ConversationMessage.objects.filter(user_memory=um).order_by('-created_at')
    if qs.count() > MAX_RAW_MESSAGES_KEEP:
        to_delete = qs[MAX_RAW_MESSAGES_KEEP:]
        ConversationMessage.objects.filter(id__in=[m.id for m in to_delete]).delete()

    return msg


def get_recent_messages_as_list_sync(external_id, limit=50):
    """
    Return list of dicts:
      [{"role": "...", "content": "..."}, ...]
    ordered from oldest to newest, limited to last `limit`.
    """
    from .models import ConversationMessage
    um = get_or_create_user_memory_sync(external_id)
    qs = ConversationMessage.objects.filter(user_memory=um).order_by('created_at')
    total = qs.count()
    if total > limit:
        qs = qs[total - limit:]
    return [{"role": m.role, "content": m.content} for m in qs]


def _summarize_memory_sync(external_id):
    """
    Read recent messages, summarize with OpenAI,
    store in ConversationSummary + UserMemory.facts.
    """
    from .models import ConversationMessage, ConversationSummary

    um = get_or_create_user_memory_sync(external_id)

    messages = ConversationMessage.objects.filter(user_memory=um).order_by('-created_at')[:SUMMARIZE_AFTER_MESSAGES]
    messages = list(reversed(messages))
    raw_text = "\n".join(f"{m.role}: {m.content}" for m in messages)

    prompt = (
        "Summarize the user's recent conversation into short bullet points suitable for long-term memory.\n\n"
        f"Conversation:\n{raw_text}\n\n"
        "Return a short JSON object with keys: 'profile_summary', 'important_facts', 'current_concerns'. "
        "Keep each field short."
    )

    client = get_client()
    resp = client.responses.create(
        model=MEMORY_MODEL,
        # input_text=prompt,
        input=prompt,
    )

    # extract summary text
    try:
        # summary_text = resp.output[0].content[0].text
        summary_text = extract_text_from_response(resp)
    except Exception:
        summary_text = str(resp)

    cs, _ = ConversationSummary.objects.get_or_create(user_memory=um)
    cs.summary_text = summary_text
    cs.last_updated = timezone.now()
    cs.save()

    # merge into facts
    try:
        import json
        parsed = json.loads(summary_text)
        if isinstance(parsed, dict):
            um.facts.update(parsed)
        else:
            um.facts.update({"summary": summary_text})
    except Exception:
        um.facts.update({"summary": summary_text})
    um.save()

    return cs


def _analyze_message_sync(external_id, text):
    """
    Analyze sentiment/topics of a message. Returns a dict.
    """
    prompt = (
        "Perform a short analysis of the following user message. Return a JSON object with fields:\n"
        "  - sentiment: one of {positive, neutral, negative}\n"
        "  - sentiment_score: a number between -1 and 1\n"
        "  - topics: array of short topic labels\n\n"
        f"Message: '''{text}'''"
    )

    client = get_client()
    resp = client.responses.create(
        model=ANALYSIS_MODEL,
        # input_text=prompt,
        input=prompt,
    )

    try:
        # out = resp.output[0].content[0].text
        out = extract_text_from_response(resp)
    except Exception:
        out = str(resp)

    try:
        import json
        parsed = json.loads(out)
        return parsed
    except Exception:
        return {"sentiment": "neutral", "sentiment_score": 0.0, "topics": []}


# -------------------------
# Async wrappers for use in async consumer
# -------------------------

async def append_message_to_memory(external_id, role, content, metadata=None):
    return await asyncio.to_thread(append_message_to_memory_sync, external_id, role, content, metadata)


async def get_recent_messages_as_list(external_id, limit=50):
    return await asyncio.to_thread(get_recent_messages_as_list_sync, external_id, limit)


async def summarize_memory_async(external_id):
    return await asyncio.to_thread(_summarize_memory_sync, external_id)


async def analyze_message_async(external_id, text):
    return await asyncio.to_thread(_analyze_message_sync, external_id, text)
