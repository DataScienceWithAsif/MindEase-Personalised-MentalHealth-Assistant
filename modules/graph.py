# ── Imports ──────────────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Literal, Annotated, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pinecone import Pinecone
from pymongo import MongoClient
from datetime import datetime, timezone
import requests, os
from dotenv import load_dotenv
load_dotenv()

from utilities import get_relevant_info
from memory import _save_summary, _get_summary, _compress_turns, save_turn_to_memory, load_history_from_memory, clear_memory, inspect_memory
from memory import get_memory_collection

memory_collection = get_memory_collection()

COMPRESSION_THRESHOLD = 10   # compress when stored turns exceed this
KEEP_RECENT           = 5    # always keep this many raw turns

# ── Models ────────────────────────────────────────────────────────────────────
groq_llm   = ChatGroq(model="llama-3.3-70b-versatile")
gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
# ── Tavily Web Search ─────────────────────────────────────────────────────────
web_search_tool = TavilySearchResults(max_results=3)

# ── Message Type Schema ───────────────────────────────────────────────────────
class MessageType(BaseModel):
    emotional_sharing:     Literal['yes', 'no'] = Field(
        description="User is expressing personal feelings, distress, pain, sadness, fear, anxiety, trauma, loneliness, hopelessness, or any emotional experience — even if subtle or indirect."
    )
    general_conversation:  Literal['yes', 'no'] = Field(
        description="Casual chat, greetings, small talk, or factual non-emotional exchange with no mental health relevance."
    )
    mentalHealth_question: Literal['yes', 'no'] = Field(
        description="User is asking for information, explanation, or advice about a mental health topic, condition, therapy, or coping strategy."
    )
    confidence:            float = Field(
        description="Classification confidence from 0.0 to 1.0"
    )
# ── Emotion Detection Schema ──────────────────────────────────────────────────
class EmotionDetection(BaseModel):
    mental_state: Literal[
        'normal', 'Personality disorder', 'SuicidalThought', 'addiction',
        'EatingDisorder', 'Bipolar disorder', 'depression', 'Psychotic disorder',
        'anxiety', 'stress', 'ADHD', 'Compulsive disorder', 'loneliness',
        'Post-trauma disorder'
    ] = Field(description="Primary detected mental state")
    emotional_tone: Literal[
        'hopeless', 'fearful', 'angry', 'sad', 'numb', 'overwhelmed',
        'confused', 'isolated', 'ashamed', 'calm', 'neutral'
    ] = Field(description="Dominant emotional tone in the user's message")
    key_concern: str = Field(
        description="One concise sentence describing the user's core concern or pain point"
    )
    
class Quotations(BaseModel):
    quotations: List[str] = Field(description="3 to 5 short motivational quotes that are relevant to current user mental state")

class CheckRelevancy(BaseModel):
    context_relevancy: Literal['yes','no'] = Field(description="Is context relevant to user message?")
    relevancy_score:   float               = Field(description="Relevancy score 0.0 to 1.0")
    

class GraphState(TypedDict):
    # ── Identity ──────────────────────────────────────────────
    user_id:               str          # who is talking
    conversation_history:  str          # loaded from MongoDB at start
    # ── Current turn ─────────────────────────────────────────
    user_message:          str
    # ── Routing & analysis ────────────────────────────────────
    message_type:          MessageType
    mental_state:          EmotionDetection
    check_relevancy:       CheckRelevancy
    # ── Intermediate outputs ──────────────────────────────────
    fine_tuned_model_response: str
    quotations:            Quotations
    relevant_info:         str
    # ── Final responses (one will be set depending on route) ──
    friendly_response:     str
    questionare_response:  str
    general_response:      str
    # ── The final answer to return and save ──────────────────
    final_response:        str
    
# =========================== nodes ========================
def load_memory_node(state: GraphState):
    """
    Fetch conversation history from MongoDB for this user.
    Injects it into state as 'conversation_history' string.
    """
    user_id = state.get("user_id", "default_user")
    history = load_history_from_memory(user_id)
    return {"conversation_history": history}

## Routing Node
llm_with_message_type = groq_llm.with_structured_output(MessageType)
def message_type_router(state: GraphState):
    user_message = state["user_message"]
    try:
        message_type = llm_with_message_type.invoke(user_message)
        if message_type.emotional_sharing    == 'yes': return "emotional_meesage"
        elif message_type.general_conversation == 'yes': return "general_conversation"
        elif message_type.mentalHealth_question == 'yes': return "questional_message"
        else: return "irrelevant"
    except Exception:
        return "general_conversation"
    
