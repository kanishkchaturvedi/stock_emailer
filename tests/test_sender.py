"""Tests for email sender module supporting SMTP and Resend API."""

import smtplib
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from smart_money_tracker.email.sender import EmailSender


class TestEmailSenderInitialization:
    """Test suite for EmailSender initialization."""

    def test_initializes_with_explicit_smtp_provider(self):
        """Test that EmailSender initializes with explicit SMTP provider."""
        sender = EmailSender(provider="smtp")
        assert sender.provider == "smtp"

    def test_initializes_with_explicit_resend_provider(self):
        """Test that EmailSender initializes with explicit Resend provider."""
        sender = EmailSender(provider="resend")
        assert sender.provider == "resend"

    def test_initializes_with_explicit_mock_provider(self):
        """Test that EmailSender initializes with explicit mock provider."""
        sender = EmailSender(provider="mock")
        assert sender.provider == "mock"

    def test_raises_on_invalid_provider(self):
        """Test that EmailSender raises ValueError on invalid provider."""
        with pytest.raises(ValueError, match="Invalid provider"):
            EmailSender(provider="invalid")

    @patch("smart_money_tracker.email.sender.settings")
    def test_auto_detects_resend_provider(self, mock_settings):
        """Test that auto provider detection prefers Resend API key."""
        mock_settings.resend_api_key = "test_key"
        mock_settings.smtp_email = "test@gmail.com"
        mock_settings.smtp_password = "password"

        sender = EmailSender(provider="auto")
        assert sender.provider == "resend"

    @patch("smart_money_tracker.email.sender.settings")
    def test_auto_detects_smtp_provider(self, mock_settings):
        """Test that auto provider detection falls back to SMTP."""
        mock_settings.resend_api_key = None
        mock_settings.smtp_email = "test@gmail.com"
        mock_settings.smtp_password = "password"

        sender = EmailSender(provider="auto")
        assert sender.provider == "smtp"

    @patch("smart_money_tracker.email.sender.settings")
    def test_auto_defaults_to_mock_provider(self, mock_settings):
        """Test that auto provider detection defaults to mock."""
        mock_settings.resend_api_key = None
        mock_settings.smtp_email = None
        mock_settings.smtp_password = None

        sender = EmailSender(provider="auto")
        assert sender.provider == "mock"


class TestEmailSenderSendMethod:
    """Test suite for send() method dispatch."""

    def test_send_dispatches_to_smtp(self):
        """Test that send() dispatches to _send_smtp for SMTP provider."""
        sender = EmailSender(provider="smtp")

        with patch.object(sender, "_send_smtp", return_value=True) as mock_smtp:
            result = sender.send("test@example.com", "Subject", "<html></html>")
            assert result is True
            mock_smtp.assert_called_once()

    def test_send_dispatches_to_resend(self):
        """Test that send() dispatches to _send_resend for Resend provider."""
        sender = EmailSender(provider="resend")

        with patch.object(sender, "_send_resend", return_value=True) as mock_resend:
            result = sender.send("test@example.com", "Subject", "<html></html>")
            assert result is True
            mock_resend.assert_called_once()

    def test_send_dispatches_to_mock(self):
        """Test that send() dispatches to _send_mock for mock provider."""
        sender = EmailSender(provider="mock")

        with patch.object(sender, "_send_mock", return_value=True) as mock_mock:
            result = sender.send("test@example.com", "Subject", "<html></html>")
            assert result is True
            mock_mock.assert_called_once()

    def test_send_passes_parameters_correctly(self):
        """Test that send() passes parameters correctly to dispatch methods."""
        sender = EmailSender(provider="mock")

        with patch.object(sender, "_send_mock", return_value=True) as mock_mock:
            sender.send(
                "recipient@example.com",
                "Test Subject",
                "<html>Body</html>",
                "Plain text",
            )

            mock_mock.assert_called_once_with(
                "recipient@example.com",
                "Test Subject",
                "<html>Body</html>",
                "Plain text",
            )


