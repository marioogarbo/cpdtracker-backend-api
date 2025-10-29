from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import uuid, datetime

def custom_exception_handler(exc, context):
    """Custom exception handler for Django Rest Framework to standardize error responses."""
    response = exception_handler(exc, context)

    # If response is None, it's an unhandled exception
    if response is None:
        return Response(
            {
                "error": {
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "code": "SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": [],
                    "timestamp": datetime.datetime.now().isoformat(),
                    "requestId": str(uuid.uuid4())
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Format the response for standard errors
    error_data = {
        "error": {
            "status": response.status_code,
            "code": get_error_code(response.status_code),
            "message": get_error_message(response.data, response.status_code),
            "details": format_error_details(response.data),
            "timestamp": datetime.datetime.now().isoformat(),
            "requestId": str(uuid.uuid4())
        }
    }
    
    response.data = error_data
    return response

def get_error_code(status_code):
    """Maps HTTP status codes to custom error codes."""
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "SERVER_ERROR"
    }
    return error_codes.get(status_code, "UNKNOWN_ERROR")

def get_error_message(data, status_code):
    """Extracts a meaningful error message from the response data."""
    default_messages = {
        400: "Invalid request parameters",
        401: "Authentication credentials are invalid",
        403: "You don't have permission to perform this action",
        404: "The requested resource was not found",
        405: "This method is not allowed for the requested resource",
        500: "An internal server error occurred"
    }
    
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        if "non_field_errors" in data:
            return str(data["non_field_errors"][0])
    
    return default_messages.get(status_code, "An error occurred")

def format_error_details(data):
    """Formats error details from the response data."""
    details = []
    
    if isinstance(data, dict):
        for field, errors in data.items():
            if field == "detail" or field == "non_field_errors":
                continue
            if isinstance(errors, list):
                for error in errors:
                    details.append({"field": field, "message": str(error)})
            else:
                details.append({"field": field, "message": str(errors)})
    
    return details