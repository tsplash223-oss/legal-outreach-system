import os
import logging
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from dotenv import load_dotenv

load_dotenv()

SMTP_EMAIL_ENV_NAMES = ("GMAIL_ADDRESS", "SMTP_EMAIL", "EMAIL_ADDRESS")
SMTP_PASSWORD_ENV_NAMES = ("GMAIL_APP_PASSWORD", "SMTP_PASSWORD", "EMAIL_APP_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 30
SMTP_CONFIGURATION_ERROR = "SMTP connection failed. Check Gmail app password and Railway environment variables."

logger = logging.getLogger(__name__)


def normalize_env_secret(value: str, remove_internal_whitespace: bool = False):
    cleaned = (value or "").strip()

    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()

    if remove_internal_whitespace:
        cleaned = "".join(cleaned.split())

    return cleaned


def get_smtp_credentials():
    gmail_address = ""
    gmail_password = ""

    for env_name in SMTP_EMAIL_ENV_NAMES:
        value = normalize_env_secret(os.getenv(env_name, ""))
        if value:
            gmail_address = value
            break

    for env_name in SMTP_PASSWORD_ENV_NAMES:
        value = normalize_env_secret(os.getenv(env_name, ""), remove_internal_whitespace=True)
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
        "smtp_host": SMTP_HOST,
        "smtp_port": SMTP_PORT,
        "gmail_address_present": gmail_address_present,
        "gmail_app_password_present": gmail_password_present,
        "gmail_app_password_length": len(gmail_password),
        "gmail_password_present": gmail_password_present,
    }


def log_smtp_config_status():
    config = check_smtp_config()

    logger.info(
        "SMTP config status host=%s port=%s sender_email_present=%s "
        "app_password_present=%s app_password_length=%s configured=%s",
        config["smtp_host"],
        config["smtp_port"],
        config["gmail_address_present"],
        config["gmail_app_password_present"],
        config["gmail_app_password_length"],
        config["configured"],
    )


def send_email(to_email, subject, body):
    gmail_address, gmail_password = get_smtp_credentials()

    if not gmail_address or not gmail_password:
        log_smtp_config_status()
        raise EmailSendError(SMTP_CONFIGURATION_ERROR)

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
        log_smtp_config_status()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.starttls()

            try:
                server.login(gmail_address, gmail_password)
            except smtplib.SMTPAuthenticationError as exc:
                raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc

            server.send_message(msg)
    except EmailSendError:
        raise
    except smtplib.SMTPConnectError as exc:
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except smtplib.SMTPServerDisconnected as exc:
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except smtplib.SMTPException as exc:
        logger.exception("SMTP send failed: %s", safe_email_error_message(exc))
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except (TimeoutError, OSError) as exc:
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except Exception as exc:
        raise EmailSendError(f"Email send failed: {safe_email_error_message(exc)}") from exc

    return True


log_smtp_config_status()
