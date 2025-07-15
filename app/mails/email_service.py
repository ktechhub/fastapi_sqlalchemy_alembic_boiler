from app.mails.custom_email_service import EmailService as CustomEmailService
from app.mails.mailjet_service import EmailService as MailjetEmailService
from app.mails.sendgrid_service import EmailService as SendgridEmailService
from app.core.config import settings


if settings.EMAIL_SERVICE == "custom":
    email_service = CustomEmailService(
        sender=settings.MAIL_FROM,
        sender_name=settings.MAIL_FROM_NAME,
    )
elif settings.EMAIL_SERVICE == "mailjet":
    email_service = MailjetEmailService(
        sender=settings.MAIL_FROM,
        sender_name=settings.MAIL_FROM_NAME,
    )
elif settings.EMAIL_SERVICE == "sendgrid":
    email_service = SendgridEmailService(
        sender=settings.MAIL_FROM,
        sender_name=settings.MAIL_FROM_NAME,
    )
else:
    raise ValueError(f"Invalid email service: {settings.EMAIL_SERVICE}")
