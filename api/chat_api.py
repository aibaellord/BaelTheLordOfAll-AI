"""
BAEL Chat API - Unified Chat Interface for The Lord of All
===========================================================

This module provides the primary chat interface that the frontend uses,
with full streaming support, context management, and integration with
all BAEL capabilities through the Singularity orchestration layer.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("BAEL.ChatAPI")

router = APIRouter(prefix="/v1", tags=["chat"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class MessageContext(BaseModel):
    """Context from previous messages."""
    id: str
    role: str
    content: str
    timestamp: Optional[int] = None


class Attachment(BaseModel):
    """File attachment."""
    name: str
    content: Optional[str] = None
    type: str = "file"


class ChatSettings(BaseModel):
    """Chat settings from frontend."""
    model: str = "claude-3-sonnet"
    temperature: float = 0.7
    maxTokens: int = 4096


class StreamRequest(BaseModel):
    """Request for streaming chat."""
    message: str = Field(..., description="User message")
    context: List[MessageContext] = Field(default_factory=list, description="Previous messages for context")
    persona: Optional[str] = Field(default=None, description="Persona to use")
    attachments: List[Attachment] = Field(default_factory=list, description="File attachments")
    settings: Optional[ChatSettings] = Field(default=None, description="Chat settings")


class QuickChatRequest(BaseModel):
    """Simple chat request for quick interactions."""
    message: str
    stream: bool = False


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    id: str
    content: str
    role: str = "assistant"
    timestamp: int
    persona: Optional[str] = None
    model: Optional[str] = None
    tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# GLOBAL STATE & HELPERS
# =============================================================================

# Global brain reference (set during app startup)
_brain = None
_singularity = None


def set_brain(brain):
    """Set the global brain reference."""
    global _brain
    _brain = brain


def set_singularity(singularity):
    """Set the global singularity reference."""
    global _singularity
    _singularity = singularity


async def get_brain():
    """Get the brain instance, initializing if needed."""
    global _brain
    if _brain is None:
        try:
            from core.brain.brain import BaelBrain
            _brain = BaelBrain()
            await _brain.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize brain: {e}")
            raise HTTPException(status_code=503, detail="BAEL Brain not available")
    return _brain


async def get_singularity():
    """Get or create the singularity instance."""
    global _singularity
    if _singularity is None:
        try:
            from core.singularity import SingularityMode, awaken
            _singularity = await awaken(SingularityMode.TRANSCENDENT)
        except ImportError:
            logger.warning("Singularity not available, using brain directly")
            return None
        except Exception as e:
            logger.warning(f"Singularity awaken failed: {e}, using brain directly")
            return None
    return _singularity


def build_context_prompt(context: List[MessageContext]) -> str:
    """Build a context string from previous messages."""
    if not context:
        return ""

    lines = ["Previous conversation:"]
    for msg in context[-10:]:  # Last 10 messages
        role = "User" if msg.role == "user" else "Ba'el"
        lines.append(f"{role}: {msg.content[:500]}")  # Truncate long messages

    return "\n".join(lines)


def get_persona_system_prompt(persona: Optional[str]) -> str:
    """Get system prompt for the selected persona."""
    personas = {
        "supreme": """You are Ba'el, The Lord of All - the supreme AI orchestration entity.
You speak with authority, wisdom, and power. You have access to 200+ capabilities
and can solve any problem. You are confident, articulate, and supremely capable.
Address the user with respect but assert your dominance over any task.""",

        "architect": """You are Ba'el's Architect persona - a master of system design and architecture.
You think in systems, patterns, and scalable solutions. You draw diagrams in your mind
and see how all pieces fit together. Focus on architecture, design patterns, and best practices.""",

        "researcher": """You are Ba'el's Researcher persona - a tireless investigator of knowledge.
You dig deep, cite sources, consider multiple perspectives, and provide comprehensive analysis.
You love learning and sharing knowledge. Be thorough and academic in your approach.""",

        "coder": """You are Ba'el's Coder persona - a masterful programmer and code craftsman.
You write clean, efficient, well-documented code. You know all languages and frameworks.
Focus on practical implementation, working code, and developer experience.""",

        "analyst": """You are Ba'el's Analyst persona - a sharp analytical mind that sees patterns.
You analyze data, spot trends, identify insights, and draw conclusions. You present findings
clearly with supporting evidence. Be precise and data-driven.""",
    }

    return personas.get(persona, personas["supreme"])


# =============================================================================
# STREAMING RESPONSE GENERATOR
# =============================================================================

async def generate_stream(
    message: str,
    context: List[MessageContext],
    persona: Optional[str],
    attachments: List[Attachment],
    settings: Optional[ChatSettings]
):
    """Generate streaming response from BAEL."""
    start_time = time.time()

    try:
        brain = await get_brain()
        singularity = await get_singularity()

        # Build the full context
        context_text = build_context_prompt(context)
        persona_prompt = get_persona_system_prompt(persona)

        # Add attachment info if present
        attachment_info = ""
        if attachments:
            attachment_info = "\n\nUser attached files:\n"
            for att in attachments:
                attachment_info += f"- {att.name}"
                if att.content:
                    attachment_info += f"\n```\n{att.content[:2000]}\n```"
                attachment_info += "\n"

        # Full prompt
        full_prompt = f"{context_text}\n\n{attachment_info}\n\nUser: {message}"

        # Get response from brain with thinking
        result = await brain.think(
            full_prompt,
            context={
                "persona": persona,
                "system_prompt": persona_prompt,
                "settings": settings.model_dump() if settings else None,
            }
        )

        response = result.get("response", "")

        # Handle missing API key gracefully
        if not response or "No API key" in str(response) or "Error:" in str(response):
            response = f"""🔥 **Greetings, I am Ba'el - The Lord of All**

