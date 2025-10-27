from mailjet_rest import Client
from app.core.config import settings
from app.core.loggers import app_logger as logger
from .email_templates import get_basic_template, get_welcome_email_template


class EmailService:
    def __init__(
        self,
        sender: str = f"no-reply@{settings.DOMAIN}.com",
        sender_name: str = settings.APP_NAME,
    ):
        self.sender = sender
        self.sender_name = sender_name
        self.mailjet = Client(
            auth=(settings.MAILJET_API_KEY, settings.MAILJET_API_SECRET), version="v3.1"
        )

    def get_mail_data(
        self,
        recipients: list,
        subject: str,
        html: str,
        cc: list = None,
        bcc: list = None,
        reply_to: str = None,
    ):
        """Get mail data structure for Mailjet

        Args:
            recipients (list): Email recipients
            subject (str): Email subject
            html (str): HTML email content

        Returns:
            dict: Mailjet data structure
        """
        to_emails = []
        for recipient in recipients:
            if isinstance(recipient, dict):
                to_emails.append(
                    {"Email": recipient["email"], "Name": recipient.get("name", "")}
                )
            else:
                to_emails.append({"Email": recipient, "Name": ""})

        message = {
            "From": {"Email": self.sender, "Name": self.sender_name},
            "To": to_emails,
            "Subject": subject,
            "HTMLPart": html,
        }
        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc
        if reply_to:
            message["ReplyTo"] = reply_to

        return {"Messages": [message]}

    async def send_email(
        self,
        recipients: list,
        subject: str,
        salutation: str,
        content: str,
        cc: list = None,
        bcc: list = None,
        reply_to: str = None,
    ):
        """Send email using Mailjet
        Args:
            recipients (list): Email recipients
            subject (str): Email subject
            salutation (str): Email salutation
            content (str): Email content

        Returns:
            None
        """
        html = get_basic_template(settings.APP_NAME, subject, salutation, content)
        data = self.get_mail_data(recipients, subject, html, cc, bcc, reply_to)
        result = self.mailjet.send.create(data=data)
        logger.info(
            f"Email sent to {recipients} with subject '{subject}'. Status: {result.status_code}"
        )

    async def send_typed_email(
        self,
        recipients: list,
        subject: str,
        html: str,
        cc: list = None,
        bcc: list = None,
        reply_to: str = None,
    ):
        """Send email using Mailjet with custom HTML
        Args:
            recipients (list): Email recipients
            subject (str): Email subject
            html (str): HTML email content

        Returns:
            None
        """
        data = self.get_mail_data(recipients, subject, html, cc, bcc, reply_to)
        result = self.mailjet.send.create(data=data)
        logger.info(
            f"Typed email sent to {recipients} with subject '{subject}'. Status: {result.status_code}"
        )

    async def send_welcome_email(
        self,
        name: str,
        email: str,
        cc: list = None,
        bcc: list = None,
        reply_to: str = None,
    ):
        """Send welcome email to new user
        Args:
            name (str): User name
            email (str): User email

        Returns:
            None
        """
        subject = f"Welcome to {settings.APP_NAME}"
        html = get_welcome_email_template(name)
        data = self.get_mail_data([email], subject, html, cc, bcc, reply_to)
        result = self.mailjet.send.create(data=data)
        logger.info(
            f"Welcome email sent to {name} ({email}). Status: {result.status_code}"
        )
