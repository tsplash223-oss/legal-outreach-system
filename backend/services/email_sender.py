import smtplib
import os

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
SIGNATURE_IMAGE_PATH = Path(__file__).resolve().parents[1] / "signature.png.png"


def get_gmail_settings():
    load_dotenv(ENV_PATH, override=True)
    return os.getenv("GMAIL_ADDRESS"), os.getenv("GMAIL_APP_PASSWORD")


def send_email(to_email, subject, body):
    gmail_address, gmail_app_password = get_gmail_settings()

    if not gmail_address or not gmail_app_password:
        return {
            "success": False,
            "error": "Missing Gmail SMTP settings. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in backend/.env."
        }

    msg = MIMEMultipart("related")
    msg["From"] = gmail_address
    msg["To"] = to_email
    msg["Subject"] = subject

    alternative_part = MIMEMultipart("alternative")
    alternative_part.attach(MIMEText(body, "html"))
    msg.attach(alternative_part)

    warning = None
    if SIGNATURE_IMAGE_PATH.exists():
        with open(SIGNATURE_IMAGE_PATH, "rb") as image_file:
            signature_image = MIMEImage(image_file.read())
            signature_image.add_header("Content-ID", "<signature_image>")
            signature_image.add_header("Content-Disposition", "inline", filename=SIGNATURE_IMAGE_PATH.name)
            msg.attach(signature_image)
    else:
        warning = f"Signature image not found at {SIGNATURE_IMAGE_PATH}. Email sent without inline signature image."

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_address, gmail_app_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": "Gmail SMTP authentication failed. Check GMAIL_ADDRESS and the Gmail app password."
        }
    except smtplib.SMTPException as exc:
        return {
            "success": False,
            "error": f"Gmail SMTP error: {exc}"
        }
    except OSError as exc:
        return {
            "success": False,
            "error": f"Could not connect to Gmail SMTP: {exc}"
        }

    return {
        "success": True,
        "message": f"Email sent successfully to {to_email}",
        "warning": warning
    }
