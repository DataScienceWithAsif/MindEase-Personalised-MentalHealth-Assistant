"""
MindEase — Mental Health Assistant
Streamlit Web Interface
Conversations persisted in MongoDB — survive page refresh & restarts
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MindEase",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE    = "https://a-asif-mindease-api.hf.space"
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME     = os.getenv("DB_NAME", "mindease_db")

# ══════════════════════════════════════════════════════════════════════════════
#  MONGODB — CONVERSATION PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_db():
    client = MongoClient(MONGODB_URI)
    db     = client[DB_NAME]
    db["ui_conversations"].create_index("user_id")
    db["ui_conversations"].create_index("conv_id", unique=True)
    return db

db = get_db()

def db_save_conversation(user_id: str, conv_id: str, title: str, messages: list):
    """Upsert a conversation to MongoDB."""
    db["ui_conversations"].update_one(
        {"conv_id": conv_id},
        {"$set": {
            "user_id":    user_id,
            "conv_id":    conv_id,
            "title":      title,
            "messages":   messages,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )

def db_load_conversations(user_id: str) -> dict:
    """Load all conversations for this user from MongoDB."""
    docs = list(
        db["ui_conversations"]
        .find({"user_id": user_id})
        .sort("updated_at", -1)
    )
    return {
        doc["conv_id"]: {"title": doc["title"], "messages": doc["messages"]}
        for doc in docs
    }

def db_delete_conversation(conv_id: str):
    db["ui_conversations"].delete_one({"conv_id": conv_id})

# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Outfit:wght@300;400;500;600&display=swap');

:root {
  --green:   #3d7a5a;
  --green-l: #6aab89;
  --green-xl:#c8e6d5;
  --cream:   #f8f5ef;
  --warm:    #f2ece0;
  --sand:    #e8dfc8;
  --char:    #1e2620;
  --mid:     #4a5550;
  --muted:   #8a9590;
  --white:   #ffffff;
}

html, body, [class*="css"] {
  font-family: 'Outfit', sans-serif;
  background: var(--cream) !important;
  color: var(--char);
}

#MainMenu, footer { visibility: hidden; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

[data-testid="stSidebar"] {
  background: var(--char) !important;
  border-right: none !important;
}
[data-testid="stSidebar"] * { color: #c8d5cc !important; }
[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  color: #c8d5cc !important;
  border-radius: 10px !important;
  text-align: left !important;
  padding: 10px 14px !important;
  font-size: 0.85rem !important;
  transition: all 0.2s !important;
  width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(109,171,137,0.15) !important;
  border-color: rgba(109,171,137,0.3) !important;
  color: #a8d5bc !important;
}

.stButton > button {
  font-family: 'Outfit', sans-serif !important;
  font-weight: 500 !important;
  border-radius: 12px !important;
  transition: all 0.22s cubic-bezier(0.34,1.56,0.64,1) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--green), #2d6148) !important;
  color: white !important;
  border: none !important;
  box-shadow: 0 4px 20px rgba(61,122,90,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 28px rgba(61,122,90,0.4) !important;
}
.stButton > button[kind="secondary"] {
  background: white !important;
  border: 1.5px solid var(--sand) !important;
  color: var(--mid) !important;
}
.stButton > button[kind="secondary"]:hover {
  border-color: var(--green-l) !important;
  color: var(--green) !important;
  transform: translateY(-2px) !important;
}

.stTextInput > div > div > input {
  font-family: 'Outfit', sans-serif !important;
  background: white !important;
  border: 1.5px solid var(--sand) !important;
  border-radius: 14px !important;
  padding: 14px 18px !important;
  font-size: 0.95rem !important;
  color: var(--char) !important;
  box-shadow: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--green-l) !important;
  box-shadow: 0 0 0 3px rgba(106,171,137,0.15) !important;
}
.stTextInput > div > div > input::placeholder { color: var(--muted) !important; }
.stTextInput label { display: none !important; }

.block-container {
  padding-top: 2rem !important;
  padding-bottom: 2rem !important;
  max-width: 960px !important;
}

@keyframes fadeUp {
  from { opacity:0; transform:translateY(20px); }
  to   { opacity:1; transform:translateY(0); }
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
@keyframes spin  { to{transform:rotate(360deg)} }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  MOOD DATA
# ══════════════════════════════════════════════════════════════════════════════
MOODS = [
    {"key":"calm",     "emoji":"😌","label":"Calm",     "desc":"Peaceful & at ease",
     "color":"#3d7a5a","bg":"#e8f4ee","border":"#b8ddc8",
     "quote":"Within you there is a stillness and a sanctuary to which you can retreat at any time.",
     "author":"Hermann Hesse",
     "affirmation":"Your calm is your superpower. Nurture this peace — it is hard-won and deeply yours.",
     "tips":["Take a mindful walk in nature","Practice gratitude journaling","Enjoy a quiet moment of tea or coffee"]},
    {"key":"anxious",  "emoji":"😰","label":"Anxious",  "desc":"Worried or restless",
     "color":"#4a6fa5","bg":"#e8eef7","border":"#b8cce8",
     "quote":"You don't have to control your thoughts. You just have to stop letting them control you.",
     "author":"Dan Millman",
     "affirmation":"Anxiety is just excitement without breath. Slow down — you are safe in this moment.",
     "tips":["Try the 4-7-8 breathing technique","Ground yourself: name 5 things you can see","Write your worries down, then set them aside"]},
    {"key":"sad",      "emoji":"😔","label":"Sad",      "desc":"Low or heavy-hearted",
     "color":"#6b5b9e","bg":"#ede8f5","border":"#ccc0e8",
     "quote":"Even the darkest night will end and the sun will rise.",
     "author":"Victor Hugo",
     "affirmation":"Sadness is not weakness. It is your heart making room for something new.",
     "tips":["Reach out to someone you trust","Allow yourself to feel without judgment","Do one small thing that brings you comfort"]},
    {"key":"stressed", "emoji":"😤","label":"Stressed", "desc":"Overwhelmed & tense",
     "color":"#a05a3a","bg":"#f5ece8","border":"#e8c8b8",
     "quote":"Almost everything will work again if you unplug it for a few minutes — including you.",
     "author":"Anne Lamott",
     "affirmation":"You are doing more than enough. Pause. Breathe. One thing at a time.",
     "tips":["Break tasks into tiny steps","Take a 5-minute movement break","Say no to one thing on your list today"]},
    {"key":"happy",    "emoji":"😊","label":"Happy",    "desc":"Joyful & grateful",
     "color":"#8a7a2a","bg":"#f5f0e0","border":"#e0d09a",
     "quote":"Happiness is not something ready-made. It comes from your own actions.",
     "author":"Dalai Lama",
     "affirmation":"Your joy is contagious. Share it freely — the world needs exactly this.",
     "tips":["Write down what made you smile today","Share your happiness with someone","Do something kind for a stranger"]},
    {"key":"lonely",   "emoji":"🥺","label":"Lonely",   "desc":"Disconnected & isolated",
     "color":"#7a4a9e","bg":"#f0e8f5","border":"#d0b8e8",
     "quote":"You are never alone. You are eternally connected with everyone.",
     "author":"Amit Ray",
     "affirmation":"Loneliness is a signal, not a sentence. You deserve connection — reach out today.",
     "tips":["Send one message to someone you miss","Join a community around something you love","Spend time in a public space, even quietly"]},
    {"key":"numb",     "emoji":"😶","label":"Numb",     "desc":"Empty & disconnected",
     "color":"#5a6a65","bg":"#eaeded","border":"#c0ccca",
     "quote":"Feelings are just visitors. Let them come and go.",
     "author":"Mooji",
     "affirmation":"Numbness is often rest in disguise. Be gentle with yourself. Sensation will return.",
     "tips":["Try a cold shower or warm bath to reconnect","Listen to music that once moved you","Be outside — let nature do its quiet work"]},
    {"key":"hopeful",  "emoji":"🌱","label":"Hopeful",  "desc":"Optimistic & growing",
     "color":"#2a8a52","bg":"#e5f5ec","border":"#a8daba",
     "quote":"Hope is being able to see that there is light despite all of the darkness.",
     "author":"Desmond Tutu",
     "affirmation":"Hope is the seed of every beautiful thing that has ever grown. Keep planting.",
     "tips":["Set one intention for the week ahead","Visualise where you want to be in 3 months","Celebrate one small win from yesterday"]},
]

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "screen":        "mood",
        "mood":          None,
        "conversations": {},        # loaded from MongoDB
        "active_conv":   None,
        "user_id":       "user_mindease",  # replace with real auth user id
        "conv_loaded":   False,     # flag: have we loaded from MongoDB yet?
        "seed_sent":     False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Load conversations from MongoDB ONCE per session ─────────────────────────
if not st.session_state.conv_loaded:
    st.session_state.conversations = db_load_conversations(st.session_state.user_id)
    st.session_state.conv_loaded   = True
    # Restore active_conv to the most recent one if returning user
    if st.session_state.conversations and st.session_state.active_conv is None:
        st.session_state.active_conv = next(iter(st.session_state.conversations))

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=20)
def api_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        return r.status_code == 200
    except:
        return False

def save_conv(conv_id: str):
    """Save one conversation to MongoDB."""
    conv = st.session_state.conversations.get(conv_id)
    if conv:
        db_save_conversation(
            st.session_state.user_id,
            conv_id,
            conv["title"],
            conv["messages"]
        )

def new_conversation(seed_message=None):
    conv_id  = f"conv_{int(time.time())}"
    mood     = st.session_state.mood
    title    = (f"{mood['emoji']} {mood['label']} — {datetime.now().strftime('%b %d, %H:%M')}"
                if mood else f"💬 Chat — {datetime.now().strftime('%b %d, %H:%M')}")
    messages = [{"role":"user","content":seed_message}] if seed_message else []

    st.session_state.conversations[conv_id] = {"title": title, "messages": messages}
    st.session_state.active_conv = conv_id
    st.session_state.seed_sent   = False

    # Persist to MongoDB immediately
    save_conv(conv_id)
    return conv_id

def get_conv():
    cid = st.session_state.active_conv
    if cid and cid in st.session_state.conversations:
        return st.session_state.conversations[cid], cid
    return None, None

# Bubble styles
AI_BUBBLE   = ("background:white;border:1px solid #e8dfc8;border-radius:18px;"
               "border-bottom-left-radius:3px;padding:14px 18px;font-size:0.92rem;"
               "line-height:1.7;color:#1e2620;box-shadow:0 2px 12px rgba(0,0,0,0.05);max-width:82%;")
USER_BUBBLE = ("background:linear-gradient(135deg,#3d7a5a,#2d6148);color:white;"
               "border-radius:18px;border-bottom-right-radius:3px;padding:14px 18px;"
               "font-size:0.92rem;line-height:1.7;max-width:82%;"
               "box-shadow:0 4px 18px rgba(61,122,90,0.25);")

def stream_ai(message: str, stage_ph, bubble_ph):
    full = ""
    try:
        with requests.post(
            f"{API_BASE}/chat/stream",
            json={"message": message, "user_id": st.session_state.user_id},
            stream=True, timeout=120,
            headers={"Accept":"text/event-stream"}
        ) as resp:
            etype = ""
            for raw in resp.iter_lines():
                if not raw: continue
                line = raw.decode("utf-8")
                if line.startswith("event:"):
                    etype = line.split(":",1)[1].strip()
                elif line.startswith("data:"):
                    try: data = json.loads(line.split(":",1)[1].strip())
                    except: continue

                    if etype == "progress":
                        stage_ph.markdown(
                            f'<div style="display:inline-flex;align-items:center;gap:8px;'
                            f'background:#f0f7f3;border:1px solid #c8e0d0;border-radius:20px;'
                            f'padding:6px 14px;font-size:0.8rem;color:#3d7a5a;margin:4px 0;">'
                            f'<div style="width:10px;height:10px;border:2px solid #c8e0d0;'
                            f'border-top-color:#3d7a5a;border-radius:50%;'
                            f'animation:spin 0.8s linear infinite;flex-shrink:0;"></div>'
                            f'{data.get("label","")}</div>',
                            unsafe_allow_html=True
                        )
                    elif etype == "token":
                        full += data.get("text","")
                        stage_ph.empty()
                        bubble_ph.markdown(
                            f'<div style="{AI_BUBBLE}">{full}'
                            f'<span style="animation:blink 1s infinite;color:#3d7a5a;">▌</span></div>',
                            unsafe_allow_html=True
                        )
                    elif etype == "done":
                        full = data.get("response", full)
                        stage_ph.empty()
                        bubble_ph.markdown(f'<div style="{AI_BUBBLE}">{full}</div>', unsafe_allow_html=True)
                        break
                    elif etype == "error":
                        stage_ph.empty()
                        bubble_ph.error(f"⚠️ {data.get('message','Something went wrong.')}")
                        return None
    except Exception as e:
        stage_ph.empty()
        bubble_ph.error(f"Connection error: {e}")
        return None
    return full

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 24px;">
          <div style="font-family:'Lora',serif;font-size:1.5rem;font-weight:500;
               color:#d0e8da;letter-spacing:-0.01em;margin-bottom:4px;">🌿 MindEase</div>
          <div style="font-size:0.75rem;color:#5a7a68;letter-spacing:0.08em;">
            YOUR WELLNESS COMPANION
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("＋  New Conversation", key="new_conv_btn", type="primary", use_container_width=True):
            new_conversation()
            st.session_state.seed_sent = False
            st.rerun()

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.7rem;letter-spacing:0.12em;color:#3a5a48;'
            'padding:0 2px 8px;">CONVERSATIONS</div>',
            unsafe_allow_html=True
        )

        # List from MongoDB (already loaded into session_state)
        convs = sorted(
            st.session_state.conversations.items(),
            key=lambda x: x[0], reverse=True
        )

        if not convs:
            st.markdown(
                '<div style="font-size:0.82rem;color:#3a5a48;padding:8px 2px;">'
                'No conversations yet.</div>',
                unsafe_allow_html=True
            )

        for cid, conv in convs:
            is_active = cid == st.session_state.active_conv
            msg_count = len(conv["messages"])
            label     = conv["title"]
            btn_label = f"{'▶ ' if is_active else ''}{label}"

            cols = st.columns([5, 1])
            with cols[0]:
                if st.button(btn_label, key=f"conv_{cid}", use_container_width=True):
                    st.session_state.active_conv = cid
                    st.session_state.seed_sent   = True   # don't re-send seed
                    st.rerun()
            with cols[1]:
                if st.button("🗑", key=f"del_{cid}", help="Delete conversation"):
                    db_delete_conversation(cid)
                    del st.session_state.conversations[cid]
                    if st.session_state.active_conv == cid:
                        remaining = [k for k in st.session_state.conversations]
                        st.session_state.active_conv = remaining[0] if remaining else None
                    st.rerun()

            if msg_count > 0:
                st.markdown(
                    f'<div style="font-size:0.72rem;color:#3a5a48;'
                    f'padding:0 4px 8px;">{msg_count} messages</div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")

        if st.button("← Mood Check-In", key="back_mood_sb", use_container_width=True):
            st.session_state.screen = "mood"
            st.session_state.mood   = None
            st.rerun()

        ok  = api_health()
        dot = "🟢" if ok else "🔴"
        st.markdown(
            f'<div style="font-size:0.75rem;color:#3a5a48;padding:8px 2px;">'
            f'{dot} {"API Online" if ok else "API Offline"}</div>',
            unsafe_allow_html=True
        )

# ══════════════════════════════════════════════════════════════════════════════
#  SCREEN 1 — MOOD CHECK-IN
# ══════════════════════════════════════════════════════════════════════════════
def screen_mood():
    ok = api_health()
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
         margin-bottom:48px;padding-bottom:24px;border-bottom:1px solid #e8dfc8;">
      <div>
        <div style="font-family:'Lora',serif;font-size:2rem;font-weight:500;
             color:#1e2620;letter-spacing:-0.02em;">🌿 MindEase</div>
        <div style="font-size:0.8rem;color:#8a9590;margin-top:2px;letter-spacing:0.06em;">
          YOUR MENTAL WELLNESS COMPANION
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;
           background:{'#e8f5ee' if ok else '#fce8e8'};border-radius:20px;
           padding:8px 16px;border:1px solid {'#b8ddc8' if ok else '#f0b8b8'};">
        <div style="width:8px;height:8px;border-radius:50%;
             background:{'#3d7a5a' if ok else '#d05a5a'};animation:pulse 2s infinite;"></div>
        <span style="font-size:0.8rem;color:{'#2d6148' if ok else '#8a2020'};">
          {'Assistant Online' if ok else 'Connecting...'}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-bottom:52px;animation:fadeUp 0.6s ease forwards;">
      <h1 style="font-family:'Lora',serif;font-size:clamp(2rem,4vw,3rem);font-weight:400;
           color:#1e2620;line-height:1.2;margin-bottom:16px;">
        How are you feeling<br><em style="color:#3d7a5a;">right now?</em>
      </h1>
      <p style="font-size:1rem;color:#8a9590;max-width:500px;margin:0 auto;line-height:1.7;">
        Check in with yourself — no judgment, no pressure.<br>
        Choose the mood that feels most true to this moment.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Show returning user's conversation count
    conv_count = len(st.session_state.conversations)
    if conv_count > 0:
        if st.button(
            f"📂  Continue — {conv_count} previous conversation{'s' if conv_count>1 else ''} waiting",
            key="goto_history",
            type="secondary",
            use_container_width=False
        ):
            st.session_state.screen = "chat"
            st.rerun()
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    cols = st.columns(4, gap="medium")
    for i, mood in enumerate(MOODS):
        with cols[i % 4]:
            st.markdown(f"""
            <div style="background:{mood['bg']};border:1.5px solid {mood['border']};
                 border-radius:20px;padding:24px 16px 16px;text-align:center;margin-bottom:4px;">
              <div style="font-size:2.4rem;margin-bottom:10px;">{mood['emoji']}</div>
              <div style="font-size:0.95rem;font-weight:600;color:{mood['color']};
                   margin-bottom:4px;">{mood['label']}</div>
              <div style="font-size:0.78rem;color:{mood['color']};opacity:0.7;">{mood['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"I feel {mood['label']}", key=f"m_{mood['key']}",
                         use_container_width=True, type="secondary"):
                st.session_state.mood   = mood
                st.session_state.screen = "quote"
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  SCREEN 2 — QUOTE / REFLECTION
# ══════════════════════════════════════════════════════════════════════════════
def screen_quote():
    mood = st.session_state.mood
    if not mood:
        st.session_state.screen = "mood"
        st.rerun()
        return

    c1, _ = st.columns([1, 4])
    with c1:
        if st.button("← Change Mood", key="back_mood", type="secondary"):
            st.session_state.mood   = None
            st.session_state.screen = "mood"
            st.rerun()

    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center;margin-bottom:40px;animation:fadeUp 0.4s ease forwards;">
      <div style="display:inline-block;background:{mood['bg']};border:2px solid {mood['border']};
           border-radius:50px;padding:12px 28px;">
        <span style="font-size:1.6rem;">{mood['emoji']}</span>
        <span style="font-size:1rem;font-weight:600;color:{mood['color']};
             margin-left:10px;vertical-align:middle;">Feeling {mood['label']}</span>
      </div>
    </div>

    <div style="background:{mood['bg']};border:1.5px solid {mood['border']};
         border-radius:28px;padding:52px 56px 44px;margin-bottom:32px;
         position:relative;overflow:hidden;animation:fadeUp 0.5s 0.1s ease both;">
      <div style="position:absolute;top:12px;left:28px;font-family:'Lora',serif;
           font-size:8rem;line-height:1;color:{mood['color']};opacity:0.08;
           user-select:none;">"</div>
      <div style="font-family:'Lora',serif;font-size:1.55rem;font-style:italic;
           font-weight:400;color:{mood['color']};line-height:1.6;
           margin-bottom:24px;position:relative;z-index:1;">
        "{mood['quote']}"
      </div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="height:1px;width:32px;background:{mood['color']};opacity:0.3;"></div>
        <div style="font-size:0.85rem;font-weight:500;letter-spacing:0.08em;
             color:{mood['color']};opacity:0.7;text-transform:uppercase;">{mood['author']}</div>
      </div>
    </div>

    <div style="background:white;border:1px solid #e8dfc8;border-radius:20px;
         padding:28px 36px;margin-bottom:32px;animation:fadeUp 0.5s 0.2s ease both;">
      <div style="font-size:0.72rem;letter-spacing:0.14em;color:#8a9590;
           text-transform:uppercase;margin-bottom:12px;">✦ Affirmation for you</div>
      <div style="font-size:1.05rem;color:#4a5550;line-height:1.7;">{mood['affirmation']}</div>
    </div>
    """, unsafe_allow_html=True)

    tips_html = "".join([
        f'<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:12px;">'
        f'<div style="width:6px;height:6px;border-radius:50%;background:{mood["color"]};'
        f'margin-top:8px;flex-shrink:0;"></div>'
        f'<div style="font-size:0.9rem;color:#4a5550;line-height:1.6;">{tip}</div></div>'
        for tip in mood["tips"]
    ])
    st.markdown(f"""
    <div style="background:white;border:1px solid #e8dfc8;border-radius:20px;
         padding:28px 36px;margin-bottom:40px;animation:fadeUp 0.5s 0.3s ease both;">
      <div style="font-size:0.72rem;letter-spacing:0.14em;color:#8a9590;
           text-transform:uppercase;margin-bottom:16px;">✦ Gentle suggestions</div>
      {tips_html}
    </div>
    """, unsafe_allow_html=True)

    _, c, _ = st.columns([1,2,1])
    with c:
        if st.button("💬  Chat with Assistant", key="go_chat",
                     type="primary", use_container_width=True):
            seed = f"Hi, I'm feeling {mood['label'].lower()} today — {mood['desc'].lower()}."
            new_conversation(seed_message=seed)
            st.session_state.screen    = "chat"
            st.session_state.seed_sent = False
            st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1,2,1])
    with c2:
        if st.button("Continue without chatting", key="skip_chat",
                     type="secondary", use_container_width=True):
            st.session_state.screen = "mood"
            st.session_state.mood   = None
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  SCREEN 3 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
def screen_chat():
    render_sidebar()

    conv, conv_id = get_conv()
    if conv is None:
        new_conversation()
        conv, conv_id = get_conv()

    mood = st.session_state.mood

    # Header
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:16px;padding-bottom:20px;
         border-bottom:1px solid #e8dfc8;margin-bottom:24px;">
      <div style="width:52px;height:52px;background:linear-gradient(135deg,#6aab89,#3d7a5a);
           border-radius:16px;display:flex;align-items:center;justify-content:center;
           font-size:1.5rem;flex-shrink:0;box-shadow:0 4px 16px rgba(61,122,90,0.2);">🌿</div>
      <div style="flex:1;">
        <div style="font-family:'Lora',serif;font-size:1.15rem;font-weight:500;color:#1e2620;">
          MindEase Assistant
        </div>
        <div style="font-size:0.78rem;color:#3d7a5a;margin-top:2px;">
          ● Online · {conv['title']}
        </div>
      </div>
      {'<div style="background:' + mood["bg"] + ';border:1px solid ' + mood["border"] +
       ';border-radius:20px;padding:6px 16px;font-size:0.82rem;color:' + mood["color"] +
       ';">' + mood["emoji"] + ' ' + mood["label"] + '</div>' if mood else ''}
    </div>
    """, unsafe_allow_html=True)

    messages = conv["messages"]

    # Welcome bubble if no messages
    if not messages:
        st.markdown(f"""
        <div style="display:flex;gap:12px;align-items:flex-end;margin-bottom:20px;">
          <div style="width:36px;height:36px;background:linear-gradient(135deg,#6aab89,#3d7a5a);
               border-radius:12px;display:flex;align-items:center;justify-content:center;
               font-size:1rem;flex-shrink:0;">🌿</div>
          <div style="{AI_BUBBLE}">
            Hi there 🌿 I'm MindEase — your personal mental wellness companion.
            I'm here to listen without judgment and support you through whatever you're facing.
            What would you like to talk about today?
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Render all stored messages
    for msg in messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-end;gap:12px;
                 align-items:flex-end;margin-bottom:16px;">
              <div style="{USER_BUBBLE}">{msg['content']}</div>
              <div style="width:36px;height:36px;background:#e8dfc8;border-radius:12px;
                   display:flex;align-items:center;justify-content:center;
                   font-size:1rem;flex-shrink:0;">👤</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display:flex;gap:12px;align-items:flex-end;margin-bottom:16px;">
              <div style="width:36px;height:36px;background:linear-gradient(135deg,#6aab89,#3d7a5a);
                   border-radius:12px;display:flex;align-items:center;justify-content:center;
                   font-size:1rem;flex-shrink:0;">🌿</div>
              <div style="{AI_BUBBLE}">{msg['content']}</div>
            </div>
            """, unsafe_allow_html=True)

    # Auto-send seed on first open of a NEW conversation
    if (messages and messages[0]["role"] == "user"
            and len(messages) == 1
            and not st.session_state.seed_sent):
        st.session_state.seed_sent = True
        seed_msg    = messages[0]["content"]
        stage_ph    = st.empty()
        response_ph = st.empty()
        ai_response = stream_ai(seed_msg, stage_ph, response_ph)
        if ai_response:
            response_ph.empty()
            conv["messages"].append({"role":"assistant","content":ai_response})
            save_conv(conv_id)   # ← persist to MongoDB
            st.rerun()

    # Input
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.markdown('<div style="border-top:1px solid #e8dfc8;padding-top:20px;margin-top:8px;"></div>',
                unsafe_allow_html=True)

    with st.form("chat_input_form", clear_on_submit=True):
        col_input, col_btn = st.columns([6, 1])
        with col_input:
            user_input = st.text_input(
                label="message",
                placeholder="Share what's on your mind...",
                label_visibility="collapsed",
                key="msg_input"
            )
        with col_btn:
            submitted = st.form_submit_button("➤", type="primary", use_container_width=True)

    if submitted and user_input.strip():
        msg_text = user_input.strip()
        conv["messages"].append({"role":"user","content":msg_text})

        # Show user bubble
        st.markdown(f"""
        <div style="display:flex;justify-content:flex-end;gap:12px;
             align-items:flex-end;margin-bottom:16px;">
          <div style="{USER_BUBBLE}">{msg_text}</div>
          <div style="width:36px;height:36px;background:#e8dfc8;border-radius:12px;
               display:flex;align-items:center;justify-content:center;
               font-size:1rem;flex-shrink:0;">👤</div>
        </div>
        """, unsafe_allow_html=True)

        stage_ph    = st.empty()
        response_ph = st.empty()
        ai_response = stream_ai(msg_text, stage_ph, response_ph)

        if ai_response:
            response_ph.empty()
            conv["messages"].append({"role":"assistant","content":ai_response})
            save_conv(conv_id)   # ← persist to MongoDB
            st.session_state.seed_sent = True
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
screen = st.session_state.screen
if   screen == "mood":  screen_mood()
elif screen == "quote": screen_quote()
elif screen == "chat":  screen_chat()
else:
    st.session_state.screen = "mood"
    st.rerun()