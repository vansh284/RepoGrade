import os
import smtplib
from email.mime.text import MIMEText
from typing import Protocol


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpEmailSender:
    def __init__(self) -> None:
        self.smtp_email = os.environ.get("SMTP_EMAIL", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")

    def send(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.smtp_email
        msg["To"] = to

        with smtplib.SMTP("outlook.office365.com", 587) as server:
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)


_sender: EmailSender | None = None


def get_email_sender() -> EmailSender:
    global _sender
    if _sender is None:
        _sender = SmtpEmailSender()
    return _sender
