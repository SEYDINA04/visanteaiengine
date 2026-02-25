"""
Visanté AI Engine - AI Triage Layer

Secure middleman: mobile app streams raw audio via WebSocket to this FastAPI backend,
which relays it to the Gemini Multimodal Live API and streams audio responses back.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types

load_dotenv()

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("visante.triage")

# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Visanté AI Engine",
    description="API for Visanté mobile app (Triage & Calls)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Gemini Configuration
# -----------------------------------------------------------------------------
_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise ValueError(
        "GOOGLE_API_KEY or GEMINI_API_KEY required. "
        "Set it in .env or environment. Get a key: https://aistudio.google.com/apikey"
    )

_client = genai.Client(api_key=_api_key, http_options={"api_version": "v1beta"})

MODEL = "gemini-2.0-flash-exp"

# AUDIO response modality with prebuilt voice "Aoede"
CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
        )
    ),
)

# PCM 16-bit mono 16kHz - matches frontend format
AUDIO_MIME_TYPE = "audio/pcm;rate=16000"

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@app.get("/", tags=["System"])
async def root():
    """Service info and links."""
    return {
        "service": "Visanté AI Engine",
        "docs": "/docs",
        "status": "/api/v1/status",
        "websocket": "/ws/triage",
    }


@app.get("/api/v1/status", tags=["System"])
async def health_check():
    """Health check for load balancers and monitoring."""
    return {"status": "online", "service": "Visanté AI Engine"}


@app.websocket("/ws/triage")
async def triage_websocket(websocket: WebSocket):
    """
    Bi-directional audio stream. Expects and returns raw binary bytes:
    - Input:  PCM 16-bit, mono, 16000 Hz (no JSON wrapper)
    - Output: PCM audio bytes from Gemini
    """
    await websocket.accept()
    logger.info("WebSocket client connected to /ws/triage")

    try:
        async with _client.aio.live.connect(model=MODEL, config=CONFIG) as session:

            async def receive_from_client() -> None:
                """Task 1: Receive audio from WebSocket → send to Gemini."""
                try:
                    while True:
                        chunk = await websocket.receive_bytes()
                        await session.send_realtime_input(
                            audio=types.Blob(data=chunk, mime_type=AUDIO_MIME_TYPE)
                        )
                except WebSocketDisconnect:
                    logger.info("Client disconnected (receive_from_client)")
                    raise
                except Exception as e:
                    logger.exception("Error receiving/sending to client: %s", e)
                    raise

            async def receive_from_gemini() -> None:
                """Task 2: Receive audio from Gemini → send to WebSocket."""
                try:
                    async for response in session.receive():
                        if response.data:
                            await websocket.send_bytes(response.data)
                except Exception as e:
                    logger.exception("Error receiving/sending from Gemini: %s", e)
                    raise

            async with asyncio.TaskGroup() as tg:
                tg.create_task(receive_from_client())
                tg.create_task(receive_from_gemini())

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except asyncio.CancelledError:
        logger.info("Triage WebSocket task cancelled")
    except Exception as e:
        logger.exception("Triage WebSocket error: %s", e)
    finally:
        try:
            await websocket.close(code=1000)
        except RuntimeError:
            pass
