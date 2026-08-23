import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailProvider:
    """
    Abstractions for sending emails using SMTP.
    Supports attachments and HTML bodies.
    """
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Tuple[str, bytes, str]]] = None, # (filename, content, mimetype)
    ) -> bool:
        """
        Sends an email. Returns True if successful, False otherwise.
        """
        if not settings.EMAIL_ENABLED:
            logger.info(f"Email disabled. Mock send to {to_email}: {subject}")
            return True

        try:
            message = MIMEMultipart("mixed")
            message["Subject"] = subject
            message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            message["To"] = to_email

            # Create body part
            body_part = MIMEMultipart("alternative")
            body_part.attach(MIMEText(body_text, "plain"))
            if body_html:
                body_part.attach(MIMEText(body_html, "html"))
            message.attach(body_part)

            # Add attachments
            if attachments:
                for filename, content, mimetype in attachments:
                    maintype, subtype = mimetype.split("/", 1)
                    part = MIMEApplication(content, _subtype=subtype)
                    part.add_header("Content-Disposition", "attachment", filename=filename)
                    message.attach(part)

            # Connect and send
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

email_provider = EmailProvider()
