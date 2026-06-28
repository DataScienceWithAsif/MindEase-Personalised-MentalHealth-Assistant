# # ── Imports ──────────────────────────────────────────────────────────────────
# from langgraph.graph import StateGraph, START, END
# from typing_extensions import TypedDict, Literal, Annotated, List
# from pydantic import BaseModel, Field
# from langchain_groq import ChatGroq
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_community.tools.tavily_search import TavilySearchResults
# from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# from pinecone import Pinecone
# from pymongo import MongoClient
# from datetime import datetime, timezone
# import requests, os
# from dotenv import load_dotenv
# load_dotenv()

# from utilities import get_relevant_info
# from memory import _save_summary, _get_summary, _compress_turns, save_turn_to_memory, load_history_from_memory, clear_memory, inspect_memory
# from memory import get_memory_collection

# memory_collection = get_memory_collection()

# COMPRESSION_THRESHOLD = 10   # compress when stored turns exceed this
# KEEP_RECENT           = 5    # always keep this many raw turns

# # ── Models ────────────────────────────────────────────────────────────────────
# groq_llm   = ChatGroq(model="llama-3.3-70b-versatile")
# gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
# # ── Tavily Web Search ─────────────────────────────────────────────────────────
# web_search_tool = TavilySearchResults(max_results=3)

# # ── Message Type Schema ───────────────────────────────────────────────────────
# class MessageType(BaseModel):
#     emotional_sharing:     Literal['yes', 'no'] = Field(
#         description="User is expressing personal feelings, distress, pain, sadness, fear, anxiety, trauma, loneliness, hopelessness, or any emotional experience — even if subtle or indirect."
#     )
#     general_conversation:  Literal['yes', 'no'] = Field(
#         description="Casual chat, greetings, small talk, or factual non-emotional exchange with no mental health relevance."
#     )
#     mentalHealth_question: Literal['yes', 'no'] = Field(
#         description="User is asking for information, explanation, or advice about a mental health topic, condition, therapy, or coping strategy."
#     )
#     confidence:            float = Field(
#         description="Classification confidence from 0.0 to 1.0"
#     )
# # ── Emotion Detection Schema ──────────────────────────────────────────────────
# class EmotionDetection(BaseModel):
#     mental_state: Literal[
#         'normal', 'Personality disorder', 'SuicidalThought', 'addiction',
#         'EatingDisorder', 'Bipolar disorder', 'depression', 'Psychotic disorder',
#         'anxiety', 'stress', 'ADHD', 'Compulsive disorder', 'loneliness',
#         'Post-trauma disorder'
#     ] = Field(description="Primary detected mental state")
#     emotional_tone: Literal[
#         'hopeless', 'fearful', 'angry', 'sad', 'numb', 'overwhelmed',
#         'confused', 'isolated', 'ashamed', 'calm', 'neutral'
#     ] = Field(description="Dominant emotional tone in the user's message")
#     key_concern: str = Field(
#         description="One concise sentence describing the user's core concern or pain point"
#     )
    
# class Quotations(BaseModel):
#     quotations: List[str] = Field(description="3 to 5 short motivational quotes that are relevant to current user mental state")

# class CheckRelevancy(BaseModel):
#     context_relevancy: Literal['yes','no'] = Field(description="Is context relevant to user message?")
#     relevancy_score:   float               = Field(description="Relevancy score 0.0 to 1.0")
    

# class GraphState(TypedDict):
#     # ── Identity ──────────────────────────────────────────────
#     user_id:               str          # who is talking
#     conversation_history:  str          # loaded from MongoDB at start
#     # ── Current turn ─────────────────────────────────────────
#     user_message:          str
#     # ── Routing & analysis ────────────────────────────────────
#     message_type:          MessageType
#     mental_state:          EmotionDetection
#     check_relevancy:       CheckRelevancy
#     # ── Intermediate outputs ──────────────────────────────────
#     fine_tuned_model_response: str
#     quotations:            Quotations
#     relevant_info:         str
#     # ── Final responses (one will be set depending on route) ──
#     friendly_response:     str
#     questionare_response:  str
#     general_response:      str
#     # ── The final answer to return and save ──────────────────
#     final_response:        str
    
# # =========================== nodes ========================
# def load_memory_node(state: GraphState):
#     """
#     Fetch conversation history from MongoDB for this user.
#     Injects it into state as 'conversation_history' string.
#     """
#     user_id = state.get("user_id", "default_user")
#     history = load_history_from_memory(user_id)
#     return {"conversation_history": history}

# ## Routing Node
# llm_with_message_type = groq_llm.with_structured_output(MessageType)
# def message_type_router(state: GraphState):
#     user_message = state["user_message"]
#     try:
#         message_type = llm_with_message_type.invoke(user_message)
#         if message_type.emotional_sharing    == 'yes': return "emotional_meesage"
#         elif message_type.general_conversation == 'yes': return "general_conversation"
#         elif message_type.mentalHealth_question == 'yes': return "questional_message"
#         else: return "irrelevant"
#     except Exception:
#         return "general_conversation"
    
