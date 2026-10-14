from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class ServiceError(APIException):
    def __init__(self, code, message, status_code=502, details=None):
        self.error_details = details
        self.status_code = status_code
        self.error_code = code
        super().__init__(detail=message)


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data
        response.data = {"error": {
            "code": getattr(exc, "error_code", getattr(exc, "default_code", "request_error")),
            "message": str(exc.detail) if isinstance(exc, ServiceError) else "Não foi possível atender à solicitação.",
            "details": exc.error_details if isinstance(exc, ServiceError) else detail,
        }}
    return response
