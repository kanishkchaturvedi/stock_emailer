"""Email sender supporting SMTP (Gmail) and Resend API delivery."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

from smart_money_tracker.config.settings import settings
from smart_money_tracker.utils.logger import get_logger
from smart_money_tracker.utils.retries import retry

logger = get_logger(__name__)


class EmailSender:
    """Sends emails via SMTP (Gmail) or Resend API."""

    def __init__(self, provider: str = "auto") -> None:
        """
        Initialize the email sender with the specified provider.

        Args:
            provider: Email provider to use ('smtp', 'resend', 'mock', or 'auto').
                     If 'auto', detects provider from settings with priority:
                     resend_api_key > smtp_email > mock

        Raises:
            ValueError: If provider is invalid or no provider can be auto-detected.
        """
        if provider == "auto":
            # Auto-detect provider from settings
            if settings.resend_api_key:
                self.provider = "resend"
                logger.info("Auto-detected Resend API provider")
            elif settings.smtp_email:
                self.provider = "smtp"
                logger.info("Auto-detected SMTP provider")
            else:
                self.provider = "mock"
                logger.warning(
                    "No email provider configured. Using mock provider for testing."
                )
        else:
            if provider not in ("smtp", "resend", "mock"):
                raise ValueError(
                    f"Invalid provider: {provider}. "
                    f"Must be 'smtp', 'resend', 'mock', or 'auto'."
                )
            self.provider = provider

        logger.info(f"EmailSender initialized with provider: {self.provider}")

    @retry(max_attempts=3, base_delay=1.0, backoff=2.0)
    def send(
        self,
        to_email: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> bool:
        """
        Send an email using the configured provider.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html: HTML email body
            text: Plain text email body (optional, defaults to None)

        Returns:
            True if email was sent successfully

        Raises:
            Exception: If email sending fails after retry attempts
        """
        if self.provider == "smtp":
            return self._send_smtp(to_email, subject, html, text)
        elif self.provider == "resend":
            return self._send_resend(to_email, subject, html, text)
        else:  # mock
            return self._send_mock(to_email, subject, html, text)

    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> bool:
        """
        Send email via Gmail SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html: HTML email body
            text: Plain text email body (optional)

        Returns:
            True if email was sent successfully

        Raises:
            ValueError: If SMTP settings are not configured
            smtplib.SMTPAuthenticationError: If authentication fails
            Exception: If SMTP connection or sending fails
        """
        if not settings.smtp_email or not settings.smtp_password:
            raise ValueError(
                "SMTP email and password not configured in settings. "
                "Set SMTP_EMAIL and SMTP_PASSWORD environment variables."
            )

        try:
            # Create multipart message (can contain both text and HTML)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.smtp_email
            msg["To"] = to_email

            # Attach text version first, then HTML (per MIME standards)
            if text:
                msg.attach(MIMEText(text, "plain"))
            else:
                # If no plain text provided, create a simple one from HTML
                msg.attach(MIMEText("Please view this email in HTML format.", "plain"))

            # Attach HTML version
            msg.attach(MIMEText(html, "html"))

            # Send via Gmail SMTP with SSL
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(settings.smtp_email, settings.smtp_password)
                server.sendmail(settings.smtp_email, [to_email], msg.as_string())

            logger.info(
                f"Email sent successfully via SMTP to {to_email} with subject: {subject}"
            )
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            raise
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error while sending email to {to_email}: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error sending email via SMTP: {type(e).__name__}: {str(e)}"
            )
            raise

    def _send_resend(
        self,
        to_email: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> bool:
        """
        Send email via Resend API.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html: HTML email body
            text: Plain text email body (optional)

        Returns:
            True if email was sent successfully

        Raises:
            ValueError: If Resend API key is not configured
            requests.exceptions.RequestException: If API request fails
        """
        if not settings.resend_api_key:
            raise ValueError(
                "Resend API key not configured in settings. "
                "Set RESEND_API_KEY environment variable."
            )

        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "from": "noreply@smartmoneytracker.com",
                "to": to_email,
                "subject": subject,
                "html": html,
            }

            # Include text version if provided
            if text:
                payload["text"] = text

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(
                f"Email sent successfully via Resend API to {to_email} "
                f"with subject: {subject}"
            )
            return True

        except requests.exceptions.HTTPError as e:
            response_text = "N/A"
            if hasattr(e, "response") and e.response is not None:
                response_text = e.response.text
            logger.error(
                f"Resend API HTTP error while sending to {to_email}: {str(e)} "
                f"Response: {response_text}"
            )
            raise
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Resend API request error while sending to {to_email}: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error sending email via Resend: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise

    def _send_mock(
        self,
        to_email: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> bool:
        """
        Mock email sending for development/testing.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html: HTML email body
            text: Plain text email body (optional)

        Returns:
            True (always succeeds)
        """
        logger.info(
            f"Mock: Email sent to {to_email} with subject: {subject} "
            f"(text version: {bool(text)}, html version: {bool(html)})"
        )
        return True
