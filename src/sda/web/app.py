from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sda.core.domain.errors import SdaError
from sda.web.routers.anonymize import router as anonymize_router
from sda.web.routers.generate import router as generate_router
from sda.web.routers.health import router as health_router
from sda.web.schemas.generate import ErrorResponse

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(title="SDA Backend API")

    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(generate_router, prefix=API_PREFIX)
    app.include_router(anonymize_router, prefix=API_PREFIX)

    @app.exception_handler(SdaError)
    async def handle_sda_error(_, exc: SdaError) -> JSONResponse:
        payload = ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=None,
        ).model_dump()
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="validation_error",
            message="Invalid request.",
            details={"errors": jsonable_encoder(exc.errors())},
            request_id=None,
        ).model_dump()
        return JSONResponse(status_code=422, content=payload)

    return app


app = create_app()