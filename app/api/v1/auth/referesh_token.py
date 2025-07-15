# app/api/v1/users/register.py
from fastapi import APIRouter, status, Header
from app.utils.security_util import create_access_token_from_refresh_token
from app.core.loggers import app_logger as logger
from app.utils.responses import success_response, bad_request_response

router = APIRouter()


@router.post(
    "/refresh-token/",
    summary="Generate access token from refresh token",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    response_model_exclude_unset=True,
)
async def generate_refresh_token(refresh_token: str = Header(...)):
    """
    Generate access token from refresh token

    :param refresh_token: str: Refresh token

    :return: dict: Access token
    """
    logger.info("Generating access token from refresh token")
    try:
        access_token = create_access_token_from_refresh_token(
            refresh_token=refresh_token
        )
    except Exception as e:
        logger.error(f"Error generating access token from refresh token: {e}")
        return bad_request_response("Invalid refresh token")
    return success_response(
        "Access token generated successfully", data={"access_token": access_token}
    )
