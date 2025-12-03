


import json
import asyncio
import websockets
import base64
import os

from dotenv import load_dotenv

load_dotenv() 




OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("OPENAI_API_KEY", OPENAI_API_KEY)

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"

class OpenAIStreamer:
   async def stream_response(self, user_message, on_delta):
        """
        Main function:
        user_message = {"type": "text" or "audio", "content": "..."}
        on_delta = callback to send partial chunks to frontend
        """

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        print("Connecting to OpenAI Realtime API...1")

        async with websockets.connect(OPENAI_REALTIME_URL, extra_headers=headers) as ws:

            # 1. Create session
            await ws.send(json.dumps({
                # "type": "session.create",
                # # "model": "gpt-4o-realtime-preview"
                "model": "gpt-5-mini-2025-08-07",
                "type": "response.create",
    "response": {
        "instructions": user_message["content"],
        "modalities": ["text"]  # forces text output
    }
            }))
            print("Connecting to OpenAI Realtime API...2")

            # 2. Send user message
            if user_message["type"] == "text":
                await ws.send(json.dumps({
                    "type": "input_text",
                    "text": user_message["content"]
                }))
                print("Connecting to OpenAI Realtime API...3")
            elif user_message["type"] == "audio":
                await ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": user_message["content"]  # base64 encoded audio
                }))

                # tell openai that audio input has completed
                await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

            # 3. Receive streaming output
            async for msg in ws:
                data = json.loads(msg)
                print("Received from OpenAI:", data)

                # streaming text
                if data.get("type") == "response.output_text.delta":
                    chunk = data.get("text_delta", "")
                    # await on_delta({"type": "text", "delta": chunk})
                    await on_delta({"type": "text", "delta": data.get("text_delta", "")})

                # final text
                if data.get("type") == "response.output_text.done":
                    final = data.get("text", "")
                    # await on_delta({"type": "text_done", "text": final})
                    await on_delta({"type": "text_done", "text": data.get("text", "")})

                # streaming audio
                if data.get("type") == "response.output_audio.delta":
                    audio_chunk = data.get("audio", "")
                    await on_delta({"type": "audio", "delta": audio_chunk})

                # final audio
                if data.get("type") == "response.output_audio.done":
                    audio_full = data.get("audio", "")
                    await on_delta({"type": "audio_done", "audio": audio_full})




















