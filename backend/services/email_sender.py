import os
import logging
import smtplib
import base64
import re
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from dotenv import load_dotenv
from services.gmail_reply_tracker import (
    CREDENTIALS_PATH,
    GMAIL_CREDENTIALS_ENV,
    GMAIL_TOKEN_ENV,
    TOKEN_PATH,
    ensure_gmail_api_files_from_env,
    gmail_file_config_for_profile,
    import_gmail_dependencies,
)
from business_profiles import (
    DRIVERS_ED_PROFILE_NAME,
    GMAIL_PROFILE_NOT_CONFIGURED_MESSAGE,
    HOPE_PROFILE_NAME,
)

load_dotenv()

SMTP_EMAIL_ENV_NAMES = ("GMAIL_ADDRESS", "SMTP_EMAIL", "EMAIL_ADDRESS")
SMTP_PASSWORD_ENV_NAMES = ("GMAIL_APP_PASSWORD", "SMTP_PASSWORD", "EMAIL_APP_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 30
SMTP_CONFIGURATION_ERROR = "SMTP connection failed. Check Gmail app password and Railway environment variables."
GMAIL_SEND_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GMAIL_API_CONFIGURATION_ERROR = (
    "Gmail API send failed. Check Gmail API credentials/token and Railway environment variables."
)
GMAIL_API_SCOPE_ERROR = "Gmail API token is missing gmail.send scope. Regenerate token.json with Gmail send permission."
SIGNATURE_CONTENT_ID = "signature_image"
SIGNATURE_IMAGE_HTML = '<img src="cid:signature_image" alt="Signature" style="width:140px; max-width:140px; display:block; margin:8px 0 4px 0;">'

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


class GmailApiNotConfigured(Exception):
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


def is_gmail_api_send_configured(business_profile=None):
    credentials_env_key, token_env_key, credentials_path, token_path, allow_legacy_files = gmail_file_config_for_profile(business_profile)
    errors = ensure_gmail_api_files_from_env(credentials_env_key, token_env_key, credentials_path, token_path)
    return not errors and credentials_path.exists() and token_path.exists()


def html_to_plain_text(html):
    if not html:
        return ""

    text = str(html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def signature_image_path_for_profile(business_profile=None):
    backend_dir = Path(__file__).resolve().parent.parent
    profile_name = (getattr(business_profile, "name", "") or "").strip()

    if profile_name == HOPE_PROFILE_NAME:
        return backend_dir / "Signature 2.png"

    if profile_name == DRIVERS_ED_PROFILE_NAME or not profile_name:
        return backend_dir / "signature.png.png"

    return backend_dir / "signature.png.png"


def ensure_signature_image_reference(html_body):
    html_body = html_body or ""

    if f"cid:{SIGNATURE_CONTENT_ID}" in html_body:
        return html_body

    body_close_match = re.search(r"(?i)</body\s*>", html_body)
    if body_close_match:
        return (
            html_body[:body_close_match.start()]
            + f"\n\n<p>{SIGNATURE_IMAGE_HTML}</p>\n"
            + html_body[body_close_match.start():]
        )

    return f"{html_body}\n\n<p>{SIGNATURE_IMAGE_HTML}</p>"


def attach_inline_signature_image(message, signature_path):
    if not signature_path.exists():
        logger.warning("Signature image file missing: %s", signature_path)
        return

    try:
        with open(signature_path, "rb") as img_file:
            img = MIMEImage(img_file.read())
    except Exception:
        logger.warning("Could not read signature image file: %s", signature_path, exc_info=True)
        return

    img.add_header("Content-ID", f"<{SIGNATURE_CONTENT_ID}>")
    img.add_header("Content-Disposition", "inline")
    img.add_header("X-Attachment-Id", SIGNATURE_CONTENT_ID)
    message.attach(img)


def build_email_message(sender_email, to_email, subject, html_body, plain_text_body=None, business_profile=None):
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    html_body = ensure_signature_image_reference(html_body)
    alternative = MIMEMultipart("alternative")
    fallback_text = plain_text_body or html_to_plain_text(html_body)
    if fallback_text:
        alternative.attach(MIMEText(fallback_text, "plain", "utf-8"))
    alternative.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alternative)

    signature_path = signature_image_path_for_profile(business_profile)
    attach_inline_signature_image(msg, signature_path)

    return msg


def get_gmail_send_service(business_profile=None):
    credentials_env_key, token_env_key, credentials_path, token_path, allow_legacy_files = gmail_file_config_for_profile(business_profile)

    if not is_gmail_api_send_configured(business_profile):
        if business_profile and not allow_legacy_files:
            raise GmailApiNotConfigured(GMAIL_PROFILE_NOT_CONFIGURED_MESSAGE)
        raise GmailApiNotConfigured("Gmail API credentials/token are not configured.")

    deps, error = import_gmail_dependencies()
    if error:
        raise EmailSendError(GMAIL_API_CONFIGURATION_ERROR)

    Credentials = deps["Credentials"]
    InstalledAppFlow = deps["InstalledAppFlow"]
    Request = deps["Request"]
    build = deps["build"]

    try:
        credentials = Credentials.from_authorized_user_file(str(token_path), GMAIL_SEND_SCOPES)
        granted_scopes = set(credentials.granted_scopes or credentials.scopes or [])
        if granted_scopes and GMAIL_SEND_SCOPES[0] not in granted_scopes:
            raise EmailSendError(GMAIL_API_SCOPE_ERROR)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), GMAIL_SEND_SCOPES)
                credentials = flow.run_local_server(port=0)

            token_path.write_text(credentials.to_json(), encoding="utf-8")

        return build("gmail", "v1", credentials=credentials)
    except EmailSendError:
        raise
    except Exception as exc:
        logger.exception("Gmail API send setup failed")
        raise EmailSendError(GMAIL_API_CONFIGURATION_ERROR) from exc


