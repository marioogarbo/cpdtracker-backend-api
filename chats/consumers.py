import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .agents import run_cpd_agent

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close()
            return
        await self.accept()

    async def disconnect(self, code):
        pass

    async def receive(self, text_data):
        try:
            # Extract token from query string
            query_string = self.scope.get("query_string").decode()
            from urllib.parse import parse_qs
            params = parse_qs(query_string)
            token = params.get("token", [None])[0]

            # Validate token
            user = await self.get_user_from_token(token)
            if not user or not user.is_authenticated:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'Authentication required.'}))
                await self.close()
                return

            # Ensure the message is valid JSON
            if not text_data:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'No message provided.'}))
                return
            
            # Load the message data
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'Invalid JSON format.'}))
                return

            # Validate the user message
            user_message = data.get('message', '').strip()
            if not user_message:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'Message is required.'}))
                return

            # Run the CPD agent with the user message
            result = run_cpd_agent(user_message, user, session_id=data.get('session_id'))

            # Stream the response back to the client
            async for delta in result:
                if delta.startswith("SESSION_ID:"):
                    session_id = None
                    session_id = delta.split(":", 1)[1]
                    # Send session_id
                    await self.send(text_data=json.dumps({"type": "session_id", "session_id": session_id}))
                else:
                    # Send streaming delta
                    await self.send(text_data=json.dumps({"type": "delta", "content": delta}))

            # Send completion signal
            await self.send(text_data=json.dumps({"type": "complete"}))
            
        except Exception as e:
            await self.send(text_data=json.dumps({'type': 'error', 'error': f'An unexpected error occurred: {str(e)}'}))
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from django.contrib.auth.models import AnonymousUser

        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return user
        except Exception:
            return AnonymousUser()