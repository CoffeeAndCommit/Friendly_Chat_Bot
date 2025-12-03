# backend/api/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .utils_openai import OpenAIStreamer

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f"user_{self.user_id}"

        print(f"[DEBUG] User {self.user_id} connecting to WebSocket...")
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print("[DEBUG] WebSocket accepted")

        await self.send(json.dumps({
            "type": "system",
            "message": "WebSocket connected"
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"[DEBUG] User {self.user_id} disconnected from WebSocket")

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"[DEBUG] Received from client: {data}")

        msg_type = data.get("type")
        content = data.get("content")

        if msg_type != "text":
            await self.send(json.dumps({
                "type": "error",
                "message": f"Unsupported msg_type: {msg_type}"
            }))
            return

        streamer = OpenAIStreamer()

        async def send_chunk(chunk):
            print(f"[DEBUG] Sending to client: {chunk}")
            await self.send(json.dumps(chunk))

        print("[DEBUG] Starting OpenAI stream_response...")
        # Unified call: GPT-4o streaming or GPT-5 REST fallback
        await streamer.stream_response({"type": msg_type, "content": content}, send_chunk)




# import json
# from channels.generic.websocket import AsyncWebsocketConsumer

# from .utils_openai import OpenAIStreamer
# import base64

# class ChatConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         self.user_id = self.scope['url_route']['kwargs']['user_id']
#         self.room_group_name = f"user_{self.user_id}"

#         await self.channel_layer.group_add(
#             self.room_group_name, 
#             self.channel_name
#         )
#         await self.accept()

#         await self.send(json.dumps({
#             "type": "system",
#             "message": "WebSocket connected"
#         }))

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.room_group_name, 
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         print("Received from client:", data)

#         msg_type = data.get("type")
#         content = data.get("content")

#         # Validate message
#         if msg_type not in ["text", "audio"]:
#             await self.send(json.dumps({
#                 "type": "error",
#                 "message": f"Invalid msg_type: {msg_type}"
#             }))
#             return

#         # Build user_message
#         user_message = {
#             "type": msg_type,
#             "content": content
#         }

#         streamer = OpenAIStreamer()
#         print("Starting to stream response from OpenAI...")
#         async def send_chunk(chunk):
#             print("Sending to client:", chunk)
#             await self.send(json.dumps(chunk))
#         print("Calling stream_response...")
#         await streamer.stream_response(user_message, send_chunk)


#     async def receive_ping(self):
#         await self.send(json.dumps({"type": "pong"}))

#     @staticmethod
#     def encode_audio_to_base64(bytes_data):
#         return base64.b64encode(bytes_data).decode('utf-8')

#     @staticmethod
#     def decode_audio_from_base64(b64):
#         return base64.b64decode(b64)
