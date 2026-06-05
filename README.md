# 🤖 Chulbul AI — Smart Bilingual Voice & Text Assistant

A modern, fully free AI assistant with a 3D audio-reactive frontend, powered by Groq's ultra-fast inference, LangGraph's agentic workflow, and completely free STT/TTS engines.

---

## ✨ Features

- **Bilingual** — Fluent in English and Hindi (Hinglish)
- **Voice + Text** — Speak or type, Chulbul responds both ways
- **3D Visualisation** — Audio-reactive orb built with React Three Fiber
- **Agentic Workflow** — LangGraph routes queries to the right tool automatically
- **Web Search** — DuckDuckGo integration (no API key needed)
- **System Tasks** — Get time, date, system info, open apps
- **Browser Automation** — Playwright-powered page reading (optional)
- **Streaming** — SSE endpoint for real-time text generation
- **100% Free** — Every component uses free-tier or open-source tools

---

## 📁 Project Structure

```
Chulbul-AI-Assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── agent.py             # LangGraph state graph
│   │   ├── config.py            # Pydantic settings
│   │   ├── models/
│   │   │   └── schemas.py       # Request/response schemas
│   │   ├── services/
│   │   │   ├── llm.py           # Groq LLM client
│   │   │   ├── tts.py           # edge-tts (Text-to-Speech)
│   │   │   └── stt.py           # faster-whisper (Speech-to-Text)
│   │   ├── tools/
│   │   │   ├── search.py        # DuckDuckGo web search
│   │   │   ├── browser.py       # Playwright browser automation
│   │   │   └── system_control.py# Safe system operations
│   │   └── utils/
│   │       └── helpers.py       # Shared utilities
│   ├── .env.example             # Environment template
│   └── requirements.txt         # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root component
│   │   ├── api.js               # Backend API client
│   │   ├── index.css            # Tailwind + design system
│   │   ├── components/
│   │   │   ├── VoiceOrb3D.jsx   # 3D audio-reactive sphere
│   │   │   ├── ChatMessage.jsx  # Chat bubble component
│   │   │   ├── ChatInput.jsx    # Input bar with mic toggle
│   │   │   └── Header.jsx       # Top nav with language switch
│   │   └── hooks/
│   │       ├── useVoiceRecorder.js  # MediaRecorder hook
│   │       └── useAudioAnalyser.js  # Web Audio API hook
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- A free **[Groq API key](https://console.groq.com)** (sign up takes 30 seconds)

---

### 1️⃣ Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy the environment template and add your Groq API key
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **http://localhost:8000**. Visit **http://localhost:8000/docs** for the interactive Swagger UI.

#### Optional: Browser Automation

```bash
# Install Playwright browsers (one-time setup)
playwright install chromium

# Enable in .env
# ENABLE_BROWSER_TOOL=true
```

---

### 2️⃣ Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at **http://localhost:5173**.

The Vite dev server is configured to proxy `/api/*` requests to the FastAPI backend on port 8000.

---

## 🔧 Configuration

All configuration is done via `backend/.env`. Key variables:

| Variable            | Default                  | Description                         |
| ------------------- | ------------------------ | ----------------------------------- |
| `GROQ_API_KEY`      | *(required)*             | Your Groq API key                   |
| `GROQ_MODEL`        | `llama-3.3-70b-versatile`| LLM model to use                   |
| `WHISPER_MODEL_SIZE`| `base`                   | STT model: tiny/base/small/medium   |
| `WHISPER_DEVICE`    | `cpu`                    | Use `cuda` for GPU acceleration     |
| `TTS_VOICE_EN`      | `en-US-GuyNeural`        | English TTS voice                   |
| `TTS_VOICE_HI`      | `hi-IN-MadhurNeural`     | Hindi TTS voice                     |
| `CORS_ORIGINS`      | `localhost:5173,3000`    | Allowed frontend origins            |
| `ENABLE_BROWSER_TOOL`| `false`                 | Enable Playwright browser tool      |

---

## 📡 API Endpoints

| Method | Path            | Description                             |
| ------ | --------------- | --------------------------------------- |
| GET    | `/health`       | Health check                            |
| POST   | `/chat`         | Text chat → full agent pipeline         |
| POST   | `/voice`        | Voice chat → transcribe + agent pipeline|
| POST   | `/chat/stream`  | SSE streaming text response             |
| GET    | `/audio/{name}` | Serve generated TTS audio files         |

---

## 🧠 Architecture

```
User Input (text/voice)
       │
       ▼
┌──────────────┐
│ process_input│   Normalize & validate
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  route_tool  │   Keyword-based intent classification
└──────┬───────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
┌──────┐  ┌──────────┐
│ skip │  │exec_tool │   Web Search / Browser / System
└──┬───┘  └────┬─────┘
   │           │
   └─────┬─────┘
         ▼
  ┌──────────────┐
  │   generate   │   Groq LLM + edge-tts
  └──────────────┘
         │
         ▼
     Response (text + audio)
```

---

## 📜 License

This project is open source. Use it, modify it, learn from it.

---

Built with ❤️ using FastAPI, LangGraph, Groq, React, and Three.js.
