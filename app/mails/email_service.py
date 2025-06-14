import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings


base = os.path.dirname(os.path.realpath(__name__))
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER="app/mails/templates",
)


async def send_email_async(subject: str, email_to: str, html):
    message = MessageSchema(
        subject=subject, recipients=[email_to], body=html, subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)
