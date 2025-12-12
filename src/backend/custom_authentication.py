from rest_framework.authentication import SessionAuthentication, TokenAuthentication, get_authorization_header


class TokenOrSessionAuthentication(TokenAuthentication):
    """
    Authenticate using token if Authorization header is provided,
    otherwise fall back to session authentication.
    """

    def authenticate(self, request):
        # Check if Authorization header exists
        auth = get_authorization_header(request).split()

        # If token/bearer auth header is present, use token authentication
        if auth and auth[0].lower() in [b"token", b"bearer"]:
            return super().authenticate(request)

        # No token header, try session authentication
        session_auth = SessionAuthentication()
        return session_auth.authenticate(request)
