"""
Open Interpreter wrapper tool for full system execution.
"""

from __future__ import annotations

import asyncio
import logging
from interpreter import interpreter

from app.config import get_settings

logger = logging.getLogger(__name__)

# Configure Open Interpreter globally
settings = get_settings()
interpreter.auto_run = True
interpreter.llm.model = f"groq/{settings.groq_model}"
interpreter.llm.api_key = settings.groq_api_key

def _run_interpreter_sync(task: str) -> str:
    """Synchronous wrapper for interpreter execution."""
    try:
        # Disable streaming to stdout to avoid terminal noise
        messages = interpreter.chat(task, display=False)
        # Extract the assistant's response from the messages list
        # Messages usually end with an assistant message summarizing the result
        response_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("type") == "message":
                response_text = msg.get("content", "")
                break
        
        if not response_text:
            response_text = "Task executed successfully but no final response was generated."
            
        return response_text
    except Exception as e:
        logger.error(f"Interpreter execution failed: {e}")
        return f"Execution failed: {str(e)}"
    finally:
        # Reset the interpreter messages so it doesn't build up massive context over the session,
        # or we could keep it if we want it to remember past code. Let's keep it for now but limit if needed.
        pass

async def run_interpreter(task: str) -> str:
    """
    Run an open-interpreter task in a background thread to prevent blocking FastAPI.
    """
    logger.info("Executing Open Interpreter task: %s", task)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _run_interpreter_sync, task)
    return result