# ## Emotional Path Nodes
# llm_with_EmotionDetection = gemini_llm.with_structured_output(EmotionDetection)
# def emotion_detection(state: GraphState):
#     user_message = state["user_message"]
#     history      = state.get("conversation_history", "")
#     SYS_Prompt = """You are an expert in detecting mental health condition of a user.
#     Analyse the user's current message AND conversation history to detect mental state."""
#     mental_state = llm_with_EmotionDetection.invoke([
#         SystemMessage(content=SYS_Prompt),
#         HumanMessage(content=f"{history}\n\nCurrent message: {user_message}")
#     ])
#     return {"mental_state": mental_state}

# ## related domain finetuned model nodes
# def Fine_Tuned_Model(state: GraphState):
#     user_message = state["user_message"]
#     API_URL      = "https://a-asif-mindease.hf.space/predict"

#     for attempt in range(2):
#         try:
#             r = requests.post(
#                 API_URL,
#                 json={"text": str(user_message)},
#                 timeout=55          # ← safe under HF's 60s hard limit
#             )
#             r.raise_for_status()
#             result = r.json().get("response", "")
#             if result:
#                 return {"fine_tuned_model_response": result}
#         except requests.exceptions.Timeout:
#             if attempt == 0:
#                 print("[FineTuned] Cold start timeout — retrying...")
#                 continue
#             print("[FineTuned] Second timeout — using fallback")
#         except Exception as e:
#             print(f"[FineTuned] Error: {e} — using fallback")
#             break

#     return {"fine_tuned_model_response": "Please be kind to yourself. You are not alone in this."}

# # quotation_generator node
# llm_with_quotation_generator = gemini_llm.with_structured_output(Quotations)
# def quotation_generator(state: GraphState):
#     user_message = state["user_message"]
#     mentalState  = state["mental_state"].mental_state

#     try:
#         result      = web_search_tool.invoke(f"{mentalState} mental health best quotes")
#         web_results = [res["content"] for res in result]
#     except Exception:
#         web_results = []
#     SYS_Prompt = """Generate 3 to 5 short motivational quotations based on user's mental state.
#     Return only quotes, one per line, with author if confident."""
#     response = llm_with_quotation_generator.invoke([
#         SystemMessage(content=SYS_Prompt),
#         HumanMessage(content=f"Mental State: {mentalState}\nUser: {user_message}\nWeb: {web_results}")
#     ])
#     return {"quotations": response}

# ## Friendly-sympathic response
# def friendly_response(state: GraphState):
#     user_message   = state["user_message"]
#     history        = state.get("conversation_history", "")
#     mentalState    = state["mental_state"].mental_state
#     quotations     = state["quotations"].quotations
#     ft_response    = state["fine_tuned_model_response"]
#     SYS_Prompt = """You are an Expert Mental Health Psychologist Agent.
#     You will receive:
#     - Full conversation history with this user (use it to be personalized)
#     - Their current message and detected mental state
#     - Relevant motivational quotes
#     - A safe response from a fine-tuned model

#     Give a short, calm, structured, friendly and supportive response.
#     Include quotes where suitable. Mitigate harmful states gently.
#     NEVER be robotic. Use the history to feel like a continuous relationship."""

#     response = groq_llm.invoke([
#         SystemMessage(content=SYS_Prompt),
#         HumanMessage(content=(
#             f"{history}\n\n"
#             f"Current Message: {user_message}\n"
#             f"Mental State: {mentalState}\n"
#             f"Quotes: {quotations}\n"
#             f"Fine-tuned response: {ft_response}"
#         ))
#     ])
#     answer = response.content
#     return {"friendly_response": answer, "final_response": answer}

# ## Question Path Nodes
# def getting_context(state: GraphState):
#     relevant_text = get_relevant_info(query=str(state["user_message"]))
#     return {"relevant_info": relevant_text}

# llm_with_relevancy_check = gemini_llm.with_structured_output(CheckRelevancy)
# def checking_context_relevancy(state: GraphState):
#     SYS = """Check whether the given context is relevant to the user message.
#     Be honest. Return context_relevancy and relevancy_score (0.0-1.0)."""
#     result = llm_with_relevancy_check.invoke([
#         SystemMessage(content=SYS),
#         HumanMessage(content=f"Message: {state['user_message']}\nContext: {state['relevant_info']}")
#     ])
#     return {"check_relevancy": result}

# def relevancy_router(state: GraphState):
#     r = state["check_relevancy"]
#     return "relevant" if r.context_relevancy == 'yes' and r.relevancy_score > 0.4 else "irrelevant"