def get_gmail_profile_email(service):
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        logger.exception("Could not read Gmail API profile email")
        return ""


def send_email_with_gmail_api(service, message):
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    try:
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw_message},
        ).execute()
    except Exception as exc:
        logger.exception("Gmail API send failed")
        raise EmailSendError(GMAIL_API_CONFIGURATION_ERROR) from exc

    message_id = result.get("id")
    logger.info("Gmail API email sent successfully message_id=%s", message_id)
    return result


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


def send_email(to_email, subject, body, plain_text_body=None, business_profile=None):
    gmail_address, gmail_password = get_smtp_credentials()

    if is_gmail_api_send_configured(business_profile):
        service = get_gmail_send_service(business_profile)
        sender_email = (getattr(business_profile, "sender_email", "") or "").strip() or gmail_address or get_gmail_profile_email(service)
        if not sender_email:
            raise EmailSendError(GMAIL_API_CONFIGURATION_ERROR)

        msg = build_email_message(
            sender_email,
            to_email,
            subject,
            body,
            plain_text_body=plain_text_body,
            business_profile=business_profile,
        )
        logger.info("Sending email with Gmail API to %s", to_email)
        send_email_with_gmail_api(service, msg)
        return True

    _, _, _, _, allow_legacy_files = gmail_file_config_for_profile(business_profile)
    if business_profile and not allow_legacy_files:
        raise EmailSendError(GMAIL_PROFILE_NOT_CONFIGURED_MESSAGE)

    if not gmail_address or not gmail_password:
        log_smtp_config_status()
        raise EmailSendError(SMTP_CONFIGURATION_ERROR)

    msg = build_email_message(
        gmail_address,
        to_email,
        subject,
        body,
        plain_text_body=plain_text_body,
        business_profile=business_profile,
    )

    try:
        log_smtp_config_status()
        logger.info("Attempting SMTP connection")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.starttls()
            logger.info("SMTP TLS established")

            try:
                server.login(gmail_address, gmail_password)
                logger.info("SMTP login successful")
            except smtplib.SMTPAuthenticationError as exc:
                raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc

            logger.info("Sending email to %s", to_email)
            server.send_message(msg)
            logger.info("Email sent successfully")
    except EmailSendError:
        logger.exception("SMTP send failed")
        raise
    except smtplib.SMTPConnectError as exc:
        logger.exception("SMTP send failed")
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except smtplib.SMTPServerDisconnected as exc:
        logger.exception("SMTP send failed")
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except smtplib.SMTPException as exc:
        logger.exception("SMTP send failed")
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except (TimeoutError, OSError) as exc:
        logger.exception("SMTP send failed")
        raise EmailSendError(SMTP_CONFIGURATION_ERROR) from exc
    except Exception as exc:
        logger.exception("SMTP send failed")
        raise EmailSendError(f"Email send failed: {safe_email_error_message(exc)}") from exc

    return True


log_smtp_config_status()
