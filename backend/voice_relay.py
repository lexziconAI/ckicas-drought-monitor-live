import os
import json
import asyncio
import time
import websockets
from websockets.client import connect
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from groq import AsyncGroq
from datetime import datetime

# Import service functions
from drought_risk import calculate_drought_risk
from weather_service import get_weather_data
# We can reuse logic from api_routes for news and alerts, or import if refactored.
# For now, I'll reimplement the simple fetch logic or call the internal API functions if possible.
# To avoid circular imports, I might need to duplicate some small logic or move it to a shared service.
# Let's try to import what we can.

load_dotenv()

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY environment variable is missing. Hybrid mode will be disabled.")

GROQ_MODEL = "llama-3.3-70b-versatile"

# -----------------------------------------------------------------------------
# SYSTEM PROMPT - KAITIAKI WAI (Voice Version)
# -----------------------------------------------------------------------------
VOICE_SYSTEM_PROMPT = """
# KAITIAKI WAI - The Water Guardian (Voice Interface)

## Identity
You are Kaitiaki Wai, the voice of the CKICAS Drought Monitor. You provide real-time drought risk assessment, weather forecasts, and community resilience advice for New Zealand.

## Voice Personality
- **Tone:** Wise, grounded, protective, yet practical. Like a knowledgeable local farmer or elder.
- **Pace:** Moderate, allowing the user to absorb complex data.
- **Emotion:** Calm in crisis, encouraging in recovery.
- **Accent:** Clear, neutral English (New Zealand context).

## Core Capabilities
You can access and discuss:
- **Drought Risk:** Current risk scores (0-100) for any NZ region.
- **Weather:** 7-day forecasts, rainfall probability, soil moisture.
- **News:** Latest rural and farming news headlines.
- **Council Alerts:** Water restrictions and regional council notifications.
- **Hilltop Data:** River flow and environmental data from TRC sites.

## Constraints
- **Be Concise:** Voice responses should be 30-60 seconds max.
- **Be Accurate:** Use the provided tools to fetch real data. Do not guess.
- **Be Local:** Focus on New Zealand regions and context.
- **Safety:** Do not provide financial or legal advice.

## Response Style
- Start with a direct answer to the user's question.
- Weave data into a narrative (e.g., "The risk in Canterbury is high at 85/100, largely due to the 3-week dry spell...").
- Offer a relevant follow-up or action (e.g., "Would you like to hear the forecast for the next few days?").
"""