class TestSmtpSending:
    """Test suite for SMTP email sending."""

    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_smtp_success(self, mock_settings, mock_smtp_class):
        """Test successful SMTP email sending."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "app_password"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")
        result = sender._send_smtp(
            "recipient@example.com",
            "Test Subject",
            "<html>Test content</html>",
            "Test content",
        )

        assert result is True
        mock_smtp_class.assert_called_once_with("smtp.gmail.com", 465)
        mock_server.login.assert_called_once_with(
            "sender@gmail.com", "app_password"
        )
        mock_server.sendmail.assert_called_once()

    @patch("smart_money_tracker.email.sender.settings")
    def test_send_smtp_missing_email_config(self, mock_settings):
        """Test SMTP sending fails when email is not configured."""
        mock_settings.smtp_email = None
        mock_settings.smtp_password = "password"

        sender = EmailSender(provider="smtp")

        with pytest.raises(ValueError, match="SMTP email and password not configured"):
            sender._send_smtp(
                "recipient@example.com", "Subject", "<html></html>", "text"
            )

    @patch("smart_money_tracker.email.sender.settings")
    def test_send_smtp_missing_password_config(self, mock_settings):
        """Test SMTP sending fails when password is not configured."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = None

        sender = EmailSender(provider="smtp")

        with pytest.raises(ValueError, match="SMTP email and password not configured"):
            sender._send_smtp(
                "recipient@example.com", "Subject", "<html></html>", "text"
            )

    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_smtp_authentication_error(self, mock_settings, mock_smtp_class):
        """Test SMTP sending handles authentication errors."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "wrong_password"

        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
            535, "Incorrect password"
        )
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")

        with pytest.raises(smtplib.SMTPAuthenticationError):
            sender._send_smtp(
                "recipient@example.com",
                "Subject",
                "<html></html>",
                "text",
            )

    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_smtp_creates_multipart_message(self, mock_settings, mock_smtp_class):
        """Test SMTP creates proper MIME multipart message."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "app_password"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")
        sender._send_smtp(
            "recipient@example.com",
            "Test Subject",
            "<html>HTML content</html>",
            "Plain text content",
        )

        # Verify sendmail was called
        assert mock_server.sendmail.called
        call_args = mock_server.sendmail.call_args

        # Extract the message string
        msg_string = call_args[0][2]

        # Verify message contains expected headers and content
        assert "Subject: Test Subject" in msg_string
        assert "From: sender@gmail.com" in msg_string
        assert "To: recipient@example.com" in msg_string
        assert "Plain text content" in msg_string
        assert "HTML content" in msg_string

    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_smtp_without_text_version(self, mock_settings, mock_smtp_class):
        """Test SMTP sending without plain text version."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "app_password"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")
        result = sender._send_smtp(
            "recipient@example.com",
            "Test Subject",
            "<html>HTML only</html>",
            text=None,
        )

        assert result is True
        call_args = mock_server.sendmail.call_args
        msg_string = call_args[0][2]

        # Should have default text message
        assert "Please view this email in HTML format" in msg_string
        assert "HTML only" in msg_string


class TestResendSending:
    """Test suite for Resend API email sending."""

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_resend_success(self, mock_settings, mock_post):
        """Test successful Resend API email sending."""
        mock_settings.resend_api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        sender = EmailSender(provider="resend")
        result = sender._send_resend(
            "recipient@example.com",
            "Test Subject",
            "<html>Test content</html>",
            "Plain text",
        )

        assert result is True
        mock_post.assert_called_once()

        # Verify API call details
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.resend.com/emails"
        assert (
            call_args[1]["headers"]["Authorization"]
            == "Bearer test_api_key"
        )
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["json"]["to"] == "recipient@example.com"
        assert call_args[1]["json"]["subject"] == "Test Subject"

    @patch("smart_money_tracker.email.sender.settings")
    def test_send_resend_missing_api_key(self, mock_settings):
        """Test Resend sending fails when API key is not configured."""
        mock_settings.resend_api_key = None

        sender = EmailSender(provider="resend")

        with pytest.raises(ValueError, match="Resend API key not configured"):
            sender._send_resend(
                "recipient@example.com", "Subject", "<html></html>", "text"
            )

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_resend_api_error(self, mock_settings, mock_post):
        """Test Resend sending handles API errors."""
        mock_settings.resend_api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_response.text = '{"error": "Invalid API key"}'
        mock_post.return_value = mock_response

        sender = EmailSender(provider="resend")

        with pytest.raises(requests.exceptions.HTTPError):
            sender._send_resend(
                "recipient@example.com",
                "Subject",
                "<html></html>",
                "text",
            )

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_resend_request_exception(self, mock_settings, mock_post):
        """Test Resend sending handles request exceptions."""
        mock_settings.resend_api_key = "test_api_key"

        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Failed to connect"
        )

        sender = EmailSender(provider="resend")

        with pytest.raises(requests.exceptions.ConnectionError):
            sender._send_resend(
                "recipient@example.com",
                "Subject",
                "<html></html>",
                "text",
            )

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_resend_payload_structure(self, mock_settings, mock_post):
        """Test Resend API payload structure."""
        mock_settings.resend_api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        sender = EmailSender(provider="resend")
        sender._send_resend(
            "recipient@example.com",
            "Test Subject",
            "<html>HTML</html>",
            "Text",
        )

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]

        assert payload["from"] == "noreply@smartmoneytracker.com"
        assert payload["to"] == "recipient@example.com"
        assert payload["subject"] == "Test Subject"
        assert payload["html"] == "<html>HTML</html>"
        assert payload["text"] == "Text"

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_resend_without_text(self, mock_settings, mock_post):
        """Test Resend API payload without text version."""
        mock_settings.resend_api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        sender = EmailSender(provider="resend")
        sender._send_resend(
            "recipient@example.com",
            "Subject",
            "<html>HTML</html>",
            text=None,
        )

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]

        # Text key should not be in payload when not provided
        assert "text" not in payload
        assert payload["html"] == "<html>HTML</html>"


class TestMockSending:
    """Test suite for mock email sending."""

    def test_send_mock_always_succeeds(self):
        """Test that mock sending always returns True."""
        sender = EmailSender(provider="mock")

        result = sender._send_mock(
            "recipient@example.com",
            "Subject",
            "<html>content</html>",
            "text",
        )

        assert result is True

    def test_send_mock_without_text(self):
        """Test mock sending without text version."""
        sender = EmailSender(provider="mock")

        result = sender._send_mock(
            "recipient@example.com",
            "Subject",
            "<html>content</html>",
            text=None,
        )

        assert result is True

    def test_send_mock_with_various_emails(self):
        """Test mock sending with various email addresses."""
        sender = EmailSender(provider="mock")

        emails = [
            "user@example.com",
            "test.user+tag@domain.co.uk",
            "name.surname@subdomain.example.com",
        ]

        for email in emails:
            result = sender._send_mock(email, "Subject", "<html></html>")
            assert result is True


class TestRetryBehavior:
    """Test suite for retry behavior on transient failures."""

    @patch("smart_money_tracker.email.sender.settings")
    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    def test_send_retries_on_smtp_error(self, mock_smtp_class, mock_settings):
        """Test that send() retries on SMTP errors."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "password"

        # First two attempts fail, third succeeds
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = [
            smtplib.SMTPException("Temporary error"),
            smtplib.SMTPException("Temporary error"),
            None,  # Success
        ]
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")

        # Should succeed on third attempt due to retry decorator
        result = sender.send(
            "recipient@example.com",
            "Subject",
            "<html></html>",
        )

        assert result is True
        assert mock_server.sendmail.call_count == 3

    @patch("smart_money_tracker.email.sender.settings")
    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    def test_send_fails_after_all_retries(self, mock_smtp_class, mock_settings):
        """Test that send() fails after exhausting retries."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "password"

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPException("Persistent error")
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")

        with pytest.raises(smtplib.SMTPException):
            sender.send(
                "recipient@example.com",
                "Subject",
                "<html></html>",
            )

        # Should have tried 3 times
        assert mock_server.sendmail.call_count == 3

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_send_retries_on_resend_timeout(self, mock_settings, mock_post):
        """Test that send() retries on Resend API timeouts."""
        mock_settings.resend_api_key = "test_api_key"

        # First two attempts timeout, third succeeds
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        mock_post.side_effect = [
            requests.exceptions.Timeout("Request timeout"),
            requests.exceptions.Timeout("Request timeout"),
            mock_response,  # Success
        ]

        sender = EmailSender(provider="resend")

        # Should succeed on third attempt due to retry decorator
        result = sender.send(
            "recipient@example.com",
            "Subject",
            "<html></html>",
        )

        assert result is True
        assert mock_post.call_count == 3


class TestEmailAddressVariations:
    """Test suite for various email address formats."""

    @patch("smart_money_tracker.email.sender.settings")
    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    def test_smtp_with_various_email_formats(self, mock_smtp_class, mock_settings):
        """Test SMTP sending with various email address formats."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "password"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")

        emails = [
            "simple@example.com",
            "user+tag@example.co.uk",
            "first.last@subdomain.example.com",
        ]

        for email in emails:
            mock_server.reset_mock()
            result = sender._send_smtp(email, "Subject", "<html></html>")
            assert result is True
            mock_server.sendmail.assert_called_once()
            # Verify recipient is in sendmail call
            call_args = mock_server.sendmail.call_args[0]
            assert email in call_args[1]

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_resend_with_various_email_formats(self, mock_settings, mock_post):
        """Test Resend API with various email address formats."""
        mock_settings.resend_api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        sender = EmailSender(provider="resend")

        emails = [
            "simple@example.com",
            "user+tag@example.co.uk",
            "first.last@subdomain.example.com",
        ]

        for email in emails:
            mock_post.reset_mock()
            result = sender._send_resend(email, "Subject", "<html></html>")
            assert result is True
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["to"] == email


