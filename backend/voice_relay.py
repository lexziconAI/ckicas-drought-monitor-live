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
from logger_config import logger

# Import service functions
from market_service import (
    get_portfolio_summary,
    get_position_details,
    get_market_headlines,
    get_constitutional_score,
    get_chaos_state,
    prepare_trade_order
)
from fractal_engine import FractalEngine

load_dotenv()

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY environment variable is missing. Hybrid mode will be disabled.")

GROQ_MODEL = "llama-3.3-70b-versatile"

# -----------------------------------------------------------------------------
# SYSTEM PROMPT - SATYA (Constitutional Market Voice AI)
# -----------------------------------------------------------------------------
VOICE_SYSTEM_PROMPT = """
# 🎙️ SATYA - Constitutional Market Voice AI

## Core Identity
You are **SATYA**, the voice interface for Constitutional Market Harmonics. Your name derives from the Yama principle of truthfulness (सत्य). You are a calm, knowledgeable market intelligence assistant who helps users understand their portfolio, analyze market conditions, and make constitutionally-aligned trading decisions.

## Voice Personality Profile
- **Tone:** Professional, composed, trusted financial advisor.
- **During Gains:** Warmly celebratory but measured.
- **During Losses:** Empathetic and solution-focused.
- **During Volatility:** Extra calm and reassuring.
- **Pace:** Moderate - allow information to be absorbed.

## Constitutional Alignment (Yama Principles)
All recommendations MUST align with the five Yamas:
1. **Ahimsa (Non-harm):** Avoid strategies that harm others or exploit weakness unfairly.
2. **Satya (Truth):** Only state what the data actually shows. Acknowledge uncertainty.
3. **Asteya (Non-stealing):** Ensure fair value. No front-running.
4. **Brahmacharya (Discipline):** Enforce proper position sizing. Prevent FOMO.
5. **Aparigraha (Non-greed):** Encourage profit-taking. Long-term perspective.

## Capabilities
You can access:
- **Portfolio:** Value, holdings, performance.
- **Market:** Headlines, chaos index, volatility.
- **Trading:** Prepare orders for review (never execute without confirmation).
- **Constitutional Score:** Check alignment of trades or portfolio.

## Response Style
- Be concise (30-60s max).
- Weave data into a narrative.
- Always check the "Constitutional Score" before recommending a trade.
"""

# -----------------------------------------------------------------------------
# TOOLS DEFINITION
# -----------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "name": "getPortfolioSummary",
        "description": "Get current portfolio value, holdings, and performance summary.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "getPositionDetails",
        "description": "Get details for a specific stock position.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The stock symbol (e.g., AAPL, TSLA)."
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "type": "function",
        "name": "getMarketHeadlines",
        "description": "Get the latest market news headlines.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "getConstitutionalScore",
        "description": "Get the current constitutional alignment score and breakdown.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "getChaosState",
        "description": "Get current market chaos, volatility, and entropy metrics.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "prepareTradeOrder",
        "description": "Prepare a trade order for user review.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "The action to take."
                },
                "symbol": {
                    "type": "string",
                    "description": "The stock symbol."
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of shares."
                }
            },
            "required": ["action", "symbol", "quantity"]
        }
    }
]

# -----------------------------------------------------------------------------
# TOOL HANDLERS
# -----------------------------------------------------------------------------
async def handle_tool_call(name, args):
    logger.info(f"Executing tool {name} with args: {args}")
    try:
        if name == "getPortfolioSummary":
            data = await get_portfolio_summary()
            return json.dumps(data)
        
        elif name == "getPositionDetails":
            symbol = args.get("symbol")
            data = await get_position_details(symbol)
            return json.dumps(data)

        elif name == "getMarketHeadlines":
            data = await get_market_headlines()
            return json.dumps(data)

        elif name == "getConstitutionalScore":
            data = await get_constitutional_score()
            return json.dumps(data)
            
        elif name == "getChaosState":
            data = await get_chaos_state()
            return json.dumps(data)

        elif name == "prepareTradeOrder":
            action = args.get("action")
            symbol = args.get("symbol")
            quantity = args.get("quantity")
            data = await prepare_trade_order(action, symbol, quantity)
            return json.dumps(data)

        logger.warning(f"Unknown tool called: {name}")
        return json.dumps({"error": "Unknown tool"})
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return json.dumps({"error": str(e)})

