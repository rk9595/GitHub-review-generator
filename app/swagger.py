from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_swagger_ui import get_swaggerui_blueprint
from app.schemas import ContributionsSchema

spec = APISpec(
    title="GitHub Contributions API",
    version="1.0.0",
    openapi_version="3.0.2",
    plugins=[MarshmallowPlugin()],
)

# Define Swagger UI blueprint
SWAGGER_URL = '/api/docs'
API_URL = '/api/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "GitHub Contributions API"
    }
)

spec.components.schema("Contributions", schema=ContributionsSchema)

spec.path(
    path="/api/repositories/{username}",
    operations=dict(
        get=dict(
            parameters=[
                {
                    "name": "username",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
 responses={
                200: {"description": "Repositories retrieved successfully"},
                404: {"description": "User not found"},
                500: {"description": "Internal server error"}
            },            
        )
    ),
)


spec.path(
    path="/api/contributions",
    operations=dict(
        post=dict(
            requestBody={"content": {"application/x-www-form-urlencoded": {"schema": {"$ref": "#/components/schemas/Contributions"}}}, "required": True},
 responses={
                200: {"description": "Contributions generated successfully"},
                400: {"description": "Invalid request parameters"},
                404: {"description": "User not found"},
                500: {"description": "Internal server error"}
            },        )
    ),
)