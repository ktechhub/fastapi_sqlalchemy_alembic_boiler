from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status, Response
from fastapi.responses import JSONResponse


def created_response(
    message: str = "Created",
    data: Any = None,
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_201_CREATED,
):
    """
    Return a 201 Created response.

    Args:
        message (str): Custom message to include in the response (default: "Created").
        data (Any): Data to include in the response.
        headers (Dict[str, str], optional): Custom headers to include in the response.
        status_code (int): HTTP status code (default: 201).

    Returns:
        dict: Response object with status and detail.
    """
    response_data = {"status": status_code, "detail": message}

    if data is not None:
        response_data["data"] = data

    if headers:
        return JSONResponse(
            content=response_data, status_code=status_code, headers=headers
        )

    return response_data


def success_response(
    message: str = "Success",
    total_count: Optional[int] = None,
    data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_200_OK,
):
    """
    Return a 200 OK response.

    Args:
        message (str): Custom message to include in the response (default: "Success").
        data (Any): Data to include in the response.
        headers (Dict[str, str], optional): Custom headers to include in the response.
        status_code (int): HTTP status code (default: 200).

    Returns:
        dict: Response object with status and detail.
    """
    response_data = {"status": status_code, "detail": message}

    if data is not None:
        response_data["data"] = data

    if total_count is not None:
        response_data["total_count"] = total_count

    if headers:
        return JSONResponse(
            content=response_data, status_code=status_code, headers=headers
        )

    return response_data


def forbidden_response(
    message: str = "Forbidden",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_403_FORBIDDEN,
):
    """
    Raise a 403 Forbidden HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Forbidden").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 403).

    Raises:
        HTTPException: 403 Forbidden exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def not_found_response(
    message: str = "Not found",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_404_NOT_FOUND,
):
    """
    Raise a 404 Not Found HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Not found").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 404).

    Raises:
        HTTPException: 404 Not Found exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def not_authorized_response(
    message: str = "Not authorized",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
):
    """
    Raise a 401 Unauthorized HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Not authorized").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 401).

    Raises:
        HTTPException: 401 Unauthorized exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def bad_request_response(
    message: str = "Bad request",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
):
    """
    Raise a 400 Bad Request HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Bad request").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 400).

    Raises:
        HTTPException: 400 Bad Request exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def conflict_response(
    message: str = "Conflict",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_409_CONFLICT,
):
    """
    Raise a 409 Conflict HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Conflict").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 409).

    Raises:
        HTTPException: 409 Conflict exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def unprocessable_entity_response(
    message: str = "Unprocessable entity",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
):
    """
    Raise a 422 Unprocessable Entity HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Unprocessable entity").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 422).

    Raises:
        HTTPException: 422 Unprocessable Entity exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def internal_server_error_response(
    message: str = "Internal server error",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
):
    """
    Raise a 500 Internal Server Error HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Internal server error").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 500).

    Raises:
        HTTPException: 500 Internal Server Error exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def too_many_requests_response(
    message: str = "Too many requests",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_429_TOO_MANY_REQUESTS,
):
    """
    Raise a 429 Too Many Requests HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Too many requests").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 429).

    Raises:
        HTTPException: 429 Too Many Requests exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def no_content_response(
    message: str = "No content",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_204_NO_CONTENT,
):
    """
    Raise a 204 No Content HTTPException.
    Args:
        message (str): Custom message to include in the response (default: "No content").
        headers (Dict[str, str], optional): Custom headers to include in the response.
        status_code (int): HTTP status code (default: 204).

    Returns:
        dict: Response object with status and detail.
    """
    response_data = {"status": status_code, "detail": message}

    if headers:
        return JSONResponse(
            content=response_data, status_code=status_code, headers=headers
        )

    return response_data


def method_not_allowed_response(
    message: str = "Method not allowed",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_405_METHOD_NOT_ALLOWED,
):
    """
    Raise a 405 Method Not Allowed HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Method not allowed").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 405).

    Raises:
        HTTPException: 405 Method Not Allowed exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def service_unavailable_response(
    message: str = "Service unavailable",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
):
    """
    Raise a 503 Service Unavailable HTTPException.

    Args:
        message (str): Custom message to include in the exception (default: "Service unavailable").
        headers (Dict[str, str], optional): Custom headers to include in the exception.
        status_code (int): HTTP status code (default: 503).

    Raises:
        HTTPException: 503 Service Unavailable exception with the provided detail.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception


def not_acceptable_response(
    message: str,
    headers: Optional[Dict[str, str]] = None,
):
    """
    Create a HTTP_406_NOT_ACCEPTABLE HTTPException with full control over all parameters.

    Args:
        message (str): Custom message to include in the exception.
        headers (Dict[str, str], optional): Custom headers to include in the exception.

    Raises:
        HTTPException: HTTP_406_NOT_ACCEPTABLE exception with the provided parameters.
    """
    exception = HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=message
    )
    if headers:
        exception.headers = headers
    raise exception


# Additional utility functions for more customization
def custom_response(
    message: str,
    data: Any = None,
    status_code: int = status.HTTP_200_OK,
    headers: Optional[Dict[str, str]] = None,
):
    """
    Create a custom response with full control over all parameters.

    Args:
        message (str): Custom message to include in the response.
        data (Any): Data to include in the response.
        status_code (int): HTTP status code.
        headers (Dict[str, str], optional): Custom headers to include in the response.

    Returns:
        Union[dict, JSONResponse]: Response object with status and detail.
    """
    response_data = {"status": status_code, "detail": message, "data": data}

    if headers:
        return JSONResponse(
            content=response_data, status_code=status_code, headers=headers
        )

    return response_data


def custom_exception(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    headers: Optional[Dict[str, str]] = None,
):
    """
    Create a custom HTTPException with full control over all parameters.

    Args:
        message (str): Custom message to include in the exception.
        status_code (int): HTTP status code.
        headers (Dict[str, str], optional): Custom headers to include in the exception.

    Raises:
        HTTPException: Custom exception with the provided parameters.
    """
    exception = HTTPException(status_code=status_code, detail=message)
    if headers:
        exception.headers = headers
    raise exception
