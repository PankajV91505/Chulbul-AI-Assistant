"""
Chulbul AI — FastAPI Entry Point

Endpoints:
    GET  /health              → health check
    POST /chat                → text chat (returns JSON with optional audio URL)
    POST /voice               → legacy voice chat (accepts audio file, returns JSON)
    GET  /audio/{filename}    → serve generated TTS audio files
    POST /chat/stream         → SSE streaming text response (runs full agent)
    POST /transcribe          → [NEW] accept audio, return text instantly
    POST /tts                 → [NEW] accept text, return audio URL
"""

from __future__ import annotations

import logging
import uuid
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.config import get_settings, TEMP_AUDIO_DIR
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    Language,
    ToolName,
    TranscribeResponse,
    TTSRequest,
    TTSResponse,
)
from app.agent import agent_runnable, GraphState
from app.services.stt import transcribe
from app.services.tts import synthesize
from app.services.llm import generate_response_stream
from app.utils.helpers import generate_session_id, cleanup_old_audio

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("chulbul")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("🚀 Chulbul AI starting on %s:%d", settings.host, settings.port)
    logger.info("   Model     : %s", settings.groq_model)
    logger.info("   Whisper   : %s (%s)", settings.whisper_model_size, settings.whisper_device)
    logger.info("   CORS      : %s", settings.cors_origin_list)
    yield
    # Shutdown: clean up temp audio
    cleanup_old_audio(max_age_seconds=0)
    logger.info("👋 Chulbul AI shut down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Chulbul AI",
    description="A modern bilingual voice-and-text AI assistant.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the React dev server
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    """Basic liveness probe."""
    return HealthResponse()


@app.post("/transcribe", response_model=TranscribeResponse, tags=["voice"])
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en"),
):
    """
    Accepts an audio file and returns the transcribed text instantly.
    """
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    temp_path = TEMP_AUDIO_DIR / f"upload_{uuid.uuid4().hex[:8]}{suffix}"

    try:
        content = await audio.read()
        temp_path.write_bytes(content)

        # Transcribe
        transcribed_text, detected_lang = transcribe(str(temp_path))
        if not transcribed_text:
            raise HTTPException(
                status_code=400,
                detail="Could not transcribe the audio. Please try again.",
            )

        lang = detected_lang if detected_lang in ("en", "hi") else language
        return TranscribeResponse(text=transcribed_text, language=lang)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.post("/tts", response_model=TTSResponse, tags=["voice"])
async def text_to_speech(req: TTSRequest):
    """
    Synthesize audio from text and return the URL.
    """
    try:
        path = await synthesize(req.text, language=req.language.value)
        return TTSResponse(audio_url=f"/audio/{path.name}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/chat/stream", tags=["chat"])