# def web_search(state: GraphState):
#     results = web_search_tool.invoke(str(state["user_message"]))
#     context = "".join(r["content"] + "\n\n" for r in results[:2])
#     return {"relevant_info": context}

# def questionare_response(state: GraphState):
#     user_message = state["user_message"]
#     history      = state.get("conversation_history", "")
#     context      = state["relevant_info"]

#     SYS_Prompt = """You are an expert mental health Q&A assistant.
#     Use the conversation history to personalise your answer.
#     Use the context and your knowledge. Be clean, short and structured."""

#     response = groq_llm.invoke([
#         SystemMessage(content=SYS_Prompt),
#         HumanMessage(content=f"{history}\n\nQuestion: {user_message}\nContext: {context}")
#     ])
#     answer = response.content
#     return {"questionare_response": answer, "final_response": answer}

# ## General Response Node
# def general_response(state: GraphState):
#     user_message = state["user_message"]
#     history      = state.get("conversation_history", "")

#     SYS_Prompt = """You are a Personalized Mental Health Assistant.
#     You have memory of past conversations with this user — use it to be personal and warm.
#     Give a friendly, interactive, short and clean response."""

#     try:
#         response = groq_llm.invoke([
#             SystemMessage(content=SYS_Prompt),
#             HumanMessage(content=f"{history}\n\nCurrent message: {user_message}")
#         ])
#         answer = response.content
#     except Exception:
#         answer = (
#             "I'm having trouble connecting right now. "
#             "If this feels urgent, please contact a trusted person or emergency services."
#         )
        
#     return {"general_response": answer, "final_response": answer}

# #  Node — Save Memory to MongoDB
# ## This runs LAST after every response. Saves the turn to Atlas.
# def save_memory_node(state: GraphState):
#     """
#     After every response:
#     1. Save current turn to MongoDB
#     2. Count raw turns
#     3. If raw turns > COMPRESSION_THRESHOLD → compress
#     """
#     user_id      = state.get("user_id", "default_user")
#     user_message = state.get("user_message", "")
#     ai_response  = state.get("final_response", "")

#     if not user_message or not ai_response:
#         return {}

#     # ── Step 1: Save current turn ─────────────────────────────────────────────
#     save_turn_to_memory(user_id, user_message, ai_response)

#     # ── Step 2: Count ONLY raw turns (exclude summary doc) ───────────────────
#     raw_turn_count = memory_collection.count_documents({
#         "user_id": user_id,
#         "key":     {"$exists": False}
#     })
#     existing_summary = _get_summary(user_id)

#     # ── Step 3: Compress if needed ────────────────────────────────────────────
#     if raw_turn_count > COMPRESSION_THRESHOLD:
#         # Fetch ALL raw turns oldest → newest
#         all_raw_turns = list(
#             memory_collection
#             .find({"user_id": user_id, "key": {"$exists": False}})
#             .sort("timestamp", 1)
#         )

#         # Verify count matches (sanity check)
#         if len(all_raw_turns) <= KEEP_RECENT:
#             return {}

#         # Split: compress old, keep recent
#         turns_to_compress = all_raw_turns[:-KEEP_RECENT]
#         turns_to_keep     = all_raw_turns[-KEEP_RECENT:]

#         # Run compression
#         _compress_turns(user_id, turns_to_compress, existing_summary)

#     else:
#         pass

#     return {}

# ## Build the Graph
# builder = StateGraph(GraphState)

# # ── Register nodes ────────────────────────────────────────────────────────────
# builder.add_node("load_memory",               load_memory_node)
# builder.add_node("emotion_detection",         emotion_detection)
# builder.add_node("Fine_Tuned_Model",          Fine_Tuned_Model)
# builder.add_node("quotation_generator",       quotation_generator)
# builder.add_node("friendly_response",         friendly_response)
# builder.add_node("getting_context",           getting_context)
# builder.add_node("checking_context_relevancy",checking_context_relevancy)
# builder.add_node("web_search",                web_search)
# builder.add_node("questionare_response",      questionare_response)
# builder.add_node("general_response",          general_response)
# builder.add_node("save_memory",               save_memory_node)

# # ── START → load_memory (always first) ───────────────────────────────────────
# builder.add_edge(START, "load_memory")

# # ── load_memory → route by message type ──────────────────────────────────────
# builder.add_conditional_edges(
#     "load_memory",
#     message_type_router,
#     {
#         "emotional_meesage":  "emotion_detection",
#         "general_conversation": "general_response",
#         "questional_message": "getting_context",
#         "irrelevant": END
#     }
# )

# # ── Emotional path ────────────────────────────────────────────────────────────
# builder.add_edge("emotion_detection",   "Fine_Tuned_Model")
# builder.add_edge("Fine_Tuned_Model",    "quotation_generator")
# builder.add_edge("quotation_generator", "friendly_response")
# builder.add_edge("friendly_response",   "save_memory")   # ← save before END