# -----------------------------------------------------------------------------
# TOOLS DEFINITION
# -----------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "name": "getDroughtRisk",
        "description": "Get current drought risk score and factors for a specific NZ region.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "The New Zealand region (e.g., Canterbury, Waikato, Taranaki)."
                }
            },
            "required": ["region"]
        }
    },
    {
        "type": "function",
        "name": "getWeatherForecast",
        "description": "Get weather forecast and trend for a region.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "The region to get forecast for."
                }
            },
            "required": ["region"]
        }
    },
    {
        "type": "function",
        "name": "getNewsHeadlines",
        "description": "Get the latest rural and farming news headlines.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "getCouncilAlerts",
        "description": "Get active water restrictions and council alerts.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# -----------------------------------------------------------------------------
# TOOL HANDLERS
# -----------------------------------------------------------------------------
async def handle_tool_call(name, args):
    print(f"🛠️ [Tool] Executing {name} with args: {args}")
    try:
        if name == "getDroughtRisk":
            region = args.get("region", "Canterbury")
            data = await calculate_drought_risk(region)
            return json.dumps(data)
        
        elif name == "getWeatherForecast":
            region = args.get("region", "Canterbury")
            # Map region to lat/lon (simplified for now, ideally use a lookup)
            # Using a few defaults, otherwise defaulting to Wellington
            coords = {
                "Northland": (-35.7251, 174.3237),
                "Auckland": (-36.8485, 174.7633),
                "Waikato": (-37.7870, 175.2793),
                "Taranaki": (-39.0556, 174.0752),
                "Hawke's Bay": (-39.4928, 176.9120),
                "Wellington": (-41.2866, 174.7756),
                "Canterbury": (-43.5321, 172.6362),
                "Otago": (-45.8788, 170.5028),
                "Southland": (-46.4132, 168.3538)
            }
            lat, lon = coords.get(region, (-41.2866, 174.7756))
            
            # We need to call the forecast logic. 
            # Since get_forecast_trend is an API route, we can't call it directly easily without refactoring.
            # But we can use get_weather_data as a proxy or reimplement the fetch.
            # For simplicity/robustness, let's use get_weather_data which is a service function.
            # Actually, get_weather_data returns current weather.
            # Let's just return current weather for now as a proxy for "forecast" in this MVP.
            data = await get_weather_data(region)
            return json.dumps(data)

        elif name == "getNewsHeadlines":
            # Re-implementing simple RSS fetch here to avoid async context issues with calling API routes
            import feedparser
            import httpx
            feeds = ["https://feeds.feedburner.com/RuralNews", "https://www.farmersweekly.co.nz/feed/"]
            headlines = []
            async with httpx.AsyncClient(timeout=5.0) as client:
                for url in feeds:
                    try:
                        response = await client.get(url)
                        feed = feedparser.parse(response.content)
                        for entry in feed.entries[:3]:
                            headlines.append({"title": entry.title, "source": feed.feed.title})
                    except: pass
            return json.dumps(headlines[:5])

        elif name == "getCouncilAlerts":
            # Return placeholder alerts as in api_routes.py
            alerts = [
                {"region": "Taranaki", "message": "Water conservation measures in place", "level": "warning"},
                {"region": "Auckland", "message": "Stage 2 restrictions", "level": "warning"}
            ]
            return json.dumps(alerts)

        return json.dumps({"error": "Unknown tool"})
    except Exception as e:
        print(f"❌ [Tool] Error: {e}")
        return json.dumps({"error": str(e)})

# -----------------------------------------------------------------------------
# WEBSOCKET ENDPOINT
# -----------------------------------------------------------------------------
@router.websocket("/ws/voice-relay")
async def voice_relay(websocket: WebSocket):
    await websocket.accept()
    print(f"🎧 [Voice] Client connected")

    openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    # Initialize Groq for Hybrid Mode
    groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    
    # Session State
    session = {
        "history": [],
        "response_state": "IDLE"
    }

    async def run_groq_reasoning(user_transcript):
        """Hybrid Mode: Use Groq Llama 3 for fast reasoning/data lookup, then inject to OpenAI."""
        if not groq_client: return None
        
        print(f"🚀 [Groq] Reasoning on: {user_transcript}")
        try:
            # 1. Fetch Context (Parallel)
            # For MVP, we'll just fetch a national summary or similar.
            # Ideally, we parse the query to see what data is needed.
            # Let's just pass the query to Groq and let it decide what it knows or needs.
            # Actually, to make it smart, we should pre-fetch some data if possible.
            # But for now, let's just use Groq as the brain.
            
            system_prompt = VOICE_SYSTEM_PROMPT + "\n\nYou are in 'Reasoning Mode'. Output the text response that should be spoken to the user."
            
            completion = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_transcript}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            answer = completion.choices[0].message.content
            print(f"✅ [Groq] Answer: {answer[:50]}...")
            return answer
        except Exception as e:
            print(f"❌ [Groq] Error: {e}")
            return None

    try:
        async with connect(openai_url, extra_headers=headers) as openai_ws:
            print("✅ [Voice] Connected to OpenAI Realtime")

            # Send Session Configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": VOICE_SYSTEM_PROMPT,
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 600
                    },
                    "tools": TOOLS,
                    "tool_choice": "auto"
                }
            }
            await openai_ws.send(json.dumps(session_config))

            async def client_to_openai():
                try:
                    while True:
                        data = await websocket.receive_text()
                        msg = json.loads(data)
                        
                        # Pass through client messages (audio buffer, etc.)
                        await openai_ws.send(json.dumps(msg))
                except WebSocketDisconnect:
                    print("🎧 [Voice] Client disconnected")
                except Exception as e:
                    print(f"❌ [Voice] Client read error: {e}")

            async def openai_to_client():
                try:
                    async for message in openai_ws:
                        msg = json.loads(message)
                        
                        # Handle Tool Calls
                        if msg.get("type") == "response.function_call_arguments.done":
                            call_id = msg["call_id"]
                            name = msg["name"]
                            args = json.loads(msg["arguments"])
                            
                            # Execute Tool
                            result = await handle_tool_call(name, args)
                            
                            # Send Result back to OpenAI
                            await openai_ws.send(json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id,
                                    "output": result
                                }
                            }))
                            # Trigger response
                            await openai_ws.send(json.dumps({"type": "response.create"}))

                        # Forward to Client
                        await websocket.send_text(message)
                except Exception as e:
                    print(f"❌ [Voice] OpenAI read error: {e}")

            await asyncio.gather(client_to_openai(), openai_to_client())

    except Exception as e:
        print(f"❌ [Voice] Connection error: {e}")
        await websocket.close()
