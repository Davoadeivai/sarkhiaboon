"""Tells the API documentation generator about the project's custom authentication."""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class OptionalJWTScheme(OpenApiAuthenticationExtension):
    target_class = "apps.core.authentication.OptionalJWTAuthentication"
    name = "jwtAuthOptional"
    # Shown in Swagger as "auth optional": the endpoint works with or without a token
    optional = True

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
