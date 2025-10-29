import os
import json

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel
from openai.types.responses import ResponseTextDeltaEvent
from .models import ChatSession, Message
from .serializers import ChatSessionListSerializer, ChatSessionSerializer

load_dotenv()
debug = settings.DEBUG

class ChatSessionListView(generics.ListAPIView):
    """View to list all chat sessions for the authenticated user."""
    serializer_class = ChatSessionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)

class ChatSessionDetailView(generics.RetrieveAPIView):
    """View to retrieve a specific chat session by ID."""
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)

class MessageView(APIView):
    """API view to handle streaming chat responses using OpenAI Agent SDK."""
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize Azure OpenAI client
        self.azure_client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY", default=""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", default=""),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", default=""),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL", default=""),
        )
        
        # Initialize the model and agent
        self.azure_model = OpenAIChatCompletionsModel(
            model="gpt-4.1-nano", 
            openai_client=self.azure_client
        )
        
        self.assistant = Agent(
            name="CPD Assistant", 
            instructions="You are a helpful CPD (Continuing Professional Development) assistant. Help users with their professional development questions and activities.",
            model=self.azure_model
        )

    def post(self, request, *args, **kwargs):
        """Handle POST requests for streaming chat"""
        user_message = request.data.get('message', '').strip()
        
        if not user_message:
            return Response(
                {'error': 'Message is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create streaming response
            return self.stream_response(user_message)
        except Exception as e:
            return Response(
                {'error': f'An error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def stream_response(self, user_message: str):
        """Stream the AI response using the OpenAI Agent SDK"""
        
        def event_stream():
            try:
                # Send initial event
                yield f'data: {json.dumps({"type": "start", "message": "Starting response..."})}\n\n'
                
                # Run the agent with streaming
                async def run_agent():
                    result = Runner.run_streamed(self.assistant, user_message)
                    full_response = ""
                    
                    async for event in result.stream_events():
                        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                            delta = event.data.delta
                            if delta:
                                full_response += delta
                                yield f'data: {json.dumps({"type": "delta", "content": delta})}\n\n'
                    
                    # Send completion event
                    yield f'data: {json.dumps({"type": "complete", "full_response": full_response})}\n\n'
                
                # Run the async function in the sync context
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async_gen = run_agent()
                    while True:
                        try:
                            chunk = loop.run_until_complete(async_gen.__anext__())
                            yield chunk
                        except StopAsyncIteration:
                            break
                finally:
                    loop.close()
                
                yield 'event: end\n\n'
                
            except Exception as e:
                error_data = {
                    'type': 'error',
                    'error': str(e)
                }
                yield f'data: {json.dumps(error_data)}\n\n'

        # Create streaming response
        resp = StreamingHttpResponse(
            event_stream(), 
            content_type='text/event-stream'
        )
        
        # Streaming headers 
        resp['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        resp['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        
        return resp