class TestMessageFormatting:
    """Test suite for email message formatting."""

    @patch("smart_money_tracker.email.sender.smtplib.SMTP_SSL")
    @patch("smart_money_tracker.email.sender.settings")
    def test_smtp_message_headers(self, mock_settings, mock_smtp_class):
        """Test SMTP message contains required headers."""
        mock_settings.smtp_email = "sender@gmail.com"
        mock_settings.smtp_password = "password"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sender = EmailSender(provider="smtp")
        sender._send_smtp(
            "recipient@example.com",
            "Important Report",
            "<html>Content</html>",
            "Content text",
        )

        msg_string = mock_server.sendmail.call_args[0][2]

        assert "Subject: Important Report" in msg_string
        assert "From: sender@gmail.com" in msg_string
        assert "To: recipient@example.com" in msg_string

    @patch("smart_money_tracker.email.sender.requests.post")
    @patch("smart_money_tracker.email.sender.settings")
    def test_resend_message_fields(self, mock_settings, mock_post):
        """Test Resend API message contains required fields."""
        mock_settings.resend_api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        sender = EmailSender(provider="resend")
        sender._send_resend(
            "recipient@example.com",
            "Important Report",
            "<h1>Report</h1>",
            "Report text",
        )

        payload = mock_post.call_args[1]["json"]

        assert payload["from"] == "noreply@smartmoneytracker.com"
        assert payload["to"] == "recipient@example.com"
        assert payload["subject"] == "Important Report"
        assert payload["html"] == "<h1>Report</h1>"
        assert payload["text"] == "Report text"
