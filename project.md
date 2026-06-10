# Chulbul AI Project Documentation

## Overview
Chulbul AI is a modern, fully free AI assistant with a 3D audio-reactive frontend, powered by Groq's ultra-fast inference, LangGraph's agentic workflow, and completely free STT/TTS engines. It's a bilingual (English/Hindi) voice and text assistant with agentic capabilities that can route queries to appropriate tools automatically.

## Key Features

- **Bilingual Support**: Fluent in English and Hindi (Hinglish)
- **Multi-modal Interaction**: Voice + Text input/output
- **3D Visualization**: Audio-reactive orb built with React Three Fiber
- **Agentic Workflow**: LangGraph routes queries to the right tool automatically
- **Web Search**: DuckDuckGo integration (no API key needed)
- **System Tasks**: Get time, date, system info, open apps
- **Browser Automation**: Playwright-powered page reading (optional)
- **Code Interpreter**: Open Interpreter integration for executing code and system tasks
- **Streaming**: SSE endpoint for real-time text generation
- **100% Free Stack**: Every component uses free-tier or open-source tools

## Architecture

### Backend (FastAPI + LangGraph)
- **main.py**: FastAPI entry point with REST and WebSocket endpoints
- **agent.py**: LangGraph state graph defining the agent workflow
- **Tools**: 
  - Web Search (DuckDuckGo)
  - Browser Automation (Playwright)
  - System Control (Safe OS operations)
  - Interpreter (Open Interpreter for code execution)
- **Services**:
  - LLM (Groq API integration)
  - STT (faster-whisper)
  - TTS (edge-tts)
- **Models**: Pydantic schemas for request/response validation

### Frontend (React + Three.js)
- **App.jsx**: Root component managing state and WebSocket connection
- **Components**:
  - Header: Language switch and branding
  - VoiceOrb3D: 3D audio-reactive visualization
  - ChatMessage: Chat bubble display
  - ChatInput: Input bar with mic toggle
- **Hooks**:
  - useVoiceRecorder: MediaRecorder API wrapper
  - useAudioAnalyser: Web Audio API for frequency analysis
  - useWakeWord: Wake word detection
  - useWebSocketChat: Real-time communication with backend

## Data Flow

### Text Chat Flow
1. User sends text via ChatInput
2. Frontend sends text through WebSocket (`text_input` message)
3. Backend receives message at `/ws/chat` endpoint
4. Message goes through LangGraph agent:
   - `process_input`: Normalizes and validates input
   - `route_tool`: LLM classifies intent and selects tool
   - `execute_tool`: Runs selected tool (if any)
   - `generate`: Creates LLM response with tool context
5. Response streamed back via WebSocket chunks
6. Frontend displays response and uses native TTS for audio output

### Voice Chat Flow
1. User speaks into microphone
2. Frontend captures audio via MediaRecorder
3. Audio chunks sent via WebSocket binary messages
4. Backend receives audio and transcribes with faster-whisper
5. Transcribed text processed same as text chat flow
6. Response streamed back and played via native browser TTS

## Tool System

### Available Tools
1. **web_search**: Searches DuckDuckGo for current information
2. **browser**: Automates Playwright to browse and extract content from URLs
3. **system**: Performs safe system operations (time, date, open apps, etc.)
4. **interpreter**: Executes code and system commands via Open Interpreter
5. **none**: Direct LLM response without tool usage

### Tool Selection
The LLM classifier in `llm.py::classify_intent` determines which tool to use based on user intent:
- **web_search**: For news, weather, current facts
- **browser**: For reading/scraping URL contents
- **system**: For local commands (time, open apps, file listing)
- **interpreter**: For complex OS tasks, code execution, file operations
- **none**: For general knowledge questions answerable directly

## Configuration

### Environment Variables (.env)
- `GROQ_API_KEY`: Groq API key (required)
- `GROQ_MODEL`: LLM model (default: llama-3.3-70b-versatile)
- `GROQ_TEMPERATURE`: Sampling temperature (default: 0.6)
- `GROQ_MAX_TOKENS`: Max tokens per response (default: 2048)
- `WHISPER_MODEL_SIZE`: STT model size (tiny/base/small/medium)
- `WHISPER_DEVICE`: STT device (cpu/cuda)
- `TTS_VOICE_EN`: English TTS voice
- `TTS_VOICE_HI`: Hindi TTS voice
- `HOST`: Backend host (default: 0.0.0.0)
- `PORT`: Backend port (default: 8000)
- `CORS_ORIGINS`: Allowed frontend origins
- `ENABLE_BROWSER_TOOL`: Enable Playwright browser automation

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Groq API key (free at console.groq.com)

### Backend Setup
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Text chat (JSON response) |
| POST | `/voice` | Voice chat (file upload) |
| POST | `/chat/stream` | SSE streaming text response |
| POST | `/transcribe` | Audio to text transcription |
| POST | `/tts` | Text to audio synthesis |
| GET | `/audio/{filename}` | Serve generated TTS audio |
| WS | `/ws/chat` | WebSocket for real-time chat |

## Development Guidelines

### Code Style
- Follow existing code patterns in the repository
- Use TypeScript-like prop checking in React components
- Keep functions focused and single-responsibility
- Add proper error handling with logging
- Write async/await for asynchronous operations

### Adding New Tools
1. Create new tool module in `backend/app/tools/`
2. Implement async function following existing patterns
3. Import and add to tool dispatch in `agent.py::execute_tool`
4. Add tool name to `ToolName` enum in `schemas.py`
5. Update LLM intent classification prompt in `llm.py::classify_intent`
6. Add any necessary configuration to `config.py` and `.env.example`

### State Management
- LangGraph uses `TypedDict` for state (`GraphState` in agent.py)
- Frontend uses React hooks for local state
- WebSocket maintains real-time communication layer
- Session IDs track conversation context

## Security Considerations

### System Tool Security
- Whitelist-based approach for system operations
- Only predefined actions allowed in `ALLOWED_ACTIONS`
- App whitelist restricts which applications can be opened
- No arbitrary shell command execution

### Data Privacy
- All processing happens locally except Groq API calls
- Audio processing is client-side when possible
- No persistent storage of conversations by default
- Temporary audio files cleaned up regularly

## Troubleshooting

### Common Issues
1. **Groq Rate Limits**: Wait and retry, check API key validity
2. **WebSocket Connection Failures**: Verify backend is running on correct port
3. **Microphone Access**: Ensure browser permissions granted
4. **Missing Dependencies**: Run `pip install -r requirements.txt` and `npm install`
5. **Browser Tool Not Working**: Install Playwright browsers with `playwright install chromium`

### Debugging
- Backend logs show agent processing steps
- Frontend React DevTools useful for component inspection
- WebSocket messages visible in browser network tab
- Test endpoints directly with tools like curl or Postman

## Future Enhancements

### Planned Features
- Memory persistence for conversation history
- Additional language support (beyond English/Hindi)
- More sophisticated agent planning and reasoning
- Enhanced 3D visualizations and animations
- Mobile application versions
- Integration with smart home devices
- Custom skill/system prompt system

### Technical Improvements
- Optimize audio processing pipeline
- Add fallback mechanisms for service failures
- Implement request rate limiting and caching
- Improve error recovery and graceful degradation
- Add comprehensive test suite