from typing import Any
from fastapi import HTTPException, status


def created_response(message: str = "Created", data: Any = None):
    """
    Return a 201 Created response.

    Args:
        message (str): Custom message to include in the response (default: "Created").

    Returns:
        dict: Response object with status and detail.
    """
    return {"status": status.HTTP_201_CREATED, "detail": message, "data": data}


def success_response(message: str = "Success", data: Any = None):
    """
    Return a 200 OK response.

    Args:
        message (str): Custom message to include in the response (default: "Success").

    Returns:
        dict: Response object with status and detail.
    """
    return {"status": status.HTTP_200_OK, "detail": message, "data": data}


def forbidden_response(message: str = "Forbidden"):
    """
    Raise a 403 Forbidden HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Forbidden").

    Raises:
        HTTPException: 403 Forbidden exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def not_found_response(message: str = "Not found"):
    """
    Raise a 404 Not Found HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Not found").

    Raises:
        HTTPException: 404 Not Found exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def not_authorized_response(message: str = "Not authorized"):
    """
    Raise a 401 Unauthorized HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Not authorized").

    Raises:
        HTTPException: 401 Unauthorized exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def bad_request_response(message: str = "Bad request"):
    """
    Raise a 400 Bad Request HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Bad request").

    Raises:
        HTTPException: 400 Bad Request exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def conflict_response(message: str = "Conflict"):
    """
    Raise a 409 Conflict HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Conflict").

    Raises:
        HTTPException: 409 Conflict exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def unprocessable_entity_response(message: str = "Unprocessable entity"):
    """
    Raise a 422 Unprocessable Entity HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Unprocessable entity").

    Raises:
        HTTPException: 422 Unprocessable Entity exception with the provided detail.
    """
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message
    )


def internal_server_error_response(message: str = "Internal server error"):
    """
    Raise a 500 Internal Server Error HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Internal server error").

    Raises:
        HTTPException: 500 Internal Server Error exception with the provided detail.
    """
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message
    )


def too_many_requests_response(message: str = "Too many requests"):
    """
    Raise a 429 Too Many Requests HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Too many requests").

    Raises:
        HTTPException: 429 Too Many Requests exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)


def method_not_allowed_response(message: str = "Method not allowed"):
    """
    Raise a 405 Method Not Allowed HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Method not allowed").

    Raises:
        HTTPException: 405 Method Not Allowed exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail=message)


def service_unavailable_response(message: str = "Service unavailable"):
    """
    Raise a 503 Service Unavailable HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Service unavailable").

    Raises:
        HTTPException: 503 Service Unavailable exception with the provided detail.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
