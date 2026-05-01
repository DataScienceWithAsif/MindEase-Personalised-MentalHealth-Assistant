<div align="center">

<img src="https://img.shields.io/badge/MindEase-Mental%20Health%20AI-3d7a5a?style=for-the-badge&logo=leaflet&logoColor=white" alt="MindEase"/>

# 🌿 MindEase — Personalised Mental Health AI Assistant

> *An intelligent, empathetic AI companion that listens, understands, and remembers — built to make mental wellness support accessible to everyone.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-FF6B35?style=flat-square&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com/atlas)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3-F55036?style=flat-square&logo=meta&logoColor=white)](https://groq.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://deepmind.google/gemini)
[![HuggingFace](https://img.shields.io/badge/HF%20Spaces-Deployed-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co/spaces)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

<br/>

**[🚀 Live API](https://a-asif-mindease-api.hf.space) · [📖 API Docs](https://a-asif-mindease-api.hf.space/docs) · [🤗 HF Space](https://huggingface.co/spaces/a-asif/mindease-api)**

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Memory System](#-memory-system)
- [LangGraph Pipeline](#-langgraph-pipeline)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)
- [Crisis Support](#-crisis-support)
- [License](#-license)

---

## 🧠 Overview

**MindEase** is an AI-powered mental health assistant designed for personalised, empathetic, and context-aware support. Unlike generic chatbots, MindEase **remembers your history**, **detects your emotional state with clinical precision**, routes your message through a specialised pipeline, and responds with the right tone — whether you need a compassionate listener, a crisis companion, or a knowledgeable guide.

Built as a **Final Year Project (FYP)**, MindEase combines state-of-the-art LLMs, a domain fine-tuned model, retrieval-augmented generation, and a production-grade memory system — all served through a streaming FastAPI backend deployed on Hugging Face Spaces.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🧠 **Clinical Emotion Detection** | Detects primary & secondary mental state, severity, crisis risk level, and emotional tone using Gemini |
| 🔀 **Intelligent Message Routing** | Classifies every message as emotional, general, or mental-health question — routes to the right pipeline |
| ⚠️ **Crisis Detection** | Keyword + LLM dual-layer crisis detection with Umang Pakistan helpline integration |
| 💬 **Streaming Responses** | Live token-by-token streaming via Server-Sent Events (SSE) — no silent waiting |
| 🧩 **Long-Term Memory** | MongoDB Atlas stores every conversation turn per user across all sessions |
| 🗜️ **Memory Compression** | LLM automatically summarises old turns when history exceeds 10 turns — preserves all personalisation context |
| 📚 **RAG Pipeline** | Pinecone vector search retrieves relevant mental health knowledge for Q&A |
| 🌐 **Web Search** | Tavily search enriches responses with current, real-world information |
| 🤖 **Fine-Tuned Model** | Domain-specific HuggingFace model trained on mental health conversations |
| 🎨 **Streamlit UI** | Mood check-in → personalised quote → full chat interface with conversation history sidebar |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│              Streamlit App  ·  Mood Check-In  ·  Chat           │
└─────────────────────┬───────────────────────────────────────────┘
                      │  POST /chat/stream  (SSE)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                               │
│             Hugging Face Spaces · Docker · Port 7860            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LANGGRAPH PIPELINE                            │
│                                                                 │
│  load_memory ──► [Router] ──────────────────────────────────┐   │
│                     │                                       │   │
│              ┌──────┼──────────┐                           │   │
│              ▼      ▼          ▼                           │   │
│         Emotional  General  Question                       │   │
│              │      │          │                           │   │
│   emotion_detection │    getting_context                  │   │
│   Fine_Tuned_Model  │    check_relevancy                  │   │
│   quotation_gen     │    [web_search if needed]           │   │
│   friendly_resp     │    questionare_resp                 │   │
│              └──────┴──────────┘                           │   │
│                      │                                     │   │
│                 save_memory ◄───────────────────────────────┘   │
│                      │                                          │
│                     END                                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
          ┌────────────┼────────────────────┐
          ▼            ▼                    ▼
    MongoDB Atlas   Pinecone            Groq / Gemini
   (Memory Store)  (Vector RAG)         (LLM APIs)
```

---

## 🛠️ Tech Stack

### Core AI & Orchestration

| Technology | Role |
|---|---|
| **LangGraph** | Stateful multi-agent graph orchestration |
| **Groq — LLaMA 3.3 70B** | Primary response generation, routing, compression |
| **Google Gemini 2.5 Flash** | Emotion detection, structured classification, RAG relevancy |
| **HuggingFace — Custom Fine-Tuned Model** | Domain-specific mental health response generation |

### Memory & Storage

| Technology | Role |
|---|---|
| **MongoDB Atlas** | Long-term conversation memory with auto-compression |
| **LangGraph Store (MongoDBStore)** | Cross-session key-value memory store |
| **LangGraph Checkpointer (MongoDBSaver)** | Thread-scoped short-term graph state |

### Knowledge Retrieval

| Technology | Role |
|---|---|
| **Pinecone** | Vector database for mental health knowledge RAG |
| **HuggingFace Embeddings** | `sentence-transformers/all-mpnet-base-v2` for vector encoding |
| **Tavily Search** | Real-time web search for quotes, news, and resources |

### Backend & Deployment

| Technology | Role |
|---|---|
| **FastAPI** | High-performance async REST API |
| **Server-Sent Events (SSE)** | Live streaming token delivery |
| **Hugging Face Spaces** | Docker-based cloud deployment |
| **Uvicorn** | ASGI server |

### Frontend

| Technology | Role |
|---|---|
| **Streamlit** | Interactive web UI |
| **Custom CSS** | Google Fonts, animations, responsive design |

---

## 📁 Project Structure

```
MindEase/
│
├── api/                          # FastAPI backend (deployed on HF Spaces)
│   ├── main.py                   # FastAPI app — all endpoints + SSE streaming
│   ├── graph.py                  # LangGraph pipeline — all nodes & edges
│   ├── memory.py                 # MongoDB memory functions + compression logic
│   ├── utilities.py              # Pinecone RAG helper
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # HF Spaces Docker config
│   └── README.md                 # HF Spaces metadata + API docs
│
├── app/
│   └── mindease_app.py           # Streamlit frontend (3 screens)
│
├── notebooks/
│   └── demo.ipynb                # Development & testing notebook
│
├── .env.example                  # Environment variable template
└── README.md                     # This file
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- MongoDB Atlas account (free M0 tier works)
- Groq API key — [console.groq.com](https://console.groq.com)
- Google AI API key — [aistudio.google.com](https://aistudio.google.com)
- Pinecone API key — [pinecone.io](https://pinecone.io)
- Tavily API key — [tavily.com](https://tavily.com)

### 1. Clone the Repository

```bash
git clone https://github.com/DataScienceWithAsif/MindEase-Personalised-MentalHealth-Assistant.git
cd MindEase-Personalised-MentalHealth-Assistant
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv mindease_env

# Windows
mindease_env\Scripts\activate

# macOS / Linux
source mindease_env/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r api/requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual keys (see Environment Variables section below)
```

### 5. Run the FastAPI Backend Locally

```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```

API will be live at: `http://localhost:7860`
Interactive docs at: `http://localhost:7860/docs`

### 6. Run the Streamlit Frontend

In a new terminal:

```bash
# Update API_BASE in mindease_app.py to http://localhost:7860
streamlit run app/mindease_app.py
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root with the following:

```env
# MongoDB Atlas
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=your-app
DB_NAME=mindease_db

# LLM APIs
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...

# Vector Search
PINECONE_API_KEY=pcsk_...

# Web Search
TAVILY_API_KEY=tvly-...
```

> ⚠️ **Never commit your `.env` file.** Add it to `.gitignore`.

---

## 📡 API Reference

Base URL: `https://a-asif-mindease-api.hf.space`

### `GET /health`
Health check — confirms the API is running.

```bash
curl https://a-asif-mindease-api.hf.space/health
# → {"status": "ok", "timestamp": 1234567890.0}
```

---

### `POST /chat/stream` ⭐ Primary Endpoint

Streaming chat via Server-Sent Events. Sends live pipeline progress + response tokens.

**Request:**
```json
{
  "message": "I've been feeling really anxious lately",
  "user_id": "user_001"
}
```

**SSE Event Stream:**
```
event: progress
data: {"stage": "load_memory", "label": "📂 Loading your memory..."}

event: progress
data: {"stage": "emotion_detection", "label": "🧠 Analysing your emotional state..."}

event: progress
data: {"stage": "friendly_response_node", "label": "💙 Crafting your response..."}

event: token
data: {"text": "I hear you — anxiety can feel "}

event: token
data: {"text": "overwhelming, especially when..."}

event: done
data: {"response": "<full response text>", "user_id": "user_001"}
```

**JavaScript Integration:**
```javascript
async function streamChat(message, userId) {
  const response = await fetch('https://a-asif-mindease-api.hf.space/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, user_id: userId })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop();

    for (const chunk of chunks) {
      const eventMatch = chunk.match(/^event: (\w+)/m);
      const dataMatch  = chunk.match(/^data: (.+)/m);
      if (!eventMatch || !dataMatch) continue;

      const event = eventMatch[1];
      const data  = JSON.parse(dataMatch[1]);

      if (event === 'progress') updateProgress(data.label);
      else if (event === 'token') appendText(data.text);
      else if (event === 'done') onComplete(data.response);
    }
  }
}
```

**Python Integration:**
```python
import requests, json

def stream_chat(message: str, user_id: str):
    response = requests.post(
        "https://a-asif-mindease-api.hf.space/chat/stream",
        json={"message": message, "user_id": user_id},
        stream=True
    )
    event = ""
    for line in response.iter_lines():
        if not line: continue
        line = line.decode("utf-8")
        if line.startswith("event:"): event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = json.loads(line.split(":", 1)[1].strip())
            if event == "progress": print(f"\r{data['label']}", end="", flush=True)
            elif event == "token":  print(data["text"], end="", flush=True)
            elif event == "done":   break

stream_chat("I feel so alone today", "user_001")
```

---

### `GET /memory/{user_id}`
Inspect stored memory for a user.

```bash
curl https://a-asif-mindease-api.hf.space/memory/user_001
# → {"user_id": "user_001", "raw_turns": 4, "summary_exists": false, "summary": null}
```

---

### `DELETE /memory/{user_id}`
Clear all memory for a user.

```bash
curl -X DELETE https://a-asif-mindease-api.hf.space/memory/user_001
# → {"message": "Memory cleared for user_001"}
```

---

## 🧠 Memory System

MindEase uses a **two-tier memory architecture** backed by MongoDB Atlas:

### Tier 1 — Raw Conversation Turns
Every message exchange is stored as a document:
```json
{
  "user_id": "user_001",
  "user_message": "I've been struggling with sleep",
  "ai_response": "I hear you — poor sleep and anxiety often feed each other...",
  "timestamp": "2026-04-30T12:34:56Z"
}
```

### Tier 2 — Compressed Summary
When raw turns exceed **10**, the oldest turns (all except the last 5) are summarised by the LLM and stored as a single summary document. The summary is **merged** with any existing summary — no detail is ever lost.

```
Raw turns: 14
         ↓  trigger compression
Turns 1–9  → LLM summarises → summary doc (merged with previous summary)
Turns 10–14 → kept as raw turns
         ↓  next turn
AI receives: [summary] + [last 5 raw turns]
```

**What the summary preserves:**
- Name, age, location, relationships
- Emotional history — what helped, what hurt, breakthroughs
- Communication preferences and coping methods
- Any detail relevant to future personalisation

---

## 🔀 LangGraph Pipeline

Each user message flows through a directed graph with three specialised paths:

```
load_memory (always first)
     │
     ▼
[message_type_router]
     │
     ├── emotional_message ──► emotion_detection
     │                              │
     │                         Fine_Tuned_Model
     │                              │
     │                         quotation_generator
     │                              │
     │                         friendly_response_node ──┐
     │                                                  │
     ├── general_conversation ──► general_response_node ─┤
     │                                                  │
     └── mental_health_question ──► getting_context      │
                                        │               │
                                  check_relevancy        │
                                        │               │
                              ┌─────────┴──────┐        │
                              ▼                ▼        │
                       questionare_      web_search     │
                       response_node ────────────────┐  │
                                                     │  │
                                              save_memory ◄─┘
                                                     │
                                                    END
```

### Node Descriptions

| Node | Model | Purpose |
|---|---|---|
| `load_memory` | — | Loads conversation history + summary from MongoDB |
| `message_type_router` | Groq LLaMA | Classifies message: emotional / general / question |
| `emotion_detection` | Gemini | Detects mental state, severity, crisis risk, emotional tone |
| `Fine_Tuned_Model` | HF Model | Generates domain-specific therapeutic reference response |
| `quotation_generator` | Groq + Tavily | Finds relevant motivational quotes via web search |
| `friendly_response_node` | Groq LLaMA | Generates empathetic response (3 modes: crisis / severe / general) |
| `getting_context` | Pinecone | Retrieves relevant mental health knowledge chunks |
| `checking_context_relevancy` | Gemini | Scores whether retrieved context is relevant |
| `web_search` | Tavily | Falls back to live web search if Pinecone context is weak |
| `questionare_response_node` | Groq LLaMA | Answers mental health questions using retrieved context |
| `general_response_node` | Groq LLaMA | Responds to casual conversation with memory-aware personalisation |
| `save_memory` | — | Saves turn to MongoDB, triggers compression if needed |

---

## ☁️ Deployment

### Deploy on Hugging Face Spaces (Docker)

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space)
   - SDK: **Docker**
   - App port: **7860**

2. Upload all files from the `api/` folder to your Space

3. Add secrets in **Space Settings → Repository Secrets:**

   | Secret | Value |
   |---|---|
   | `MONGODB_URI` | Your Atlas connection string |
   | `DB_NAME` | `mindease_db` |
   | `GROQ_API_KEY` | Your Groq key |
   | `GOOGLE_API_KEY` | Your Google AI key |
   | `PINECONE_API_KEY` | Your Pinecone key |
   | `TAVILY_API_KEY` | Your Tavily key |

4. Space will auto-build and deploy — your API will be live at:
   ```
   https://<your-username>-<space-name>.hf.space
   ```

### Deploy Streamlit Frontend

Update `API_BASE` in `mindease_app.py` to your deployed HF Space URL, then:

```bash
# Local
streamlit run app/mindease_app.py

# Streamlit Community Cloud
# Connect your GitHub repo at share.streamlit.io
```

---

## 🗺️ Roadmap

- [x] LangGraph multi-agent pipeline
- [x] MongoDB long-term memory with compression
- [x] Clinical emotion detection (severity + crisis risk)
- [x] Crisis detection with helpline integration
- [x] Pinecone RAG for mental health Q&A
- [x] FastAPI streaming backend on HF Spaces
- [x] Streamlit frontend with mood check-in
- [ ] User authentication & personalised profiles
- [ ] Voice input / voice response (TTS)
- [ ] Mobile app (React Native)
- [ ] Dashboard with mood trends & analytics
- [ ] Therapist handoff / escalation system
- [ ] Multi-language support (Urdu, Arabic)

---

## 🆘 Crisis Support

MindEase includes automatic crisis detection. If you or someone you know is in immediate distress:

> 🇵🇰 **Umang Pakistan Helpline:** `0317-4288665`
>
> Available 24/7 — free, confidential, and compassionate support.

---

## 👨‍💻 Author

**Asif** — Final Year AI/Data Science Student

[![GitHub](https://img.shields.io/badge/GitHub-DataScienceWithAsif-181717?style=flat-square&logo=github)](https://github.com/DataScienceWithAsif)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-a--asif-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co/a-asif)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

*Built with 💚 for mental wellness — because everyone deserves to be heard.*

**🌿 MindEase — Your Wellness Companion**

</div>
