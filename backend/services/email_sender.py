import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_email(to_email, subject, body):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise Exception("Missing Gmail SMTP settings")

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
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

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    return True