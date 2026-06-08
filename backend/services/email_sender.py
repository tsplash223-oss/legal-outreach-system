import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from dotenv import load_dotenv

load_dotenv()

SMTP_EMAIL_ENV_NAMES = ("GMAIL_ADDRESS", "SMTP_EMAIL", "EMAIL_ADDRESS")
SMTP_PASSWORD_ENV_NAMES = ("GMAIL_APP_PASSWORD", "SMTP_PASSWORD", "EMAIL_APP_PASSWORD")


def get_smtp_credentials():
    gmail_address = ""
    gmail_password = ""

    for env_name in SMTP_EMAIL_ENV_NAMES:
        value = os.getenv(env_name, "").strip()
        if value:
            gmail_address = value
            break

    for env_name in SMTP_PASSWORD_ENV_NAMES:
        value = os.getenv(env_name, "").replace(" ", "").strip()
        if value:
            gmail_password = value
            break

    return gmail_address, gmail_password


GMAIL_ADDRESS, GMAIL_APP_PASSWORD = get_smtp_credentials()


class EmailSendError(Exception):
    pass


def safe_email_error_message(error):
    message = str(error) or error.__class__.__name__
    gmail_address, gmail_password = get_smtp_credentials()

    if gmail_password:
        message = message.replace(gmail_password, "[redacted]")

    if gmail_address:
        message = message.replace(gmail_address, "[gmail address]")

    return message


def check_smtp_config():
    gmail_address, gmail_password = get_smtp_credentials()
    gmail_address_present = bool(gmail_address)
    gmail_password_present = bool(gmail_password)

    return {
        "configured": gmail_address_present and gmail_password_present,
        "gmail_address_present": gmail_address_present,
        "gmail_password_present": gmail_password_present,
        "gmail_address": gmail_address,
        "password_length": len(gmail_password),
    }


def log_smtp_config_status():
    config = check_smtp_config()

    print(f"SMTP configured: {config['configured']}")
    print(f"Gmail address present: {config['gmail_address_present']}")
    print(f"Password present: {config['gmail_password_present']}")
    print(f"Password length: {config['password_length']}")


def send_email(to_email, subject, body):
    gmail_address, gmail_password = get_smtp_credentials()

    if not gmail_address or not gmail_password:
        raise EmailSendError("Missing Gmail SMTP settings.")

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_email

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(body, "html", "utf-8"))
    msg.attach(alternative)

    signature_path = Path(__file__).resolve().parent.parent / "signature.png.png"

    if signature_path.exists():
        with open(signature_path, "rb") as img_file:
            img = MIMEImage(img_file.read())
            img.add_header("Content-ID", "<signature_image>")
            img.add_header("Content-Disposition", "inline")
            img.add_header("X-Attachment-Id", "signature_image")
            msg.attach(img)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()

            try:
                server.login(gmail_address, gmail_password)
            except smtplib.SMTPAuthenticationError as exc:
                raise EmailSendError("Gmail login failed. Check Gmail App Password and 2-Step Verification.") from exc

            server.send_message(msg)
    except EmailSendError:
        raise
    except smtplib.SMTPConnectError as exc:
        raise EmailSendError("SMTP connection failed.") from exc
    except smtplib.SMTPServerDisconnected as exc:
        raise EmailSendError("SMTP server disconnected.") from exc
    except smtplib.SMTPException as exc:
        raise EmailSendError(f"Email send failed: {safe_email_error_message(exc)}") from exc
    except (TimeoutError, OSError) as exc:
        raise EmailSendError("SMTP connection failed.") from exc
    except Exception as exc:
        raise EmailSendError(f"Email send failed: {safe_email_error_message(exc)}") from exc

    return True


log_smtp_config_status()
