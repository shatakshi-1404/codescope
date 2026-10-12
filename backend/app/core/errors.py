from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for all expected, user-facing errors."""

    status_code = 400
    code = "app_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class InvalidRepositoryURLError(AppError):
    status_code = 422
    code = "invalid_repository_url"


class RepositoryCloneError(AppError):
    status_code = 502
    code = "repository_clone_failed"


class AnalysisFailedError(AppError):
    status_code = 500
    code = "analysis_failed"


class BusinessRuleError(AppError):
    """The request is well-formed but breaks a domain rule (e.g. removing the owner)."""

    status_code = 422
    code = "business_rule_violation"


class InvalidBranchError(AppError):
    status_code = 422
    code = "invalid_branch"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "rate_limited"


class RepositoryNotFoundError(AppError):
    status_code = 404
    code = "repository_not_found"


def _body(code: str, message: str, details=None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_body("validation_error", "Request validation failed.", details),
        )