## Emotional Path Nodes
llm_with_EmotionDetection = gemini_llm.with_structured_output(EmotionDetection)
def emotion_detection(state: GraphState):
    user_message = state["user_message"]
    history      = state.get("conversation_history", "")
    SYS_Prompt = """You are an expert in detecting mental health condition of a user.
    Analyse the user's current message AND conversation history to detect mental state."""
    mental_state = llm_with_EmotionDetection.invoke([
        SystemMessage(content=SYS_Prompt),
        HumanMessage(content=f"{history}\n\nCurrent message: {user_message}")
    ])
    return {"mental_state": mental_state}

## related domain finetuned model nodes
def Fine_Tuned_Model(state: GraphState):
    user_message = state["user_message"]
    API_URL = "https://a-asif-mindease.hf.space/predict"
    try:
        response = requests.post(API_URL, json={"text": str(user_message)}, timeout=15)
        response = response.json()["response"]
    except Exception:
        response = "Please be kind to yourself. You are not alone in this."
    return {"fine_tuned_model_response": response}

# quotation_generator node
llm_with_quotation_generator = gemini_llm.with_structured_output(Quotations)
def quotation_generator(state: GraphState):
    user_message = state["user_message"]
    mentalState  = state["mental_state"].mental_state

    try:
        result      = web_search_tool.invoke(f"{mentalState} mental health best quotes")
        web_results = [res["content"] for res in result]
    except Exception:
        web_results = []
    SYS_Prompt = """Generate 3 to 5 short motivational quotations based on user's mental state.
    Return only quotes, one per line, with author if confident."""
    response = llm_with_quotation_generator.invoke([
        SystemMessage(content=SYS_Prompt),
        HumanMessage(content=f"Mental State: {mentalState}\nUser: {user_message}\nWeb: {web_results}")
    ])
    return {"quotations": response}

## Friendly-sympathic response
def friendly_response(state: GraphState):
    user_message   = state["user_message"]
    history        = state.get("conversation_history", "")
    mentalState    = state["mental_state"].mental_state
    quotations     = state["quotations"].quotations
    ft_response    = state["fine_tuned_model_response"]
    SYS_Prompt = """You are an Expert Mental Health Psychologist Agent.
    You will receive:
    - Full conversation history with this user (use it to be personalized)
    - Their current message and detected mental state
    - Relevant motivational quotes
    - A safe response from a fine-tuned model

    Give a short, calm, structured, friendly and supportive response.
    Include quotes where suitable. Mitigate harmful states gently.
    NEVER be robotic. Use the history to feel like a continuous relationship."""

    response = groq_llm.invoke([
        SystemMessage(content=SYS_Prompt),
        HumanMessage(content=(
            f"{history}\n\n"
            f"Current Message: {user_message}\n"
            f"Mental State: {mentalState}\n"
            f"Quotes: {quotations}\n"
            f"Fine-tuned response: {ft_response}"
        ))
    ])
    answer = response.content
    return {"friendly_response": answer, "final_response": answer}

## Question Path Nodes
def getting_context(state: GraphState):
    relevant_text = get_relevant_info(query=str(state["user_message"]))
    return {"relevant_info": relevant_text}

llm_with_relevancy_check = gemini_llm.with_structured_output(CheckRelevancy)
def checking_context_relevancy(state: GraphState):
    SYS = """Check whether the given context is relevant to the user message.
    Be honest. Return context_relevancy and relevancy_score (0.0-1.0)."""
    result = llm_with_relevancy_check.invoke([
        SystemMessage(content=SYS),
        HumanMessage(content=f"Message: {state['user_message']}\nContext: {state['relevant_info']}")
    ])
    return {"check_relevancy": result}

def relevancy_router(state: GraphState):
    r = state["check_relevancy"]
    return "relevant" if r.context_relevancy == 'yes' and r.relevancy_score > 0.4 else "irrelevant"

def web_search(state: GraphState):
    results = web_search_tool.invoke(str(state["user_message"]))
    context = "".join(r["content"] + "\n\n" for r in results[:2])
    return {"relevant_info": context}

def questionare_response(state: GraphState):
    user_message = state["user_message"]
    history      = state.get("conversation_history", "")
    context      = state["relevant_info"]

    SYS_Prompt = """You are an expert mental health Q&A assistant.
    Use the conversation history to personalise your answer.
    Use the context and your knowledge. Be clean, short and structured."""

    response = groq_llm.invoke([
        SystemMessage(content=SYS_Prompt),
        HumanMessage(content=f"{history}\n\nQuestion: {user_message}\nContext: {context}")
    ])
    answer = response.content
    return {"questionare_response": answer, "final_response": answer}