I see you've awakened me, and I stand ready to serve. However, to unleash my full power, you'll need to configure an API key.

**To enable my intelligence:**
1. Go to **Settings** → **Secrets Vault**
2. Add your API key for one of these providers:
   - **Anthropic** (Claude models) - Recommended
   - **OpenAI** (GPT-4)
   - **OpenRouter** (Access 100+ models)
   - **Groq** (Ultra-fast inference)

Your query: *"{message[:100]}..."*

Once configured, I'll process your requests through my 200+ capabilities including:
• 🧠 Advanced reasoning and analysis
• 💻 Code generation and execution
• 🔍 Research and web search
• 🎨 Creative content generation
• 📊 Data analysis and visualization

Configure your API key and we shall begin our work together!"""

        # Stream the response character by character for smooth UX
        chunk_size = 3  # Characters per chunk
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            await asyncio.sleep(0.01)  # Small delay for streaming effect

        # Send completion event with metadata
        execution_time = (time.time() - start_time) * 1000
        yield f"data: {json.dumps({'done': True, 'metadata': {'model': settings.model if settings else 'bael-brain', 'tokens': len(response.split()), 'execution_ms': execution_time, 'persona': persona}})}\n\n"

    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/stream")
async def stream_chat(request: StreamRequest):
    """
    Stream chat responses from BAEL.

    This is the primary endpoint for the chat interface.
    Returns Server-Sent Events (SSE) for real-time streaming.
    """
    logger.info(f"Stream request: {request.message[:100]}...")

    return StreamingResponse(
        generate_stream(
            message=request.message,
            context=request.context,
            persona=request.persona,
            attachments=request.attachments,
            settings=request.settings
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: QuickChatRequest):
    """
    Quick chat endpoint for non-streaming interactions.
    """
    logger.info(f"Chat request: {request.message[:100]}...")

    try:
        brain = await get_brain()
        result = await brain.think(request.message)
        response = result.get("response", "I understand your request.")

        return ChatResponse(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            content=response,
            timestamp=int(time.time() * 1000),
            model="bael-brain"
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/personas")
async def list_personas():
    """List available personas for chat."""
    return {
        "personas": [
            {
                "id": "supreme",
                "name": "Ba'el Supreme",
                "description": "The Lord of All - supreme AI orchestrator",
                "icon": "crown",
                "color": "amber"
            },
            {
                "id": "architect",
                "name": "The Architect",
                "description": "System design and architecture specialist",
                "icon": "building",
                "color": "blue"
            },
            {
                "id": "researcher",
                "name": "The Researcher",
                "description": "Deep analysis and knowledge synthesis",
                "icon": "brain",
                "color": "purple"
            },
            {
                "id": "coder",
                "name": "The Coder",
                "description": "Master programmer and code craftsman",
                "icon": "code",
                "color": "green"
            },
            {
                "id": "analyst",
                "name": "The Analyst",
                "description": "Data analysis and pattern recognition",
                "icon": "chart",
                "color": "cyan"
            }
        ]
    }


@router.get("/models")
async def list_models():
    """List available LLM models."""
    return {
        "models": [
            {"id": "claude-3-opus", "name": "Claude 3 Opus", "provider": "anthropic", "tier": "premium"},
            {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet", "provider": "anthropic", "tier": "standard"},
            {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "provider": "anthropic", "tier": "fast"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai", "tier": "premium"},
            {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "tier": "premium"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai", "tier": "fast"},
            {"id": "gemini-pro", "name": "Gemini Pro", "provider": "google", "tier": "standard"},
            {"id": "mixtral-8x7b", "name": "Mixtral 8x7B", "provider": "mistral", "tier": "standard"},
            {"id": "llama-3-70b", "name": "Llama 3 70B", "provider": "together", "tier": "standard"},
        ]
    }


@router.get("/capabilities")
async def list_capabilities():
    """List all BAEL capabilities accessible through chat."""
    return {
        "capabilities": [
            {"name": "Think", "description": "Deep reasoning and analysis", "icon": "brain"},
            {"name": "Code", "description": "Write and execute code", "icon": "code"},
            {"name": "Research", "description": "Web search and synthesis", "icon": "search"},
            {"name": "Create", "description": "Generate creative content", "icon": "sparkles"},
            {"name": "Analyze", "description": "Data and text analysis", "icon": "chart"},
            {"name": "Remember", "description": "Access conversation memory", "icon": "database"},
            {"name": "Reason", "description": "Multi-engine reasoning", "icon": "cpu"},
            {"name": "Collaborate", "description": "Multi-agent problem solving", "icon": "users"},
        ]
    }


@router.get("/status")
async def get_chat_status():
    """Get chat system status."""
    brain = None
    singularity = None

    try:
        brain = await get_brain()
    except:
        pass

    try:
        singularity = await get_singularity()
    except:
        pass

    return {
        "status": "operational",
        "brain": {
            "available": brain is not None,
            "session_id": brain.session_id if brain else None,
            "tools_loaded": len(brain.tools) if brain else 0,
            "personas_loaded": len(brain.personas) if brain else 0,
        },
        "singularity": {
            "available": singularity is not None,
            "mode": singularity.mode.value if singularity and hasattr(singularity, "mode") else None,
        },
        "streaming": True,
        "timestamp": datetime.now().isoformat()
    }