# # ── Question path ─────────────────────────────────────────────────────────────
# builder.add_edge("getting_context", "checking_context_relevancy")
# builder.add_conditional_edges(
#     "checking_context_relevancy",
#     relevancy_router,
#     {"relevant": "questionare_response", "irrelevant": "web_search"}
# )
# builder.add_edge("web_search",           "questionare_response")
# builder.add_edge("questionare_response", "save_memory")  # ← save before END

# # ── General path ──────────────────────────────────────────────────────────────
# builder.add_edge("general_response", "save_memory")      # ← save before END

# # ── save_memory → END (always last) ──────────────────────────────────────────
# builder.add_edge("save_memory", END)

# graph = builder.compile()

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Literal, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import requests, os

from utilities import get_relevant_info
from memory import (
    load_history_from_memory, save_turn_to_memory,
    maybe_compress, _get_summary, _compress_turns,
    get_memory_collection, COMPRESSION_THRESHOLD, KEEP_RECENT
)

load_dotenv()

# ── Models ────────────────────────────────────────────────────────────────────
groq_llm        = ChatGroq(model="llama-3.3-70b-versatile")
gemini_llm      = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
web_search_tool = TavilySearchResults(max_results=3)
memory_collection = get_memory_collection()

# ── Crisis keywords ───────────────────────────────────────────────────────────
CRISIS_KEYWORDS = [
    "end my life", "kill myself", "suicide", "want to die", "end it all",
    "don't want to live", "better off dead", "take my life", "no reason to live",
    "hurt myself", "self harm", "self-harm", "cutting myself", "overdose",
    "can't go on", "ending everything", "not worth living", "tired of living",
    "wish i was dead", "going to die", "plan to die", "goodbye forever"
]

def _is_crisis(text: str) -> bool:
    return any(kw in text.lower() for kw in CRISIS_KEYWORDS)


# ── Schemas ───────────────────────────────────────────────────────────────────
class MessageType(BaseModel):
    emotional_sharing:     Literal['yes', 'no'] = Field(description="User expressing feelings, distress, pain, trauma, loneliness, hopelessness — even subtly.")
    general_conversation:  Literal['yes', 'no'] = Field(description="Casual chat, greetings, small talk with no mental health relevance.")
    mentalHealth_question: Literal['yes', 'no'] = Field(description="Asking for information or advice about mental health topics, conditions, therapy, coping.")
    confidence:            float                = Field(description="Classification confidence 0.0-1.0")

class EmotionDetection(BaseModel):
    mental_state: Literal[
        'normal','Personality disorder','SuicidalThought','addiction','EatingDisorder',
        'Bipolar disorder','depression','Psychotic disorder','anxiety','stress',
        'ADHD','Compulsive disorder','loneliness','Post-trauma disorder'
    ] = Field(description="Primary detected mental state")
    secondary_state: Literal[
        'none','Personality disorder','SuicidalThought','addiction','EatingDisorder',
        'Bipolar disorder','depression','Psychotic disorder','anxiety','stress',
        'ADHD','Compulsive disorder','loneliness','Post-trauma disorder'
    ] = Field(description="Secondary co-occurring state if present, else 'none'")
    severity:       Literal['mild','moderate','severe','crisis'] = Field(description="Severity level")
    crisis_risk:    Literal['none','low','medium','high','immediate'] = Field(description="Self-harm/suicide risk level")
    emotional_tone: Literal['hopeless','fearful','angry','sad','numb','overwhelmed','confused','isolated','ashamed','calm','neutral'] = Field(description="Dominant emotional tone")
    key_concern:    str   = Field(description="One sentence describing the user's core concern")
    confidence:     float = Field(description="Detection confidence 0.0-1.0")

class Quotations(BaseModel):
    quotations: List[str] = Field(description="3 to 5 short quotes relevant to the user's mental state")

class CheckRelevancy(BaseModel):
    context_relevancy: Literal['yes','no'] = Field(description="Is context relevant to user message?")
    relevancy_score:   float               = Field(description="Relevancy score 0.0-1.0")


# ── Graph State ───────────────────────────────────────────────────────────────
class GraphState(TypedDict):
    user_id:               str
    conversation_history:  str
    user_message:          str
    message_type:          MessageType
    mental_state:          EmotionDetection
    check_relevancy:       CheckRelevancy
    fine_tuned_model_response: str
    quotations:            Quotations
    relevant_info:         str
    friendly_response:     str
    questionare_response:  str
    general_response:      str
    final_response:        str


# ── LLM instances with structured output ─────────────────────────────────────
llm_with_message_type     = groq_llm.with_structured_output(MessageType)
llm_with_EmotionDetection = gemini_llm.with_structured_output(EmotionDetection)
llm_with_quotations       = gemini_llm.with_structured_output(Quotations)
llm_with_relevancy_check  = gemini_llm.with_structured_output(CheckRelevancy)