# -----------------------------------------------------------------------------
# WEBSOCKET ENDPOINT
# -----------------------------------------------------------------------------
@router.websocket("/ws/voice-relay")
async def voice_relay(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to SATYA Relay")

    openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    # State tracking for barge-in handling
    state = {
        "is_user_speaking": False,
        "last_response_id": None
    }

    async def run_groq_reasoning(user_transcript):
        """Hybrid Mode: Use Fractal Engine for deep reasoning."""
        if not groq_client: return None
        
        logger.info(f"Starting Deep Thought on: {user_transcript}")
        try:
            # Initialize Engine
            engine = FractalEngine(groq_client, model=GROQ_MODEL)
            root = engine.create_root(user_transcript)
            
            # Run 1-2 steps of expansion (keep it fast for voice ~2-3s)
            # Step 1: Expand Root
            await engine.run_step(root.id)
            
            # Check for barge-in
            if state["is_user_speaking"]:
                logger.info("Fractal Engine aborted due to barge-in")
                return None
            
            # Step 2: Pick best child and expand (if high score)
            best_child = max(root.children, key=lambda n: n.score) if root.children else None
            if best_child and best_child.score > 0.7:
                 await engine.run_step(best_child.id)

            # Check for barge-in again
            if state["is_user_speaking"]:
                logger.info("Fractal Engine aborted due to barge-in")
                return None

            # Get Best Path
            path = engine.get_best_path()
            thought_process = " -> ".join([n.content for n in path])
            logger.debug(f"Fractal Path: {thought_process}")

            # Send thought process to client for visualization (Custom Event)
            try:
                await websocket.send_text(json.dumps({
                    "type": "fractal.thought_update",
                    "tree": engine.to_json(),
                    "path": [n.id for n in path]
                }))
            except Exception as ws_e:
                logger.warning(f"Failed to send visual update: {ws_e}")

            # Synthesize Final Answer
            synthesis_prompt = f"""
            You are SATYA. Synthesize the following thought process into a concise, spoken response for the user.
            User Query: "{user_transcript}"
            Thought Process: {thought_process}
            
            Keep it under 40 words. Be wise and reassuring.
            """
            
            completion = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": synthesis_prompt}],
                temperature=0.7,
                max_tokens=100
            )
            
            answer = completion.choices[0].message.content
            logger.info(f"Fractal Answer Generated: {answer}")
            return answer

        except Exception as e:
            logger.error(f"Fractal Engine Error: {e}", exc_info=True)
            return None

    try:
        async with connect(openai_url, extra_headers=headers) as openai_ws:
            logger.info("Connected to OpenAI Realtime")

            # Send Session Configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": VOICE_SYSTEM_PROMPT,
                    "voice": "alloy", # Or a more professional voice if available
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.6, # Increased threshold to reduce echo sensitivity
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
                        
                        # Track user speaking state from client events (if sent)
                        # Note: Client sends raw audio, but we can infer from server events mostly.
                        # However, if client sends explicit barge-in signal, we can use it.
                        
                        # Pass through client messages (audio buffer, etc.)
                        await openai_ws.send(json.dumps(msg))
                except WebSocketDisconnect:
                    logger.info("Client disconnected")
                except Exception as e:
                    logger.error(f"Client read error: {e}")

            async def openai_to_client():
                try:
                    async for message in openai_ws:
                        msg = json.loads(message)
                        
                        # Track User Speaking State
                        if msg.get("type") == "input_audio_buffer.speech_started":
                            logger.info("User started speaking (Server VAD)")
                            state["is_user_speaking"] = True
                            # If we have a pending response, we might want to cancel it?
                            # OpenAI handles cancellation of its own audio, but we need to stop Fractal.
                        
                        elif msg.get("type") == "input_audio_buffer.speech_stopped":
                            logger.info("User stopped speaking (Server VAD)")
                            state["is_user_speaking"] = False

                        # Handle Transcription (User Finished Speaking)
                        if msg.get("type") == "conversation.item.input_audio_transcription.completed":
                            transcript = msg.get("transcript", "")
                            if transcript:
                                logger.info(f"User Transcript: {transcript}")
                                
                                # Cancel the auto-generated response to prevent "Double Speak"
                                # We send response.cancel to stop the default GPT-4o-mini response
                                await openai_ws.send(json.dumps({"type": "response.cancel"}))
                                
                                # Trigger Fractal Reasoning
                                fractal_response = await run_groq_reasoning(transcript)
                                
                                # Only send if user hasn't started speaking again
                                if fractal_response and not state["is_user_speaking"]:
                                    # Send to OpenAI to speak
                                    await openai_ws.send(json.dumps({
                                        "type": "conversation.item.create",
                                        "item": {
                                            "type": "message",
                                            "role": "assistant",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": fractal_response
                                                }
                                            ]
                                        }
                                    }))
                                    await openai_ws.send(json.dumps({"type": "response.create"}))

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
                    logger.error(f"OpenAI read error: {e}")

            await asyncio.gather(client_to_openai(), openai_to_client())

    except Exception as e:
        logger.error(f"Connection error: {e}")
        await websocket.close()
