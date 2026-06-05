"""
LangGraph Agent — the cognitive core of Chulbul.

Defines a state graph with four nodes:
  1. process_input  → normalize and validate user input
  2. route_tool     → decide which tool (if any) to invoke
  3. execute_tool   → run the selected tool and capture output
  4. generate       → call Groq LLM (with optional tool context) and TTS

The graph is compiled into a runnable that the FastAPI layer invokes.
"""

from __future__ import annotations

import logging
import re
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END

from app.models.schemas import Language, ToolName
from app.services.llm import generate_response
from app.services.tts import synthesize
from app.tools.search import web_search
from app.tools.browser import browse_url
from app.tools.system_control import run_system_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State schema — LangGraph uses TypedDict, not Pydantic
# ---------------------------------------------------------------------------
class GraphState(TypedDict, total=False):
    user_input: str
    language: str                # "en" | "hi"
    session_id: str
    selected_tool: str           # ToolName value
    tool_args: str               # extra args for tools
    tool_result: str
    llm_response: str
    audio_path: str | None
    error: str | None


# ---------------------------------------------------------------------------
# Node 1: Process Input
# ---------------------------------------------------------------------------
async def process_input(state: GraphState) -> GraphState:
    """
    Normalise whitespace and validate that we have non-empty input.
    """
    raw = state.get("user_input", "").strip()
    if not raw:
        return {**state, "error": "Empty input received."}
    # Collapse multiple spaces / newlines
    cleaned = re.sub(r"\s+", " ", raw)
    logger.info("[process_input] input=%r lang=%s", cleaned[:80], state.get("language"))
    return {**state, "user_input": cleaned}


async def route_tool(state: GraphState) -> GraphState:
    """
    Uses the LLM to classify user intent into a specific tool and arguments.
    """
    from app.services.llm import classify_intent
    text = state.get("user_input", "")
    
    logger.info("Classifying intent for: %s", text)
    intent = await classify_intent(text)
    
    return {
        **state,
        "selected_tool": intent["tool"],
        "tool_args": intent["args"],
    }


# ---------------------------------------------------------------------------
# Node 3: Execute Tool
# ---------------------------------------------------------------------------
async def execute_tool(state: GraphState) -> GraphState:
    """
    Dispatch to the correct tool based on the routing decision.
    """
    tool = state.get("selected_tool", ToolName.NONE)
    args = state.get("tool_args", "")

    if tool == ToolName.NONE:
        return {**state, "tool_result": ""}

    try:
        if tool == ToolName.WEB_SEARCH:
            result = await web_search(args)

        elif tool == ToolName.BROWSER:
            if not args:
                result = "No URL provided for browser automation."
            else:
                result = await browse_url(args)

        elif tool == ToolName.SYSTEM:
            parts = args.split("|", 1)
            action = parts[0].strip()
            extra = parts[1].strip() if len(parts) > 1 else ""
            result = await run_system_task(action, args=extra)

        else:
            result = ""

        logger.info("[execute_tool] tool=%s result_len=%d", tool, len(result))
        return {**state, "tool_result": result}

    except Exception as exc:
        logger.error("[execute_tool] %s failed: %s", tool, exc)
        return {**state, "tool_result": f"Tool error: {exc}"}


# ---------------------------------------------------------------------------
# Node 4: Generate Response
# ---------------------------------------------------------------------------
async def generate(state: GraphState) -> GraphState:
    """
    Call Groq LLM (with tool context if available).
    """
    if state.get("error"):
        return state

    language = state.get("language", "en")
    context = state.get("tool_result", "")
    user_msg = state.get("user_input", "")

    try:
        llm_text = await generate_response(
            user_msg,
            language=language,
            context=context,
        )
    except Exception as exc:
        logger.error("[generate] LLM call failed: %s", exc)
        llm_text = (
            "Sorry, I encountered an error generating a response."
            if language == "en"
            else "Maaf kijiye, jawab banane mein error aa gaya."
        )

    return {
        **state,
        "llm_response": llm_text,
        "audio_path": None,
    }


# ---------------------------------------------------------------------------
# Conditional edge: skip tool execution when no tool is selected
# ---------------------------------------------------------------------------
def _should_execute_tool(state: GraphState) -> str:
    """Return next node name based on whether a tool was selected."""
    if state.get("error"):
        return "generate"           # skip straight to output on error
    if state.get("selected_tool", ToolName.NONE) == ToolName.NONE:
        return "generate"           # no tool → go to LLM directly
    return "execute_tool"


# ---------------------------------------------------------------------------
# Build & compile the graph
# ---------------------------------------------------------------------------
def build_agent_graph() -> StateGraph:
    """
    Construct the LangGraph state graph.

    Flow:
        process_input → route_tool ─┬─ (tool needed)   → execute_tool → generate → END
                                    └─ (no tool / err) → generate      → END
    """
    graph = StateGraph(GraphState)

    # Register nodes
    graph.add_node("process_input", process_input)
    graph.add_node("route_tool", route_tool)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("generate", generate)

    # Edges
    graph.set_entry_point("process_input")
    graph.add_edge("process_input", "route_tool")

    # Conditional branch after routing
    graph.add_conditional_edges(
        "route_tool",
        _should_execute_tool,
        {
            "execute_tool": "execute_tool",
            "generate": "generate",
        },
    )

    graph.add_edge("execute_tool", "generate")
    graph.add_edge("generate", END)

    return graph


# ---------------------------------------------------------------------------
# Pre-compiled runnable (import this in main.py)
# ---------------------------------------------------------------------------
agent_graph = build_agent_graph()
agent_runnable = agent_graph.compile()