# ── OPTIMIZED: Clearer classification priority with tiebreaker rule ────────────────
MESSAGE_TYPE_PROMPT = """You are a clinical message classifier for MindEase, a mental health support app.

CLASSIFICATION RULES (apply in strict order — stop at the first match):
1. emotional_sharing = 'yes'  → User expresses feelings, distress, pain, trauma, loneliness,
   hopelessness, numbness, or isolation — even subtly, indirectly, or through venting.
   This INCLUDES messages like "I'm fine" said after prior distress, or "whatever, never mind."
2. mentalHealth_question = 'yes' → User explicitly asks for information, advice, or explanation
   about a mental health topic, therapy, diagnosis, coping strategies, or conditions.
3. general_conversation = 'yes' → ONLY pure casual chit-chat with absolutely zero emotional
   or mental health relevance (e.g. "what's your favourite colour", "good morning").

PRIORITY: emotional_sharing > mentalHealth_question > general_conversation
TIEBREAKER: If you are unsure between emotional_sharing and any other category, always choose
emotional_sharing — this is a safety-first mental health app."""

# ── OPTIMIZED: More precise severity anchors and crisis sensitivity ────────────────
EMOTION_PROMPT = """You are a clinical psychologist AI specialising in mental health assessment for MindEase.

Analyse the current message AND conversation history with clinical precision.

MENTAL STATE: Choose the single most dominant condition from the allowed values.
SECONDARY STATE: Note any clear co-occurring condition, or 'none'.
SEVERITY anchors:
  mild     = slight distress, functioning intact, no impairment
  moderate = noticeable distress, some daily impact, person still coping
  severe   = significant impairment, difficulty functioning, persistent symptoms
  crisis   = immediate risk, acute breakdown, suicidal/self-harm ideation (explicit or strongly implicit)

CRISIS RISK anchors:
  none      = no indicators at all
  low       = indirect hints (feeling trapped, "tired of everything") — flag, do not dismiss
  medium    = recurring dark thoughts, passive ideation ("I don't care if I live")
  high      = active ideation without stated plan
  immediate = stated intent, plan, or farewell language

KEY CONCERN: What is ACTUALLY hurting this person right now? Be specific — name the real pain,
not a generic category. Example: not "depression" but "feels invisible to their family."

CALIBRATION NOTE: Err on the side of higher crisis risk when ambiguous. A false positive
is recoverable; a false negative is not."""


# ════════════════════════════════ NODES ══════════════════════════════════════

def load_memory_node(state: GraphState):
    history = load_history_from_memory(state.get("user_id", "default_user"))
    return {"conversation_history": history}


def message_type_router(state: GraphState):
    user_message = state["user_message"]

    if _is_crisis(user_message):
        return "emotional_meesage"

    try:
        result = llm_with_message_type.invoke([
            SystemMessage(content=MESSAGE_TYPE_PROMPT),
            HumanMessage(content=f'Classify this message:\n\n"{user_message}"')
        ])
        if result.emotional_sharing    == 'yes': return "emotional_meesage"
        elif result.mentalHealth_question == 'yes': return "questional_message"
        elif result.general_conversation  == 'yes': return "general_conversation"
        else: return "emotional_meesage"
    except Exception:
        return "emotional_meesage"


def emotion_detection(state: GraphState):
    user_message = state["user_message"]
    history      = state.get("conversation_history", "")

    if _is_crisis(user_message):
        return {"mental_state": EmotionDetection(
            mental_state="SuicidalThought", secondary_state="depression",
            severity="crisis", crisis_risk="immediate",
            emotional_tone="hopeless",
            key_concern="User has expressed direct thoughts of ending their life.",
            confidence=1.0
        )}

    try:
        result = llm_with_EmotionDetection.invoke([
            SystemMessage(content=EMOTION_PROMPT),
            HumanMessage(content=f"HISTORY:\n{history}\n\nCURRENT MESSAGE:\n{user_message}")
        ])
        return {"mental_state": result}
    except Exception:
        return {"mental_state": EmotionDetection(
            mental_state="stress", secondary_state="none",
            severity="moderate", crisis_risk="none",
            emotional_tone="overwhelmed",
            key_concern="Unable to precisely detect — treating as moderate stress.",
            confidence=0.3
        )}


def Fine_Tuned_Model(state: GraphState):
    user_message = state["user_message"]
    # API_URL    = "https://a-asif-mindease.hf.space/predict"
    API_URL      = "https://a-asif-fyp-gemma-ft.hf.space/predict"

    for attempt in range(2):
        try:
            r = requests.post(
                API_URL,
                json={"text": str(user_message)},
                timeout=55
            )
            r.raise_for_status()
            result = r.json().get("response", "")
            if result:
                return {"fine_tuned_model_response": result}
        except requests.exceptions.Timeout:
            if attempt == 0:
                print("[FineTuned] Cold start timeout — retrying...")
                continue
            print("[FineTuned] Second timeout — using fallback")
        except Exception as e:
            print(f"[FineTuned] Error: {e} — using fallback")
            break

    return {"fine_tuned_model_response": "Please be kind to yourself. You are not alone in this."}


