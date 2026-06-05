from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, parseaddr
from pathlib import Path

import models


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BACKEND_DIR = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = BACKEND_DIR / "credentials.json"
TOKEN_PATH = BACKEND_DIR / "token.json"
MAX_MESSAGES = 500
CAMPAIGN_SEARCH_QUERIES = [
    'subject:"Professional Introduction - Green Light Drivers Ed & DUI School LLC"',
    'subject:"Re: Professional Introduction - Green Light Drivers Ed & DUI School LLC"',
    '"Green Light Drivers Ed & DUI School LLC" newer_than:180d',
]
GMAIL_SEARCH_QUERY = " OR ".join(CAMPAIGN_SEARCH_QUERIES)
METADATA_HEADERS = ["From", "To", "Subject", "Date"]


def normalize_email(value):
    if not value:
        return ""

    _, email_address = parseaddr(str(value))
    return email_address.strip().lower()


def parse_sender(value):
    name, email_address = parseaddr(str(value or ""))
    return name.strip(), email_address.strip().lower()


def format_gmail_date(date_header, internal_date):
    parsed_date = None

    if date_header:
        try:
            parsed_date = parsedate_to_datetime(date_header)
        except (TypeError, ValueError):
            parsed_date = None

    if not parsed_date and internal_date:
        try:
            parsed_date = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
        except (TypeError, ValueError):
            parsed_date = None

    if not parsed_date:
        return "", 0

    if parsed_date.tzinfo:
        parsed_date = parsed_date.astimezone()

    return parsed_date.strftime("%Y-%m-%d %I:%M %p"), parsed_date.timestamp()


def base_error(message, configured=False, error=None):
    response = {
        "success": False,
        "configured": configured,
        "checked_messages": 0,
        "gmail_search_query": GMAIL_SEARCH_QUERY,
        "replies_found": 0,
        "updated_firms": 0,
        "reply_rate": "0.0%",
        "replies": [],
        "message": message,
    }

    if error:
        response["error"] = str(error)

    return response


def import_gmail_dependencies():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        return None, base_error(
            (
                "Gmail API packages are missing. Install google-api-python-client, "
                "google-auth-httplib2, and google-auth-oauthlib."
            ),
            error=exc,
        )

    return {
        "Request": Request,
        "Credentials": Credentials,
        "InstalledAppFlow": InstalledAppFlow,
        "build": build,
    }, None


def get_gmail_service():
    if not CREDENTIALS_PATH.exists():
        return None, base_error("Gmail API credentials.json is missing from backend/.")

    deps, error = import_gmail_dependencies()
    if error:
        return None, error

    Credentials = deps["Credentials"]
    InstalledAppFlow = deps["InstalledAppFlow"]
    Request = deps["Request"]
    build = deps["build"]

    credentials = None

    try:
        if TOKEN_PATH.exists():
            credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
                credentials = flow.run_local_server(port=0)

            TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")

        return build("gmail", "v1", credentials=credentials), None
    except Exception as exc:
        return None, base_error(f"Gmail OAuth or API connection failed: {exc}", error=exc)


def get_header(headers, name):
    target = name.lower()

    for header in headers or []:
        if header.get("name", "").lower() == target:
            return header.get("value", "")

    return ""


def build_campaign_search_queries(business_email=None):
    if not business_email:
        return CAMPAIGN_SEARCH_QUERIES

    return [
        f"{query} -from:{business_email}"
        for query in CAMPAIGN_SEARCH_QUERIES
    ]


def format_search_query(queries):
    return " OR ".join(queries)


def search_campaign_messages(service, queries):
    message_refs = []
    seen_message_ids = set()

    for query in queries:
        page_token = None

        while len(message_refs) < MAX_MESSAGES:
            list_request = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=min(100, MAX_MESSAGES - len(message_refs)),
                pageToken=page_token,
            )
            response = list_request.execute()

            for message_ref in response.get("messages", []):
                message_id = message_ref.get("id")

                if not message_id or message_id in seen_message_ids:
                    continue

                seen_message_ids.add(message_id)
                message_refs.append(message_ref)

                if len(message_refs) >= MAX_MESSAGES:
                    break

            page_token = response.get("nextPageToken")

            if not page_token or len(message_refs) >= MAX_MESSAGES:
                break

    return message_refs