## General Response Node
def general_response(state: GraphState):
    user_message = state["user_message"]
    history      = state.get("conversation_history", "")

    SYS_Prompt = """You are a Personalized Mental Health Assistant.
    You have memory of past conversations with this user — use it to be personal and warm.
    Give a friendly, interactive, short and clean response."""

    try:
        response = groq_llm.invoke([
            SystemMessage(content=SYS_Prompt),
            HumanMessage(content=f"{history}\n\nCurrent message: {user_message}")
        ])
        answer = response.content
    except Exception:
        answer = (
            "I'm having trouble connecting right now. "
            "If this feels urgent, please contact a trusted person or emergency services."
        )
        
    return {"general_response": answer, "final_response": answer}

#  Node — Save Memory to MongoDB
## This runs LAST after every response. Saves the turn to Atlas.
def save_memory_node(state: GraphState):
    """
    After every response:
    1. Save current turn to MongoDB
    2. Count raw turns
    3. If raw turns > COMPRESSION_THRESHOLD → compress
    """
    user_id      = state.get("user_id", "default_user")
    user_message = state.get("user_message", "")
    ai_response  = state.get("final_response", "")

    if not user_message or not ai_response:
        return {}

    # ── Step 1: Save current turn ─────────────────────────────────────────────
    save_turn_to_memory(user_id, user_message, ai_response)

    # ── Step 2: Count ONLY raw turns (exclude summary doc) ───────────────────
    raw_turn_count = memory_collection.count_documents({
        "user_id": user_id,
        "key":     {"$exists": False}
    })
    existing_summary = _get_summary(user_id)

    # ── Step 3: Compress if needed ────────────────────────────────────────────
    if raw_turn_count > COMPRESSION_THRESHOLD:
        # Fetch ALL raw turns oldest → newest
        all_raw_turns = list(
            memory_collection
            .find({"user_id": user_id, "key": {"$exists": False}})
            .sort("timestamp", 1)
        )

        # Verify count matches (sanity check)
        if len(all_raw_turns) <= KEEP_RECENT:
            return {}

        # Split: compress old, keep recent
        turns_to_compress = all_raw_turns[:-KEEP_RECENT]
        turns_to_keep     = all_raw_turns[-KEEP_RECENT:]

        # Run compression
        _compress_turns(user_id, turns_to_compress, existing_summary)

    else:
        pass

    return {}

## Build the Graph
builder = StateGraph(GraphState)

# ── Register nodes ────────────────────────────────────────────────────────────
builder.add_node("load_memory",               load_memory_node)
builder.add_node("emotion_detection",         emotion_detection)
builder.add_node("Fine_Tuned_Model",          Fine_Tuned_Model)
builder.add_node("quotation_generator",       quotation_generator)
builder.add_node("friendly_response",         friendly_response)
builder.add_node("getting_context",           getting_context)
builder.add_node("checking_context_relevancy",checking_context_relevancy)
builder.add_node("web_search",                web_search)
builder.add_node("questionare_response",      questionare_response)
builder.add_node("general_response",          general_response)
builder.add_node("save_memory",               save_memory_node)

# ── START → load_memory (always first) ───────────────────────────────────────
builder.add_edge(START, "load_memory")

# ── load_memory → route by message type ──────────────────────────────────────
builder.add_conditional_edges(
    "load_memory",
    message_type_router,
    {
        "emotional_meesage":  "emotion_detection",
        "general_conversation": "general_response",
        "questional_message": "getting_context",
        "irrelevant": END
    }
)

# ── Emotional path ────────────────────────────────────────────────────────────
builder.add_edge("emotion_detection",   "Fine_Tuned_Model")
builder.add_edge("Fine_Tuned_Model",    "quotation_generator")
builder.add_edge("quotation_generator", "friendly_response")
builder.add_edge("friendly_response",   "save_memory")   # ← save before END

# ── Question path ─────────────────────────────────────────────────────────────
builder.add_edge("getting_context", "checking_context_relevancy")
builder.add_conditional_edges(
    "checking_context_relevancy",
    relevancy_router,
    {"relevant": "questionare_response", "irrelevant": "web_search"}
)
builder.add_edge("web_search",           "questionare_response")
builder.add_edge("questionare_response", "save_memory")  # ← save before END

# ── General path ──────────────────────────────────────────────────────────────
builder.add_edge("general_response", "save_memory")      # ← save before END

# ── save_memory → END (always last) ──────────────────────────────────────────
builder.add_edge("save_memory", END)

graph = builder.compile()