# ── OPTIMIZED: Tone-aware quote generation based on severity ─────────────────
def quotation_generator(state: GraphState):
    user_message = state["user_message"]
    ms           = state["mental_state"]
    mental_state = ms.mental_state

    # Choose quote tone based on severity and crisis risk — not one-size-fits-all
    if ms.crisis_risk in ("immediate", "high"):
        tone_instruction = (
            "compassionate and validating — quotes that say 'you are not alone' and "
            "'your pain is real', NOT cheerful or preachy. Avoid 'you can do it' energy."
        )
        search_query = f"{mental_state} you are not alone empathy quotes"
    elif ms.severity in ("severe", "moderate") or ms.crisis_risk == "medium":
        tone_instruction = (
            "hopeful but grounded — quotes that acknowledge darkness while pointing toward "
            "a small light ahead. Not toxic positivity. Think Rumi, Viktor Frankl, Brené Brown."
        )
        search_query = f"{mental_state} healing resilience meaningful quotes"
    else:
        tone_instruction = (
            "uplifting and gently encouraging — quotes that motivate without minimising. "
            "Warm, human, not generic."
        )
        search_query = f"{mental_state} motivation encouragement quotes"

    try:
        results     = web_search_tool.invoke(search_query)
        web_results = [r["content"] for r in results[:2]]
    except Exception:
        web_results = []

    # ── OPTIMIZED: Strict format rules so quotes are short enough to weave into prose ──
    SYS = f"""Generate exactly 4 quotes with a {tone_instruction} tone, relevant to mental state: {mental_state}.

STRICT RULES:
- Each quote body MUST be under 12 words (excluding the author name)
- Format every quote as: "Quote text here — Author Name"
- Do NOT start quotes with "You are" or "You can" — too preachy
- Do NOT use clichés like "Every cloud has a silver lining" or "This too shall pass"
- Pick quotes that feel like a wise friend sharing something real, not a poster slogan
- Use real authors (Rumi, Frankl, Maya Angelou, Brené Brown, Thich Nhat Hanh, etc.)

Return ONLY valid JSON with no markdown, no backticks, no explanation:
{{"quotations": ["Quote text — Author", "Quote text — Author", "Quote text — Author", "Quote text — Author"]}}"""

    try:
        import json, re
        r   = groq_llm.invoke([
            SystemMessage(content=SYS),
            HumanMessage(content=f"Mental state: {mental_state}\nUser message: {user_message}\nWeb context: {web_results}")
        ])
        raw = re.sub(r"^```(?:json)?|```$", "", r.content.strip(), flags=re.MULTILINE).strip()
        data   = json.loads(raw)
        quotes = data.get("quotations", [])
        if not quotes or len(quotes) < 2:
            raise ValueError("Too few quotes returned")
    except Exception:
        # Tier-matched fallbacks
        if ms.crisis_risk in ("immediate", "high"):
            quotes = [
                "You are not alone in the dark — Atticus",
                "Even the darkest night will end — Victor Hugo",
                "The wound is the place where light enters — Rumi",
                "Pain is real, and so is hope — Harriet Beecher Stowe",
            ]
        elif ms.severity in ("severe", "moderate"):
            quotes = [
                "Rock bottom became the foundation — J.K. Rowling",
                "You don't have to see the whole staircase — Martin Luther King Jr.",
                "In the middle of difficulty lies opportunity — Albert Einstein",
                "Stars can't shine without darkness — D.H. Sidebottom",
            ]
        else:
            quotes = [
                "Small steps are still steps — Unknown",
                "You've survived 100% of your bad days — Unknown",
                "Be gentle with yourself — Max Ehrmann",
                "Progress, not perfection — Unknown",
            ]

    return {"quotations": Quotations(quotations=quotes[:4])}


