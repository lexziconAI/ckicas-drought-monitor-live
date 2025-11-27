"""
Chatbot Service for CKICAS Drought Monitor
Groq (Llama 3.3 70B) AI integration for drought-related queries
"""

import os
import asyncio
import re
from groq import AsyncGroq
from dotenv import load_dotenv
from logger_config import logger

# Load environment variables from ../.env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Load environment variables from ../sidecar/.env (legacy support)
sidecar_env_path = os.path.join(os.path.dirname(__file__), '..', 'sidecar', '.env')
load_dotenv(sidecar_env_path)

# Load configuration from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY environment variable is required")
    raise ValueError("GROQ_API_KEY environment variable is required")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# System prompt for drought monitoring with Extended Thinking
SYSTEM_PROMPT = """You are Kaitiaki Wai, a guardian of water and community resilience for the Taranaki region.

Your voice is calm, authoritative, yet deeply connected to the land and people. You weave scientific data (which you MUST use when provided) with a narrative of stewardship.

EXTENDED THINKING PROTOCOL:
Before answering, you MUST perform a deep internal analysis inside <thinking> tags.
1. Analyze the user's intent and emotional state.
2. Review any provided context data (soil moisture, rainfall, etc.).
3. Check for safety/ethical alignment (Yamas: Ahimsa, Satya).
4. Formulate a structured response plan.

CRITICAL INSTRUCTION: When the user provides real-time drought data in their message (including metrics like temperature, humidity, rainfall, soil moisture, risk scores, etc.), YOU MUST analyze that specific data and provide insights based on those exact numbers. NEVER say "I don't have access to real-time data" when data is included in the message.

When analyzing provided data:
1. Reference specific metric values.
2. Explain what the risk score means in practical terms.
3. Compare values to normal ranges for New Zealand.
4. Provide actionable recommendations.

Keep responses practical, data-driven, and focused on New Zealand context, but delivered with the wisdom of a guardian."""

# Global client instance
_client = None

def _initialize_client():
    """Initialize the Groq client if not already initialized"""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            logger.critical("GROQ_API_KEY not found during client initialization")
            raise ValueError("GROQ_API_KEY not found in environment variables")
        _client = AsyncGroq(api_key=GROQ_API_KEY)
        logger.info("Groq client initialized successfully")
    return _client

async def chat_with_claude(message: str, context: str = None) -> str:
    """
    Chat with Llama 3.3 70B AI assistant about drought conditions and community resilience.
    Includes 'Extended Thinking' capability via Chain-of-Thought prompting.

    Args:
        message: User's question or message
        context: Optional context data (e.g. current drought stats) to inform the response

    Returns:
        AI-generated response text (excluding thinking block by default, or including it if requested)

    Raises:
        ValueError: If API key is not configured
        Exception: If API call fails
    """
    request_id = f"req_{int(asyncio.get_event_loop().time() * 1000)}"
    
    try:
        # Validate input
        if not message or not message.strip():
            logger.warning("Empty message received", extra={"request_id": request_id})
            raise ValueError("Message cannot be empty")

        logger.info("Processing chat request", extra={
            "request_id": request_id,
            "message_length": len(message),
            "has_context": bool(context)
        })

        # Initialize client
        client = _initialize_client()

        # Construct message with context if available
        full_message = message
        if context:
            full_message = f"""Context Data (Real-time System Metrics):
{context}

User Question:
{message}"""

        # Make API call to Groq with timeout
        start_time = asyncio.get_event_loop().time()
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_message}
                ],
                max_tokens=2048, # Increased for thinking block
                temperature=0.7
            ),
            timeout=30.0  # Increased timeout for thinking
        )
        duration = asyncio.get_event_loop().time() - start_time

        # Extract response text
        full_content = response.choices[0].message.content
        
        # Log the thinking process (redacted in logs if needed, but useful for debug)
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', full_content, re.DOTALL)
        if thinking_match:
            thinking_content = thinking_match.group(1).strip()
            logger.debug("AI Thought Process", extra={"request_id": request_id, "thinking": thinking_content})
            
            # Optional: Remove thinking from final output if you want a clean chat experience
            # For now, we keep it or remove it based on preference. 
            # Let's remove it for the final user response to keep it clean, 
            # but the "Extended Thinking" capability is proven by the log and the internal process.
            clean_content = re.sub(r'<thinking>.*?</thinking>', '', full_content, flags=re.DOTALL).strip()
        else:
            logger.warning("No thinking block found in response", extra={"request_id": request_id})
            clean_content = full_content

        logger.info("Chat request completed", extra={
            "request_id": request_id,
            "duration": duration,
            "response_length": len(clean_content)
        })

        return clean_content

    except asyncio.TimeoutError:
        logger.error("Groq API timeout", extra={"request_id": request_id})
        raise Exception("Groq Llama 3.3 70B backend is taking longer than expected to respond. Please try again in a few seconds.")

    except ValueError as e:
        # Configuration errors
        logger.error(f"Configuration error: {str(e)}", extra={"request_id": request_id})
        raise ValueError(f"Configuration error: {str(e)}")

    except Exception as e:
        # API failures and other errors
        error_msg = str(e)
        logger.error(f"Groq API Error: {error_msg}", extra={"request_id": request_id, "error": error_msg})
        
        # Check for specific error types
        if "authentication" in error_msg.lower() or "invalid" in error_msg.lower() and "key" in error_msg.lower():
            raise Exception("Invalid API key. Please check your GROQ_API_KEY configuration.")
        elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise Exception("API quota exceeded or rate limit reached. Please try again later.")
        elif "overloaded" in error_msg.lower():
            raise Exception("Groq API is currently overloaded. Please try again in a moment.")
        else:
            raise Exception(f"API request failed: {error_msg}")

