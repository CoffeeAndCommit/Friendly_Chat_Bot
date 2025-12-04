import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .utils_openai import get_openai_client

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        print("[WS] New WebSocket connection")
        await self.accept()
        print("[WS] Connection accepted")
    async def receive(self, text_data):
        print("======== [WS RECEIVE] ==========")
        print("[RAW DATA]:", text_data)

        data = json.loads(text_data)
        user_msg = data.get("message", "")
        
        print("[USER MSG]:", user_msg)

        if not user_msg:
            print("[ERROR] Empty message!")
            await self.send(json.dumps({
                "type": "error",
                "message": "Message cannot be empty"
            }))
            return

        try:
            client = get_openai_client()
            print("[DEBUG] OpenAI client created")

            print("[DEBUG] Sending request to OpenAI →", user_msg)
     
            # ---- FIXED: Use input_text instead of input ----
            response = client.responses.create(
                model="gpt-5-nano",
                # input_text=user_msg
                input=user_msg
            )
            print("[DEBUG] Raw OpenAI response:", response)

            ai_text = response.output_text
            print("[DEBUG] Extracted output_text:", ai_text)

            await self.send(json.dumps({
                "type": "message",
                "message": ai_text
            }))
            print("[WS] Sent AI response")
        except Exception as e:
            print("********** [OPENAI ERROR] **********")
            print(str(e))
            print("************************************")

            await self.send(json.dumps({
                "type": "error",
                "message": f"Error: {str(e)}"
            }))