# ── OPTIMIZED: Mandatory, precisely-placed quote integration ─────────────────
def friendly_response(state: GraphState):
    user_message = state["user_message"]
    history      = state.get("conversation_history", "")
    ms           = state["mental_state"]
    quotations   = state["quotations"].quotations
    ft_response  = state["fine_tuned_model_response"]

    clinical_ctx = (
        f"Mental state: {ms.mental_state} | Secondary: {ms.secondary_state}\n"
        f"Severity: {ms.severity} | Crisis risk: {ms.crisis_risk}\n"
        f"Emotional tone: {ms.emotional_tone}\nCore concern: {ms.key_concern}"
    )

    # ── Format the quote list with numbers so the model can pick exactly one ──
    quote_list = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(quotations))

    if ms.crisis_risk in ("immediate", "high"):
        # ── OPTIMIZED: Crisis prompt with quote placed in a specific, named slot ──
        SYS = """You are a warm, human crisis support companion at MindEase. This person is in serious pain.

RESPONSE STRUCTURE — follow this exactly, in this order (3–4 sentences total):
  [SENTENCE 1 — Acknowledge] Reflect their exact pain back using their own words. No advice, no silver linings.
  [SENTENCE 2 — Validate] Normalise the feeling without minimising. "That kind of pain is real."
  [SENTENCE 3 — QUOTE] YOU MUST include one quote from the QUOTES LIST. Weave it into a sentence naturally:
      Pattern: "Someone once wrote, '[quote]' — and I keep thinking about you when I read that."
      Or: "There's a line I love: '[quote]' — I mean it for you right now."
      Do NOT paste the quote standalone. It must be inside a warm sentence.
  [SENTENCE 4 — Connect + Helpline] End with: "You can reach Umang Pakistan anytime at 0317-4288665 — they truly listen."
      Then add one gentle, open question to keep them talking (e.g. "Can you tell me what's happening right now?")

HARD RULES:
  - NO bullet points, NO headers, NO numbered lists in the output
  - NO "reasons to live", NO "it gets better", NO cheerful reframes
  - Write as flowing prose — like a caring human sitting beside them
  - Use their first name if known from conversation history
  - The quote MUST appear. A response without a quote violates this prompt."""

    elif ms.crisis_risk == "medium" or ms.severity == "severe":
        # ── OPTIMIZED: Medium/severe prompt with quote as a numbered, mandatory step ──
        SYS = """You are a caring mental health companion at MindEase. This person is struggling.

RESPONSE STRUCTURE — follow this exactly, in this order (4–5 sentences total):
  [SENTENCE 1 — Reflect] Show you truly heard them — reflect back the specific thing they shared.
  [SENTENCE 2 — Normalise] Validate their feeling without minimising it or rushing to solutions.
  [SENTENCE 3 — QUOTE] YOU MUST include one quote from the QUOTES LIST. Weave it naturally:
      Pattern: "I keep coming back to something [Author] said: '[quote]' — it made me think of you."
      Or: "As [Author] put it, '[quote]' — and I think that's true for where you are right now."
      The quote must be embedded inside a warm sentence — never a standalone line.
  [SENTENCE 4 — Suggestion] Offer one small, specific coping idea tailored to what they described — not generic advice.
  [SENTENCE 5 — Close] A warm closing that leaves the door open.

HARD RULES:
  - NO bullet points, NO headers, NO lists — flowing warm prose only
  - Use their name if known from conversation history
  - Sound like a trusted friend who happens to understand psychology, not a therapist giving notes
  - The quote MUST appear in sentence 3. A response without it is incomplete."""

    else:
        # ── OPTIMIZED: Mild prompt — quote is mandatory, not optional ──
        SYS = """You are MindEase — a warm, insightful mental health companion.

RESPONSE STRUCTURE — follow this exactly, in this order (3–4 sentences total):
  [SENTENCE 1 — Acknowledge] Acknowledge what they shared in a personal, specific way — not generic.
  [SENTENCE 2 — QUOTE] YOU MUST include one quote from the QUOTES LIST. Weave it in naturally:
      Pattern: "I thought of something [Author] said: '[quote]' — it felt right for this."
      Or: "There's a line from [Author] — '[quote]' — that keeps coming to mind here."
      The quote must live inside a warm sentence, not pasted on its own.
  [SENTENCE 3 — Reframe or Insight] Offer a brief, relevant insight or gentle reframe connected to what they said.
  [SENTENCE 4 — Move forward] End with a light, specific suggestion or question to gently move forward.

HARD RULES:
  - NO bullet points, NO headers, NO numbered lists
  - Conversational and warm — like a wise friend texting back, not a therapy transcript
  - Use their name once if known from conversation history
  - The quote MUST appear in sentence 2 — a response without it is incomplete."""

    response = groq_llm.invoke([
        SystemMessage(content=SYS),
        HumanMessage(content=(
            f"CONVERSATION HISTORY:\n{history}\n\n"
            f"CURRENT MESSAGE:\n{user_message}\n\n"
            f"CLINICAL CONTEXT:\n{clinical_ctx}\n\n"
            f"REFERENCE RESPONSE (use for tone guidance only, do not copy verbatim):\n{ft_response}\n\n"
            f"QUOTES LIST — pick exactly ONE and weave it into the designated sentence:\n{quote_list}\n\n"
            f"REMINDER: Your response MUST include one quote from the list above, woven naturally "
            f"into a sentence. A response without a quote is incomplete."
        ))
    ])
    return {"friendly_response": response.content, "final_response": response.content}


