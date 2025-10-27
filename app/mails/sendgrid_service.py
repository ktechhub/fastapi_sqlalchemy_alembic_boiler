from sendgrid import SendGridAPIClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.core.config import settings
from app.core.loggers import app_logger as logger
from .email_templates import get_basic_template, get_welcome_email_template


class EmailService:
    def __init__(self, sender: str = f"no-reply@{settings.DOMAIN}.com"):
        self.sender = sender
        self.sendgrid = SendGridAPIClient(settings.SENDGRID_API_KEY)

    def get_mail(
        self,
        recipients: list,
        subject: str,
        html: str,
        cc: list = None,
        bcc: list = None,
        reply_to: str = None,
    ):
        """Get mail object

        Args:
            recipients (list): Email recipient
            subject (str): Email subject
            html (str): Email content

        Returns:
            Mail: Mail object
        """
        mail = Mail(
            from_email=Email(self.sender),
            to_emails=[To(recipient) for recipient in recipients],
            subject=subject,
            html_content=Content("text/html", html),
        )
        if cc:
            mail.cc = [Email(cc) for cc in cc]
        if bcc:
            mail.bcc = [Email(bcc) for bcc in bcc]
        if reply_to:
            mail.reply_to = Email(reply_to)
        return mail

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
        """Send email using SendGrid
        Args:
            recipients (list): Email recipient
            subject (str): Email subject
            content (str): Email content

        Returns:
            None
        """
        html = get_basic_template(settings.APP_NAME, subject, salutation, content)
        mail = self.get_mail(recipients, subject, html, cc, bcc, reply_to)
        self.sendgrid.send(mail)
        logger.info(f"Email sent to {recipients} with subject '{subject}'")

    async def send_typed_email(
        self,
        recipients: list,
        subject: str,
        html: str,
        cc: list = None,
        bcc: list = None,
        reply_to: str = None,
    ):
        """Send email using SendGrid
        Args:
            recipients (list): Email recipient
            subject (str): Email subject
            html (str): Email content

        Returns:
            None
        """
        mail = self.get_mail(recipients, subject, html, cc, bcc, reply_to)
        self.sendgrid.send(mail)
        logger.info(f"Email sent to {recipients} with subject '{subject}'")

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
        mail = self.get_mail([email], subject, html, cc, bcc, reply_to)
        self.sendgrid.send(mail)
        logger.info(f"Email sent to {email} with subject '{subject}'")
