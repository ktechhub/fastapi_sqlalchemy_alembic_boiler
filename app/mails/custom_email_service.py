import os
from typing import List, Optional, Union
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
from app.core.loggers import logger
from .email_templates import get_basic_template, get_welcome_email_template


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


async def send_email_async(
    subject: str,
    email_to: Union[str, List[str]],
    html: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
):
    """Send email asynchronously using FastAPI Mail

    Args:
        subject (str): Email subject
        email_to (Union[str, List[str]]): Email recipient(s)
        html (str): HTML email content
        cc (Optional[List[str]], optional): CC recipients. Defaults to None.
        bcc (Optional[List[str]], optional): BCC recipients. Defaults to None.
        reply_to (Optional[str], optional): Reply-to email. Defaults to None.
    """
    # Convert single email to list
    if isinstance(email_to, str):
        recipients = [email_to]
    else:
        recipients = email_to

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=html,
        subtype=MessageType.html,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    logger.info(f"Async email sent to {recipients} with subject '{subject}'")


class EmailService:
    def __init__(self, sender: str = None, sender_name: str = None) -> None:
        """Initialize EmailService with custom sender details

        Args:
            sender (str, optional): Sender email. Defaults to settings.MAIL_FROM.
            sender_name (str, optional): Sender name. Defaults to settings.MAIL_FROM_NAME.
        """
        self.sender = sender or settings.MAIL_FROM
        self.sender_name = sender_name or settings.MAIL_FROM_NAME
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=self.sender,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_FROM_NAME=self.sender_name,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER="app/mails/templates",
        )

    def get_mail_message(
        self,
        recipients: Union[str, List[str]],
        subject: str,
        html: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> MessageSchema:
        """Create a mail message object

        Args:
            recipients (Union[str, List[str]]): Email recipient(s)
            subject (str): Email subject
            html (str): HTML email content
            cc (Optional[List[str]], optional): CC recipients. Defaults to None.
            bcc (Optional[List[str]], optional): BCC recipients. Defaults to None.
            reply_to (Optional[str], optional): Reply-to email. Defaults to None.

        Returns:
            MessageSchema: Mail message object
        """
        # Convert single email to list
        if isinstance(recipients, str):
            recipients = recipients.split(",")

        return MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html,
            subtype=MessageType.html,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
        )

    async def send_email(
        self,
        recipients: Union[str, List[str]],
        subject: str,
        salutation: str,
        content: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ):
        """Send email using basic template

        Args:
            recipients (Union[str, List[str]]): Email recipient(s)
            subject (str): Email subject
            salutation (str): Email salutation
            content (str): Email content
            cc (Optional[List[str]], optional): CC recipients. Defaults to None.
            bcc (Optional[List[str]], optional): BCC recipients. Defaults to None.
            reply_to (Optional[str], optional): Reply-to email. Defaults to None.
        """
        html = get_basic_template("Media Transcribe", subject, salutation, content)
        message = self.get_mail_message(recipients, subject, html, cc, bcc, reply_to)

        fm = FastMail(self.conf)
        await fm.send_message(message)

        recipient_list = recipients if isinstance(recipients, list) else [recipients]
        logger.info(f"Email sent to {recipient_list} with subject '{subject}'")

    async def send_typed_email(
        self,
        recipients: Union[str, List[str]],
        subject: str,
        html: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ):
        """Send email with custom HTML

        Args:
            recipients (Union[str, List[str]]): Email recipient(s)
            subject (str): Email subject
            html (str): HTML email content
            cc (Optional[List[str]], optional): CC recipients. Defaults to None.
            bcc (Optional[List[str]], optional): BCC recipients. Defaults to None.
            reply_to (Optional[str], optional): Reply-to email. Defaults to None.
        """
        message = self.get_mail_message(recipients, subject, html, cc, bcc, reply_to)

        fm = FastMail(self.conf)
        await fm.send_message(message)

        recipient_list = recipients if isinstance(recipients, list) else [recipients]
        logger.info(f"Typed email sent to {recipient_list} with subject '{subject}'")

    async def send_welcome_email(
        self,
        name: str,
        email: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ):
        """Send welcome email to new user

        Args:
            name (str): User name
            email (str): User email
            cc (Optional[List[str]], optional): CC recipients. Defaults to None.
            bcc (Optional[List[str]], optional): BCC recipients. Defaults to None.
            reply_to (Optional[str], optional): Reply-to email. Defaults to None.
        """
        subject = "Welcome to Media Transcribe"
        html = get_welcome_email_template(name)
        message = self.get_mail_message([email], subject, html, cc, bcc, reply_to)

        fm = FastMail(self.conf)
        await fm.send_message(message)

        logger.info(f"Welcome email sent to {name} ({email})")

    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        html: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ):
        """Send bulk email to multiple recipients

        Args:
            recipients (List[str]): List of email recipients
            subject (str): Email subject
            html (str): HTML email content
            cc (Optional[List[str]], optional): CC recipients. Defaults to None.
            bcc (Optional[List[str]], optional): BCC recipients. Defaults to None.
            reply_to (Optional[str], optional): Reply-to email. Defaults to None.
        """
        message = self.get_mail_message(recipients, subject, html, cc, bcc, reply_to)

        fm = FastMail(self.conf)
        await fm.send_message(message)

        logger.info(
            f"Bulk email sent to {len(recipients)} recipients with subject '{subject}'"
        )
