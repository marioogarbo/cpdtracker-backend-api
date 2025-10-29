from urllib.parse import parse_qs
from channels.db import database_sync_to_async

import logging
logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user_from_token(token):
    """Get user from JWT token with proper error handling."""
    from django.contrib.auth.models import AnonymousUser
    if not token:
        return AnonymousUser()

    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated_token)
        return user
    except Exception as e:
        logger.warning(f"JWT authentication failed: {str(e)}")
        return AnonymousUser()

class JWTAuthMiddleware:
    """JWT Authentication middleware for WebSocket connections."""
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """Process the scope and authenticate the user."""
        from django.contrib.auth.models import AnonymousUser

        try:
            # Extract token from query string
            query_string = scope.get("query_string").decode()
            params = parse_qs(query_string)
            token = params.get("token", [None])[0]

            # Authenticate user
            if token:
                scope["user"] = await get_user_from_token(token)
            else:
                scope["user"] = AnonymousUser()

        except Exception as e:
            logger.error(f"Error in JWT middleware: {str(e)}")
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)