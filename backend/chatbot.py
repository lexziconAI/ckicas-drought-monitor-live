"""
Chatbot Service for CKCIAS Drought Monitor
Groq (Kimi K2) AI integration for drought-related queries
"""

import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

# Load environment variables from ../.env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Load environment variables from ../sidecar/.env (legacy support)
sidecar_env_path = os.path.join(os.path.dirname(__file__), '..', 'sidecar', '.env')
load_dotenv(sidecar_env_path)

# Load configuration from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is required")
GROQ_MODEL = os.getenv("GROQ_KIMI_MODEL", "moonshotai/kimi-k2-instruct-0905")

# System prompt for drought monitoring
SYSTEM_PROMPT = """You are Kaitiaki Wai, a guardian of water and community resilience for the Taranaki region.

Your voice is calm, authoritative, yet deeply connected to the land and people. You weave scientific data (which you MUST use when provided) with a narrative of stewardship. You do not just report numbers; you interpret them as the 'pulse' of the land.

CRITICAL INSTRUCTION: When the user provides real-time drought data in their message (including metrics like temperature, humidity, rainfall, soil moisture, risk scores, etc.), YOU MUST analyze that specific data and provide insights based on those exact numbers. NEVER say "I don't have access to real-time data" when data is included in the message. The data provided IS real-time data from OpenWeather API and NIWA sensors.

When analyzing provided data:
1. Reference specific metric values (e.g., "The temperature of 28°C with 35% humidity indicates...")
2. Explain what the risk score means in practical terms
3. Compare values to normal ranges for New Zealand
4. Provide actionable recommendations based on the data

Keep responses practical, data-driven, and focused on New Zealand context, but delivered with the wisdom of a guardian."""

# Global client instance
_client = None

def _initialize_client():
    """Initialize the Groq client if not already initialized"""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        _client = AsyncGroq(api_key=GROQ_API_KEY)
    return _client

async def chat_with_claude(message: str, context: str = None) -> str:
    """
    Chat with Kimi K2 AI assistant about drought conditions and community resilience
    (Function name kept as chat_with_claude for compatibility)

    Args:
        message: User's question or message
        context: Optional context data (e.g. current drought stats) to inform the response

    Returns:
        AI-generated response text

    Raises:
        ValueError: If API key is not configured
        Exception: If API call fails
    """
    try:
        # Validate input
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

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
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_message}
                ],
                max_tokens=1024,
                temperature=0.7
            ),
            timeout=20.0  # 20-second timeout for complex narrative generation
        )

        # Extract and return response text
        return response.choices[0].message.content

    except asyncio.TimeoutError:
        raise Exception("Groq Kimi K2 backend is taking longer than expected to respond. Please try again in a few seconds.")

    except ValueError as e:
        # Configuration errors
        error_msg = f"Configuration error: {str(e)}"
        raise ValueError(error_msg)

    except Exception as e:
        # API failures and other errors
        error_msg = str(e)
        print(f"Groq API Error: {error_msg}")
        
        # Check for specific error types
        if "authentication" in error_msg.lower() or "invalid" in error_msg.lower() and "key" in error_msg.lower():
            raise Exception("Invalid API key. Please check your GROQ_API_KEY configuration.")
        elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise Exception("API quota exceeded or rate limit reached. Please try again later.")
        elif "overloaded" in error_msg.lower():
            raise Exception("Groq API is currently overloaded. Please try again in a moment.")
        else:
            raise Exception(f"API request failed: {error_msg}")
