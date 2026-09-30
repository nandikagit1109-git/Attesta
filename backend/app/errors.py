"""Standard error format for every endpoint: {"error": {"code", "message", "details"}}.

Registered as FastAPI exception handlers in main.py so error shape is uniform.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .states import ErrorCode


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: dict | list | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code.value, "message": message, "details": details}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: ErrorCode.AUTHENTICATION_ERROR,
            403: ErrorCode.PERMISSION_DENIED,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
        }.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return error_response(exc.status_code, code, str(exc.detail), getattr(exc, "details", None))

    @app.exception_handler(RequestValidationError)
    async def validation_exc_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            422, ErrorCode.VALIDATION_ERROR, "Invalid request payload", exc.errors()
        )

    @app.exception_handler(Exception)
    async def unhandled_exc_handler(request: Request, exc: Exception) -> JSONResponse:
        # Fail loud, leak nothing: log server-side, generic message client-side.
        request.app.state.last_internal_error = repr(exc)
        return error_response(500, ErrorCode.INTERNAL_ERROR, "Internal server error")