async def chat_stream(req: ChatRequest):
    """
    Streaming text response via Server-Sent Events (SSE).
    This now runs the tools first, then streams the LLM response.
    """
    session_id = req.session_id or generate_session_id()

    async def event_generator():
        # Step 1: Initialize State
        state: GraphState = {
            "user_input": req.message,
            "language": req.language.value,
            "session_id": session_id,
            "selected_tool": ToolName.NONE,
            "tool_args": "",
            "tool_result": "",
            "llm_response": "",
            "audio_path": None,
            "error": None,
        }

        # Step 2: Run Agent up to tool execution using ainvoke
        # We invoke the graph but skip generation, since we want to stream that manually.
        # However, to reuse the graph, it's easier to just call the nodes directly here
        # or use LangGraph's streaming. Let's call the node functions directly to stream cleanly.
        from app.agent import process_input, route_tool, execute_tool

        state = await process_input(state)
        state = await route_tool(state)
        
        tool = state.get("selected_tool", ToolName.NONE)
        
        if tool != ToolName.NONE:
            # Yield a status message to the UI
            tool_name = tool.replace("_", " ").title()
            yield f"data: {json.dumps({'type': 'tool_status', 'tool': tool_name})}\n\n"
            
            # Execute the tool
            state = await execute_tool(state)

        # Step 3: Stream the LLM response
        context = state.get("tool_result", "")
        async for chunk in generate_response_stream(
            state["user_input"], language=req.language.value, context=context
        ):
            # Send chunks as JSON
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
        
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Ultra-Low Latency WebSocket endpoint.
    Receives audio chunks, runs STT, executes tools, and streams LLM output.
    """
    await websocket.accept()
    
    session_id = generate_session_id()
    language = "en"
    audio_buffer = bytearray()
    
    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                audio_buffer.extend(message["bytes"])
                
            elif "text" in message:
                data = json.loads(message["text"])
                msg_type = data.get("type")
                
                if msg_type == "start":
                    language = data.get("language", "en")
                    audio_buffer = bytearray()
                    
                elif msg_type == "stop":
                    # User stopped talking, process audio buffer instantly!
                    if not audio_buffer:
                        await websocket.send_json({"type": "error", "message": "No audio received"})
                        continue
                        
                    # Save to temp file for faster-whisper
                    suffix = ".webm"
                    temp_path = TEMP_AUDIO_DIR / f"ws_{uuid.uuid4().hex[:8]}{suffix}"
                    temp_path.write_bytes(audio_buffer)
                    
                    try:
                        # Transcribe
                        transcribed_text, detected_lang = transcribe(str(temp_path))
                        
                        if not transcribed_text:
                            await websocket.send_json({"type": "error", "message": "Could not transcribe audio"})
                            continue
                            
                        lang = detected_lang if detected_lang in ("en", "hi") else language
                        await websocket.send_json({"type": "transcript", "text": transcribed_text})
                    finally:
                        if temp_path.exists():
                            temp_path.unlink(missing_ok=True)
                            
                elif msg_type == "text_input":
                    transcribed_text = data.get("text", "")
                    lang = data.get("language", "en")
                    if not transcribed_text:
                        continue
                        
                else:
                    continue

                # Run Intent Routing & Tool Execution for both 'stop' and 'text_input'
                if msg_type in ("stop", "text_input"):
                    try:
                        from app.agent import process_input, route_tool, execute_tool, GraphState
                        state: GraphState = {
                            "user_input": transcribed_text,
                            "language": lang,
                            "session_id": session_id,
                            "selected_tool": ToolName.NONE,
                        }
                        
                        state = await process_input(state)
                        state = await route_tool(state)
                        tool = state.get("selected_tool", ToolName.NONE)
                        
                        if tool != ToolName.NONE:
                            tool_name = tool.replace("_", " ").title()
                            await websocket.send_json({"type": "tool_status", "tool": tool_name})
                            state = await execute_tool(state)
                            
                        # Stream LLM Response
                        context = state.get("tool_result", "")
                        async for chunk in generate_response_stream(
                            state["user_input"], language=lang, context=context
                        ):
                            await websocket.send_json({"type": "chunk", "text": chunk})
                            
                        await websocket.send_json({"type": "done"})
                        
                    except Exception as e:
                        logger.error("Processing error: %s", e)
                        await websocket.send_json({"type": "error", "message": str(e)})
                            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        try:
            await websocket.close()
        except:
            pass


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(req: ChatRequest):
    """
    Legacy text-based chat. Runs the full LangGraph pipeline.
    """
    session_id = req.session_id or generate_session_id()

    initial_state: GraphState = {
        "user_input": req.message,
        "language": req.language.value,
        "session_id": session_id,
        "selected_tool": ToolName.NONE,
    }

    result = await agent_runnable.ainvoke(initial_state)

    return ChatResponse(
        text=result.get("llm_response", ""),
        tool_used=result.get("selected_tool", ToolName.NONE),
        audio_url=None,
        session_id=session_id,
    )


@app.post("/voice", response_model=ChatResponse, tags=["chat"])
async def voice(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    session_id: str = Form(""),
):
    """
    Legacy voice-based chat.
    """
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    temp_path = TEMP_AUDIO_DIR / f"upload_{uuid.uuid4().hex[:8]}{suffix}"

    try:
        content = await audio.read()
        temp_path.write_bytes(content)

        transcribed_text, detected_lang = transcribe(str(temp_path))
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="Could not transcribe")

        lang = detected_lang if detected_lang in ("en", "hi") else language
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    sid = session_id or generate_session_id()
    initial_state: GraphState = {
        "user_input": transcribed_text,
        "language": lang,
        "session_id": sid,
        "selected_tool": ToolName.NONE,
    }

    result = await agent_runnable.ainvoke(initial_state)

    return ChatResponse(
        text=result.get("llm_response", ""),
        tool_used=result.get("selected_tool", ToolName.NONE),
        audio_url=None,
        session_id=sid,
    )


@app.get("/audio/{filename}", tags=["media"])
async def serve_audio(filename: str):
    """Serve a generated TTS audio file."""
    path = TEMP_AUDIO_DIR / filename
    if not path.exists() or not path.name.startswith("chulbul_"):
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(
        path=str(path),
        media_type="audio/mpeg",
        filename=filename,
    )
