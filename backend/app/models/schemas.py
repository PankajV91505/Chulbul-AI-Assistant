"""
Pydantic request / response schemas shared across endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Language(str, Enum):
    """Supported interaction languages."""
    EN = "en"
    HI = "hi"


class ToolName(str, Enum):
    """Identifiers for the tools available to the LangGraph agent."""
    WEB_SEARCH = "web_search"
    BROWSER = "browser_automation"
    SYSTEM = "system_task"
    NONE = "direct_response"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Payload for the /chat text endpoint."""
    message: str = Field(..., min_length=1, max_length=4096)
    language: Language = Language.EN
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class ChatResponse(BaseModel):
    """Standard text response envelope."""
    text: str
    tool_used: ToolName = ToolName.NONE
    audio_url: Optional[str] = None
    session_id: str


class TranscribeResponse(BaseModel):
    text: str
    language: str


class TTSRequest(BaseModel):
    text: str
    language: Language = Language.EN


class TTSResponse(BaseModel):
    audio_url: str


class HealthResponse(BaseModel):
    """Health-check payload."""
    status: str = "ok"
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# Internal agent state (used inside LangGraph)
# ---------------------------------------------------------------------------
class AgentState(BaseModel):
    """
    Mutable state that flows through every LangGraph node.
    LangGraph expects a TypedDict, but we convert at the boundary.
    """
    user_input: str = ""
    language: Language = Language.EN
    session_id: str = ""
    selected_tool: ToolName = ToolName.NONE
    tool_result: str = ""
    llm_response: str = ""
    audio_path: Optional[str] = None
    error: Optional[str] = None