def fetch_message_metadata(service, message_id):
    return service.users().messages().get(
        userId="me",
        id=message_id,
        format="metadata",
        metadataHeaders=METADATA_HEADERS,
    ).execute()


def is_inbox_message(message):
    return "INBOX" in set(message.get("labelIds", []))


def is_reply_message(subject, message, sender_email, business_email, firms_by_email):
    subject_text = subject or ""

    return (
        "re:" in subject_text.lower()
        or (is_inbox_message(message) and sender_email != business_email)
        or sender_email in firms_by_email
    )


def check_gmail_replies(db):
    service, error = get_gmail_service()
    if error:
        return error

    try:
        profile = service.users().getProfile(userId="me").execute()
        business_email = normalize_email(profile.get("emailAddress"))
        search_queries = build_campaign_search_queries(business_email)
        gmail_search_query = format_search_query(search_queries)

        messages = search_campaign_messages(service, search_queries)
        checked_messages = 0
        replies_by_firm_id = {}
        updated_firm_count = 0

        firms_by_email = {
            normalize_email(email): firm
            for email, firm in db.query(models.Firm.email, models.Firm).filter(models.Firm.email.isnot(None)).all()
            if normalize_email(email)
        }

        for message_ref in messages:
            message_id = message_ref.get("id")

            if not message_id:
                continue

            try:
                message = fetch_message_metadata(service, message_id)
            except Exception:
                continue

            checked_messages += 1
            headers = message.get("payload", {}).get("headers", [])
            from_header = get_header(headers, "From")
            to_header = get_header(headers, "To")
            subject = get_header(headers, "Subject")
            date_header = get_header(headers, "Date")
            from_name, sender_email = parse_sender(from_header)

            if not sender_email or sender_email == business_email:
                continue

            firm = firms_by_email.get(sender_email)

            if not firm:
                continue

            if not is_reply_message(subject, message, sender_email, business_email, firms_by_email):
                continue

            reply_date, reply_timestamp = format_gmail_date(date_header, message.get("internalDate"))
            existing_reply = replies_by_firm_id.get(firm.id)

            if existing_reply and existing_reply["_timestamp"] >= reply_timestamp:
                continue

            if firm.status != "Replied":
                firm.status = "Replied"
                updated_firm_count += 1

            replies_by_firm_id[firm.id] = {
                "_timestamp": reply_timestamp,
                "firm_id": firm.id,
                "firm_name": firm.firm_name,
                "email": firm.email,
                "from_name": from_name,
                "from_email": sender_email,
                "to": to_header,
                "subject": subject,
                "reply_date": reply_date,
                "snippet": message.get("snippet", ""),
                "status": "Replied",
            }

        if updated_firm_count:
            db.commit()

        replies = [
            {key: value for key, value in reply.items() if key != "_timestamp"}
            for reply in sorted(replies_by_firm_id.values(), key=lambda item: item["_timestamp"], reverse=True)
        ]

        replies_found = len(replies)
        contacted_count = db.query(models.Firm).filter(
            models.Firm.status.in_(["Email Sent", "Replied"])
        ).count()
        reply_rate_value = 0 if contacted_count == 0 else (replies_found / contacted_count) * 100

        return {
            "success": True,
            "configured": True,
            "checked_messages": checked_messages,
            "gmail_search_query": gmail_search_query,
            "replies_found": replies_found,
            "updated_firms": updated_firm_count,
            "reply_rate": f"{reply_rate_value:.1f}%",
            "replies": replies,
            "message": f"Checked {checked_messages} Gmail messages related to the outreach campaign and found {replies_found} matching replies.",
        }
    except Exception as exc:
        db.rollback()
        return base_error(f"Gmail reply check failed: {exc}", configured=True, error=exc)
