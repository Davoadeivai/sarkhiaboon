from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken, TokenError


class OptionalJWTAuthentication(JWTAuthentication):
    """
    Like JWTAuthentication, but an invalid/expired token (or a deactivated
    user) is treated as anonymous instead of rejecting the request.

    Used on public endpoints (catalog browsing, login) so a stale token stored
    in the app never blocks the user from browsing or signing in again.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, TokenError, AuthenticationFailed):
            return None
