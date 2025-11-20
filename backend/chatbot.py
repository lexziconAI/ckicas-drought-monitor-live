"""
Chatbot Service for CKCIAS Drought Monitor
Claude Haiku 4.5 AI integration for drought-related queries
"""

import os
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Load environment variables from ../.env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Load environment variables from ../sidecar/.env (legacy support)
sidecar_env_path = os.path.join(os.path.dirname(__file__), '..', 'sidecar', '.env')
load_dotenv(sidecar_env_path)

# Load configuration from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("ANTHROPIC_HAIKU_MODEL", "claude-haiku-4-5")

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
    """Initialize the Anthropic client if not already initialized"""
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        _client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client

async def chat_with_claude(message: str) -> str:
    """
    Chat with Claude 3 Haiku AI assistant about drought conditions and community resilience

    Args:
        message: User's question or message

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

        # Make API call to Claude
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": message}
            ]
        )

        # Extract and return response text
        return response.content[0].text

    except ValueError as e:
        # Configuration errors
        error_msg = f"Configuration error: {str(e)}"
        raise ValueError(error_msg)

    except Exception as e:
        # API failures and other errors
        error_msg = str(e)

        # Check for specific error types
        if "authentication" in error_msg.lower() or "invalid" in error_msg.lower() and "key" in error_msg.lower():
            raise Exception("Invalid API key. Please check your ANTHROPIC_API_KEY configuration.")
        elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise Exception("API quota exceeded or rate limit reached. Please try again later.")
        elif "overloaded" in error_msg.lower():
            raise Exception("Claude API is currently overloaded. Please try again in a moment.")
        else:
            raise Exception(f"API request failed: {error_msg}")