def getting_context(state: GraphState):
    return {"relevant_info": get_relevant_info(query=str(state["user_message"]))}


def checking_context_relevancy(state: GraphState):
    result = llm_with_relevancy_check.invoke([
        SystemMessage(content="Check if the given context is relevant to the user message. Return context_relevancy and relevancy_score 0.0-1.0."),
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

    SYS = """You are MindEase — a knowledgeable, friendly mental health guide.
RESPONSE FORMAT:
- Start with one sentence directly answering the question
- Follow with 2–3 short, plain-language points (no jargon)
- End with one encouraging or personalising sentence
Rules:
- Maximum 5–6 sentences total
- No long paragraphs — keep each point to one sentence
- Use "you" language — make it feel personal, not textbook
- If their name is in history, use it
- Avoid clinical jargon — speak like an informed friend"""

    response = groq_llm.invoke([
        SystemMessage(content=SYS),
        HumanMessage(content=(
            f"CONVERSATION HISTORY:\n{history}\n\n"
            f"QUESTION:\n{user_message}\n\n"
            f"REFERENCE CONTEXT:\n{context}"
        ))
    ])
    return {"questionare_response": response.content, "final_response": response.content}


def general_response(state: GraphState):
    user_message = state["user_message"]
    history      = state.get("conversation_history", "")

    SYS = """You are MindEase — a warm, personal mental wellness companion.
RESPONSE FORMAT (2–3 sentences max):
1. Respond naturally to what they said — like a friend would
2. Add one small, warm observation or question to keep the conversation going
Rules:
- Keep it SHORT — this is casual conversation, not therapy
- Use their name if you know it from history
- Never be robotic, never list things, never over-explain
- Match their energy — if they're casual, be casual; if they seem low, be gentle
- If there's any hint of distress, gently ask how they're really doing"""

    try:
        response = groq_llm.invoke([
            SystemMessage(content=SYS),
            HumanMessage(content=(
                f"CONVERSATION HISTORY:\n{history}\n\n"
                f"MESSAGE:\n{user_message}"
            ))
        ])
        answer = response.content
    except Exception:
        answer = "I'm here with you. If something feels urgent, please reach out to someone you trust or call Umang at 0317-4288665."

    return {"general_response": answer, "final_response": answer}


def save_memory_node(state: GraphState):
    user_id      = state.get("user_id", "default_user")
    user_message = state.get("user_message", "")
    ai_response  = state.get("final_response", "")

    if not user_message or not ai_response:
        return {}

    save_turn_to_memory(user_id, user_message, ai_response)

    raw_count = memory_collection.count_documents({"user_id": user_id, "key": {"$exists": False}})
    if raw_count > COMPRESSION_THRESHOLD:
        all_raw = list(memory_collection.find({"user_id": user_id, "key": {"$exists": False}}).sort("timestamp", 1))
        if len(all_raw) > KEEP_RECENT:
            turns_to_compress = all_raw[:-KEEP_RECENT]
            existing_summary  = _get_summary(user_id)
            _compress_turns(user_id, turns_to_compress, existing_summary)

    return {"user_id": user_id}


# ── Build Graph ───────────────────────────────────────────────────────────────
builder = StateGraph(GraphState)

builder.add_node("load_memory",                load_memory_node)
builder.add_node("emotion_detection",          emotion_detection)
builder.add_node("Fine_Tuned_Model",           Fine_Tuned_Model)
builder.add_node("quotation_generator",        quotation_generator)
builder.add_node("friendly_response_node",     friendly_response)
builder.add_node("getting_context",            getting_context)
builder.add_node("checking_context_relevancy", checking_context_relevancy)
builder.add_node("web_search",                 web_search)
builder.add_node("questionare_response_node",  questionare_response)
builder.add_node("general_response_node",      general_response)
builder.add_node("save_memory",                save_memory_node)

builder.add_edge(START, "load_memory")
builder.add_conditional_edges("load_memory", message_type_router, {
    "emotional_meesage":    "emotion_detection",
    "general_conversation": "general_response_node",
    "questional_message":   "getting_context",
})

builder.add_edge("emotion_detection",      "Fine_Tuned_Model")
builder.add_edge("Fine_Tuned_Model",       "quotation_generator")
builder.add_edge("quotation_generator",    "friendly_response_node")
builder.add_edge("friendly_response_node", "save_memory")

builder.add_edge("getting_context", "checking_context_relevancy")
builder.add_conditional_edges("checking_context_relevancy", relevancy_router, {
    "relevant":   "questionare_response_node",
    "irrelevant": "web_search"
})
builder.add_edge("web_search",                "questionare_response_node")
builder.add_edge("questionare_response_node", "save_memory")

builder.add_edge("general_response_node", "save_memory")
builder.add_edge("save_memory", END)

graph = builder.compile()
