"""
WebSocket JWT Authentication Middleware
"""
import logging
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for Django Channels WebSocket connections
    """
    
    def __init__(self, inner):
        super().__init__(inner)
    
    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        token = None
        if 'token' in query_params:
            token = query_params['token'][0]
        
        # Authenticate user
        user = await self.get_user_from_token(token)
        scope['user'] = user
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        Authenticate user from JWT token
        """
        if not token:
            logger.warning("No token provided in WebSocket connection")
            return AnonymousUser()
        
        try:
            # Validate the token
            UntypedToken(token)
            
            # Decode the token to get user ID
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            # Get the user
            user = User.objects.get(id=user_id, is_active=True)
            logger.info(f"WebSocket authenticated user: {user.get_full_name()}")
            return user
            
        except (InvalidToken, TokenError, User.DoesNotExist) as e:
            logger.error(f"JWT WebSocket authentication failed: {str(e)}")
            return AnonymousUser()
        except Exception as e:
            logger.error(f"Unexpected error in JWT WebSocket authentication: {str(e)}")
            return AnonymousUser()


class JWTAuthMiddlewareStack(BaseMiddleware):
    """
    Custom middleware stack for JWT authentication with WebSockets
    """
    
    def __init__(self, inner):
        self.inner = inner
    
    async def __call__(self, scope, receive, send):
        """
        Middleware stack that adds JWT authentication to WebSocket scope
        """
        return await JWTAuthMiddleware(self.inner)(scope, receive, send)