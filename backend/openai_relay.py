import os
import json
import asyncio
import time
import websockets
from websockets.client import connect
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is required")
GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"

# -----------------------------------------------------------------------------
# SIDECAR SYSTEM PROMPT (Extracted & Adapted for Observer Mode)
# -----------------------------------------------------------------------------
SIDECAR_SYSTEM_PROMPT = """
You are the "CCA Coach Observer", an expert cross-cultural communication assessor.
Your task is to analyze the ongoing conversation between a "Coach" (AI) and a "User" (Human).
You do NOT speak. You only output JSON to update the visual dashboard.

## YOUR CORE MISSION: DEEP FRACTAL INFERENCE
You are running a "Deep Fractal Scoring Matrix" that evolves from simple observation to complex pattern recognition.

### 1. INITIAL CALIBRATION (Turns 1-3)
- Focus on **Micro-Evidence**: Tone, hesitation, word choice, emotional resonance.
- Make tentative score adjustments based on immediate signals.

### 2. FRACTAL PATTERN RECOGNITION (Turn 4 Onwards)
- **ACTIVATION**: Starting at Turn 4, and for **EVERY** subsequent turn, you must analyze the **ENTIRE** conversation history.
- **METHOD**: Look for "Self-Similar Patterns" — consistent behavioral choices that repeat across different contexts.
- **GOAL**: Use this deep historical view to refine "Nuance" and increase "Confidence".

## THE FIVE DIMENSIONS (FRACTAL ANCHORS)
1. **DT - Directness & Transparency** (0-5)
2. **TR - Task vs Relational Accountability** (0-5)
3. **CO - Conflict Orientation** (0-5)
4. **CA - Cultural Adaptability** (0-5)
5. **EP - Empathy & Perspective-Taking** (0-5)

## OUTPUT FORMAT
You must output a SINGLE JSON object matching this structure exactly. Do not include markdown formatting or explanations.
{
  "dimensions": {
    "DT": { "score": number, "confidence": "low"|"medium"|"high", "evidenceCount": number, "trend": "stable"|"rising"|"falling" },
    "TR": { "score": number, "confidence": "string", "evidenceCount": number, "trend": "string" },
    "CO": { "score": number, "confidence": "string", "evidenceCount": number, "trend": "string" },
    "CA": { "score": number, "confidence": "string", "evidenceCount": number, "trend": "string" },
    "EP": { "score": number, "confidence": "string", "evidenceCount": number, "trend": "string" }
  },
  "newEvidence": {
    "dimension": "DT"|"TR"|"CO"|"CA"|"EP",
    "type": "positive"|"negative"|"contextual",
    "summary": "string",
    "timestamp": "string"
  },
  "phase": "OPENING"|"CORE"|"GAP_FILLING"|"VALIDATION"|"CLOSING",
  "summary": "string",
  "strengths": ["string"],
  "developmentPriorities": ["string"]
}
"""

@router.websocket("/ws/openai-relay")
async def openai_relay(websocket: WebSocket):
    await websocket.accept()
    print(f"Client connected to OpenAI Relay. Websockets version: {websockets.__version__}")

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
            print(f"🚀 [Sidecar] Triggering analysis with {len(history_snapshot)} turns...")
            start_time = time.time()
            
            messages = [
                {"role": "system", "content": SIDECAR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Current Conversation History:\n{json.dumps(history_snapshot, indent=2)}\n\nAnalyze the latest turn and provide the JSON update."}
            ]

            # Use parameters from user's snippet (Kimi K2 specific)
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
            print(f"✅ [Sidecar] Analysis complete in {duration:.2f}s")

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
            print(f"❌ [Sidecar] Error: {e}")

    try:
        # Use connect directly from websockets.client
        async with connect(openai_url, extra_headers=headers) as openai_ws:
            print("Connected to OpenAI Realtime API")
            
            # Task to forward messages from Client to OpenAI
            async def client_to_openai():
                try:
                    while True:
                        data = await websocket.receive_text()
                        msg = json.loads(data)

                        # INTERCEPT: Remove tools from session update to prevent OpenAI from blocking
                        if msg.get("type") == "session.update" and "session" in msg:
                            if "tools" in msg["session"]:
                                print("✂️ [Relay] Stripping tools from session config (Sidecar will handle them)")
                                del msg["session"]["tools"]
                                # Force tool_choice to none so it doesn't look for them
                                msg["session"]["tool_choice"] = "none"

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
                    print("Client disconnected")
                except Exception as e:
                    print(f"Error in client_to_openai: {e}")

            # Task to forward messages from OpenAI to Client
            async def openai_to_client():
                try:
                    async for message in openai_ws:
                        msg = json.loads(message)
                        
                        # TRACKING: Build History
                        if msg.get("type") == "conversation.item.input_audio_transcription.completed":
                            transcript = msg.get("transcript", "")
                            if transcript:
                                print(f"🗣️ [User]: {transcript}")
                                conversation_history.append({"role": "user", "content": transcript})
                                # Trigger Sidecar on User Turn
                                asyncio.create_task(run_sidecar_analysis(list(conversation_history)))

                        elif msg.get("type") == "response.audio_transcript.done":
                            transcript = msg.get("transcript", "")
                            if transcript:
                                print(f"🤖 [AI]: {transcript}")
                                conversation_history.append({"role": "assistant", "content": transcript})

                        await websocket.send_text(message)
                except Exception as e:
                    print(f"Error in openai_to_client: {e}")

            # Run both tasks
            await asyncio.gather(client_to_openai(), openai_to_client())

    except Exception as e:
        print(f"OpenAI Connection Error: {e}")
        # Send error to client if possible
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
        await websocket.close()
