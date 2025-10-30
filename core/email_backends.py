"""
Custom email backend for SendGrid Web API.

Railway (and many PaaS platforms) block outbound SMTP connections.
This backend uses SendGrid's official Web API which works reliably
on all platforms via HTTPS.
"""
import logging
import os
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address

logger = logging.getLogger('auth')


class SendGridWebAPIBackend(BaseEmailBackend):
    """
    Email backend that uses SendGrid's official Web API.

    This solves the issue of platforms like Railway blocking outbound
    SMTP connections on ports 25 and 587.

    Requires:
    - pip install sendgrid
    - SENDGRID_API_KEY environment variable

    Usage in settings.py:
        EMAIL_BACKEND = 'core.email_backends.SendGridWebAPIBackend'
        SENDGRID_API_KEY = 'SG.your-api-key-here'  # nosec - example value
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = getattr(settings, 'SENDGRID_API_KEY',
                               None) or os.environ.get('SENDGRID_API_KEY')

        if not self.api_key:
            error_msg = "SENDGRID_API_KEY not configured in settings or environment"
            logger.error(error_msg)
            if not fail_silently:
                raise ValueError(error_msg)

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number sent.
        """
        if not email_messages:
            return 0

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
        except ImportError as e:
            error_msg = "SendGrid library not installed. Run: pip install sendgrid"
            logger.error(error_msg)
            if not self.fail_silently:
                raise ImportError(error_msg) from e
            return 0

        sg = SendGridAPIClient(self.api_key)
        num_sent = 0

        for message in email_messages:
            try:
                # Extract email addresses
                from_email = sanitize_address(
                    message.from_email, message.encoding)
                to_emails = [sanitize_address(
                    addr, message.encoding) for addr in message.to]

                # Build SendGrid message
                mail = Mail(
                    from_email=from_email,
                    to_emails=to_emails,
                    subject=message.subject,
                )

                # Add plain text body
                if message.body:
                    mail.add_content(Content("text/plain", message.body))

                # Add HTML alternative if present
                if hasattr(message, 'alternatives') and message.alternatives:
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            mail.add_content(HtmlContent(content))
                            break

                # Send via Web API
                logger.info(
                    f"Sending email to {', '.join(message.to)} via SendGrid Web API...")
                response = sg.send(mail)

                # Check response status
                if response.status_code in (200, 201, 202):
                    num_sent += 1
                    logger.info(
                        f"✓ Email sent successfully to {', '.join(message.to)} "
                        f"(status: {response.status_code})"
                    )
                else:
                    error_msg = f"SendGrid API returned status {response.status_code}: {response.body}"
                    logger.error(error_msg)
                    if not self.fail_silently:
                        raise Exception(error_msg)

            except Exception as e:
                logger.error(f"Failed to send email via SendGrid Web API: {e}")
                if not self.fail_silently:
                    raise

        return num_sent
