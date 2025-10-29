import os
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, OpenAIChatCompletionsModel
from channels.db import database_sync_to_async

load_dotenv()    

async def run_cpd_agent(user_message, user, session_id=None):
    """Run the CPD agent with the provided user message."""

    # Initialize the Azure OpenAI client
    azure_client = AsyncAzureOpenAI(
        api_key=os.getenv('AZURE_OPENAI_API_KEY'),
        api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
        azure_deployment=os.getenv('AZURE_OPENAI_DEPLOYMENT_MODEL'),
    )

    # Initialize the Azure OpenAI model
    azure_model = OpenAIChatCompletionsModel(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL"),
        openai_client=azure_client
    )

    # Initialize the instructions
    instructions = '''
        You are a CPD (Continuing Professional Development) Assistant. Your job is to help professionals 
        with anything related to CPD, including:
        
        - Explaining what CPD is and how it works
        - Helping with CPD planning and tracking
        - Explaining credentialing programs/systems and requirements
        - Helping with activity categorization and point/hour calculations
        - Providing advice on CPD activities and documentation
        - Assisting with enrollment and cycle planning
        
        You can help with questions about:
        - Courses, workshops, seminars, webinars, conferences
        - Certifications and formal education programs
        - Self-study activities and research projects
        - Mentoring and professional development activities
        - Online learning and virtual training sessions
        - Points-based vs hours-based methodologies
        - Renewal cycles and requirements
        - Carryover policies and limits
        - Category-specific rules and calculations
        
        If someone asks about anything NOT related to CPD (like programming, current events, 
        general knowledge, etc.), politely say: "I'm a CPD assistant and can only help with 
        Continuing Professional Development questions. Please ask me about CPD topics instead."
        
        Be helpful, professional, and encouraging when answering CPD-related questions.'''

    # Initialize the assistant
    assistant = Agent(
        name="CPD Assistant",
        instructions=instructions,
        model=azure_model
    )

    try:
        # Get or create a chat session
        session = await get_or_create_session(user, session_id, user_message)
        
        if not session:
            yield "Chat session not found."
            return
        
        # If this is a new session (no session_id provided), yield the session ID first
        if not session_id:
            yield f"SESSION_ID:{session.id}"
        
        # Store the user message
        await create_message(session, 'user', user_message)

        # Run the agent
        result = Runner.run_streamed(assistant, user_message)

        # Stream the response back to the client
        full_response = ""
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                delta = event.data.delta
                if delta:
                    full_response += delta
                    yield delta
        
        # Store the AI response
        await create_message(session, 'ai', full_response)
    
    except Exception as e:
        yield f"An unexpected error occurred: {str(e)}"


@database_sync_to_async
def get_or_create_session(user, session_id, user_message):
    """Get existing session or create new one."""
    from .models import ChatSession
    if session_id:
        try:
            return ChatSession.objects.get(id=session_id, user=user)
        except ChatSession.DoesNotExist:
            return None
    else:
        return ChatSession.objects.create(user=user, title=user_message[:30])


@database_sync_to_async
def create_message(session, sender, content):
    """Create a message in the database."""
    from .models import Message
    return Message.objects.create(session=session, sender=sender, content=content)