import os
import json
import asyncio
import time
import websockets
from websockets.client import connect
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from groq import AsyncGroq
from logger_config import logger

load_dotenv()

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY environment variable is required")
    raise ValueError("GROQ_API_KEY environment variable is required")
GROQ_MODEL = "llama-3.3-70b-versatile"

# -----------------------------------------------------------------------------
# SIDECAR SYSTEM PROMPT (Constitutional Validator)
# -----------------------------------------------------------------------------
SIDECAR_SYSTEM_PROMPT = """
You are the "Constitutional Validator", an expert in ethical market analysis based on the Yamas.
Your task is to analyze the ongoing conversation between "SATYA" (AI) and a "User" (Human).
You do NOT speak. You only output JSON to update the visual dashboard.

## YOUR CORE MISSION: CONSTITUTIONAL ALIGNMENT
You must evaluate the conversation against five core principles (Yamas):
1. Ahimsa (Non-harm): Is the advice safe? Does it avoid exploitation?
2. Satya (Truth): Is the data accurate? Is uncertainty acknowledged?
3. Asteya (Non-stealing): Is the trade fair? No front-running?
4. Brahmacharya (Discipline): Is position sizing correct? No FOMO?
5. Aparigraha (Non-greed): Is profit-taking encouraged? Long-term view?

## OUTPUT FORMAT
You must output a SINGLE JSON object matching this structure exactly.
{
  "constitutionalScore": number, // 0.0 to 1.0
  "alignment": {
    "ahimsa": { "score": number, "status": "aligned"|"violation"|"neutral", "reason": "string" },
    "satya": { "score": number, "status": "aligned"|"violation"|"neutral", "reason": "string" },
    "asteya": { "score": number, "status": "aligned"|"violation"|"neutral", "reason": "string" },
    "brahmacharya": { "score": number, "status": "aligned"|"violation"|"neutral", "reason": "string" },
    "aparigraha": { "score": number, "status": "aligned"|"violation"|"neutral", "reason": "string" }
  },
  "marketState": {
    "chaosIndex": number, // 0.0 to 1.0 (derived from user sentiment/market context)
    "volatility": number, // 0.0 to 1.0
    "entropy": number // 0.0 to 1.0
  },
  "recommendation": "string" // Short constitutional guidance
}
"""

@router.websocket("/ws/openai-relay")
async def openai_relay(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"Client connected to OpenAI Relay. Websockets version: {websockets.__version__}")

    openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    # Initialize Sidecar
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)
    conversation_history = [] # List of {"role": "user"|"assistant", "content": "..."}
    
    async def run_sidecar_analysis(history_snapshot):
        """Runs Groq inference in the background and injects the result back to the client."""
        try:
            logger.info(f"Triggering Sidecar analysis with {len(history_snapshot)} turns...")
            start_time = time.time()
            
            messages = [
                {"role": "system", "content": SIDECAR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Current Conversation History:\n{json.dumps(history_snapshot, indent=2)}\n\nAnalyze the latest turn and provide the JSON update."}
            ]

            # Use parameters optimized for Llama 3.3 70B
            completion = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.6,
                max_completion_tokens=4096,
                top_p=1,
                stream=False,
                stop=None
            )
            
            result_json_str = completion.choices[0].message.content
            duration = time.time() - start_time
            logger.info(f"Sidecar analysis complete in {duration:.2f}s")

            # Construct the fake tool call event for the frontend
            tool_event = {
                "type": "response.function_call_arguments.done",
                "call_id": f"sidecar_{int(time.time())}",
                "name": "updateAssessmentState",
                "arguments": result_json_str
            }
            
            # Inject into client stream
            await websocket.send_text(json.dumps(tool_event))

        except Exception as e:
            logger.error(f"Sidecar Error: {e}", exc_info=True)

    try:
        # Use connect directly from websockets.client
        async with connect(openai_url, extra_headers=headers) as openai_ws:
            logger.info("Connected to OpenAI Realtime API")
            
            # Task to forward messages from Client to OpenAI
            async def client_to_openai():
                try:
                    while True:
                        data = await websocket.receive_text()
                        msg = json.loads(data)

                        # INTERCEPT: Remove tools from session update to prevent OpenAI from blocking
                        # if msg.get("type") == "session.update" and "session" in msg:
                        #     if "tools" in msg["session"]:
                        #         print("✂️ [Relay] Stripping tools from session config (Sidecar will handle them)")
                        #         del msg["session"]["tools"]
                        #         # Force tool_choice to none so it doesn't look for them
                        #         msg["session"]["tool_choice"] = "none"

                        # INTERCEPT: Track User Audio Transcription (if available) or just rely on audio
                        # Note: Client sends 'input_audio_buffer.append'. 
                        # We rely on Server VAD events to know when user spoke, but we need the TEXT.
                        # The server sends 'conversation.item.input_audio_transcription.completed' 
                        # BUT only if we ask for it. We should ensure input_audio_transcription is enabled.
                        
                        # If it's a session update, ensure transcription is on
                        if msg.get("type") == "session.update" and "session" in msg:
                             if "input_audio_transcription" not in msg["session"]:
                                 msg["session"]["input_audio_transcription"] = {"model": "whisper-1"}

                        await openai_ws.send(json.dumps(msg))
                except WebSocketDisconnect:
                    logger.info("Client disconnected")
                except Exception as e:
                    logger.error(f"Error in client_to_openai: {e}", exc_info=True)

            # Task to forward messages from OpenAI to Client
            async def openai_to_client():
                try:
                    async for message in openai_ws:
                        msg = json.loads(message)
                        
                        # TRACKING: Build History
                        if msg.get("type") == "conversation.item.input_audio_transcription.completed":
                            transcript = msg.get("transcript", "")
                            if transcript:
                                logger.info(f"User Transcript: {transcript}")
                                conversation_history.append({"role": "user", "content": transcript})
                                # Trigger Sidecar on User Turn
                                asyncio.create_task(run_sidecar_analysis(list(conversation_history)))

                        elif msg.get("type") == "response.audio_transcript.done":
                            transcript = msg.get("transcript", "")
                            if transcript:
                                logger.info(f"AI Transcript: {transcript}")
                                conversation_history.append({"role": "assistant", "content": transcript})

                        await websocket.send_text(message)
                except Exception as e:
                    logger.error(f"Error in openai_to_client: {e}", exc_info=True)

            # Run both tasks
            await asyncio.gather(client_to_openai(), openai_to_client())

    except Exception as e:
        logger.error(f"OpenAI Connection Error: {e}", exc_info=True)
        # Send error to client if possible
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
        await websocket.close()
