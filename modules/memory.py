from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
load_dotenv()

groq_llm         = ChatGroq(model="llama-3.3-70b-versatile")

# ── MongoDB Memory Setup ──────────────────────────────────────────────────────
MONGODB_URI      = os.getenv("MONGODB_URI")
DB_NAME          = os.getenv("DB_NAME", "mindease_db")
mongo_client     = MongoClient(MONGODB_URI)

def get_memory_collection():
    memory_collection = mongo_client[DB_NAME]["conversation_memory"]
    # Create index on user_id for fast retrieval
    memory_collection.create_index("user_id")
    return memory_collection

memory_collection = get_memory_collection()

# ── Memory Functions with Summarization Compression ───────────────────────────

COMPRESSION_THRESHOLD = 10   # compress when stored turns exceed this
KEEP_RECENT           = 5    # always keep this many raw turns

SUMMARY_DOC_KEY = "__summary__"   # special key to store the summary document

COMPRESSION_SYSTEM_PROMPT = """You are a memory compression assistant for a mental health support chatbot called MindEase.

Your job is to merge an existing memory summary (if any) with new conversation turns
into one comprehensive, compact summary. 
If there is no existing summery then summarize the given conversation turns.

CRITICAL RULES:
- Preserve ALL personal details: name, age, location, relationships, job, health conditions
- Preserve ALL emotional history: what troubled them, what helped, breakthroughs, setbacks
- Preserve ALL preferences: communication style, topics they like/dislike, coping methods
- Preserve ALL context needed for personalization in future sessions
- Write in third-person about the user (e.g. "The user's name is Asif...")
- Be concise but NEVER omit a detail that could matter for future personalization
- Output plain text only — no bullet points, no headers, no markdown"""


def _get_summary(user_id: str) -> str | None:
    """Retrieve the stored summary document for a user, if any."""
    doc = memory_collection.find_one({
        "user_id": user_id,
        "key":     SUMMARY_DOC_KEY
    })
    return doc["summary_text"] if doc else None


def _save_summary(user_id: str, summary_text: str):
    """Upsert the summary document for a user."""
    memory_collection.update_one(
        {"user_id": user_id, "key": SUMMARY_DOC_KEY},
        {"$set": {
            "user_id":      user_id,
            "key":          SUMMARY_DOC_KEY,
            "summary_text": summary_text,
            "updated_at":   datetime.now(timezone.utc)
        }},
        upsert=True
    )


def _compress_turns(user_id: str, turns_to_compress: list, existing_summary: str | None):
    """
    Ask LLM to merge existing_summary + turns_to_compress → new summary.
    Save new summary and delete compressed raw turns from MongoDB.
    """
    # Build LLM input
    turns_text = ""
    for t in turns_to_compress:
        turns_text += f"User: {t['user_message']}\nAssistant: {t['ai_response']}\n\n"

    if existing_summary:
        llm_input = (
            f"EXISTING SUMMARY (preserve every detail):\n{existing_summary}\n\n"
            f"NEW TURNS TO MERGE IN:\n{turns_text}"
        )
    else:
        llm_input = f"CONVERSATION TURNS TO SUMMARIZE:\n{turns_text}"

    print(f"[Compress] Sending {len(turns_to_compress)} turns to LLM for compression...")

    response = groq_llm.invoke([
        SystemMessage(content=COMPRESSION_SYSTEM_PROMPT),
        HumanMessage(content=llm_input)
    ])
    new_summary = response.content.strip()

    # Save updated summary
    _save_summary(user_id, new_summary)

    # Delete only the turns that were compressed — by their exact MongoDB _id
    compressed_ids = [t["_id"] for t in turns_to_compress]
    delete_result  = memory_collection.delete_many(
        {"_id": {"$in": compressed_ids}}
    )

    print(f"[Compress] Deleted {delete_result.deleted_count} raw turns from MongoDB")

    if delete_result.deleted_count != len(turns_to_compress):
        print(f"[Compress] ⚠️  Mismatch! Expected to delete {len(turns_to_compress)} "
              f"but deleted {delete_result.deleted_count}")

    return new_summary


def save_turn_to_memory(user_id: str, user_message: str, ai_response: str):
    """
    Save one conversation turn to MongoDB.
    Raw turns are identified by absence of 'key' field.
    """
    memory_collection.insert_one({
        "user_id":      user_id,
        "user_message": user_message,
        "ai_response":  ai_response,
        "timestamp":    datetime.now(timezone.utc)
        # deliberately no 'key' field — distinguishes raw turns from summary doc
    })


def load_history_from_memory(user_id: str) -> str:
    """
    Load conversation context for the LLM:
      - Summary of all old compressed turns (if exists)
      - Last KEEP_RECENT raw turns in full
    Returns a single formatted string to inject into the system prompt.
    """
    parts = []

    # 1. Load summary of old turns
    summary = _get_summary(user_id)
    if summary:
        parts.append(f"=== Memory summary (older conversations) ===\n{summary}")

    # 2. Load latest KEEP_RECENT raw turns
    recent_turns = list(
        memory_collection
        .find({"user_id": user_id, "key": {"$exists": False}})
        .sort("timestamp", -1)
        .limit(KEEP_RECENT)
    )
    recent_turns.reverse()  # chronological order

    if recent_turns:
        lines = []
        for t in recent_turns:
            lines.append(f"User: {t['user_message']}")
            lines.append(f"Assistant: {t['ai_response']}")
            lines.append("")
        parts.append("=== Recent conversation ===\n" + "\n".join(lines))

    if not parts:
        return "No previous conversation history."

    return "\n\n".join(parts)


def clear_memory(user_id: str):
    """Wipe all memory and summary for a user."""
    result = memory_collection.delete_many({"user_id": user_id})
    print(f"Cleared {result.deleted_count} documents for {user_id}")


def inspect_memory(user_id: str):
    """Debug helper — print current memory state for a user."""
    summary = _get_summary(user_id)
    raw_count = memory_collection.count_documents({
        "user_id": user_id, "key": {"$exists": False}
    })
    print(f"\n{'='*50}")
    print(f"User: {user_id}")
    print(f"Raw turns stored: {raw_count}")
    print(f"Summary exists: {summary is not None}")
    if summary:
        print(f"\nSummary:\n{summary}")
    print(f"{'='*50}\n")
