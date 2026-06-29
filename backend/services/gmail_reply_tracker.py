import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, parseaddr
from pathlib import Path

import models
from business_profiles import DRIVERS_ED_PROFILE_NAME, GMAIL_PROFILE_NOT_CONFIGURED_MESSAGE


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BACKEND_DIR = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = BACKEND_DIR / "credentials.json"
TOKEN_PATH = BACKEND_DIR / "token.json"
PROFILE_GMAIL_DIR = BACKEND_DIR / ".gmail_profiles"
GMAIL_CREDENTIALS_ENV = "GMAIL_CREDENTIALS_JSON"
GMAIL_TOKEN_ENV = "GMAIL_TOKEN_JSON"
MAX_MESSAGES = 500
CAMPAIGN_SEARCH_QUERIES = [
    'subject:"Professional Introduction - Green Light Drivers Ed & DUI School LLC"',
    'subject:"Re: Professional Introduction - Green Light Drivers Ed & DUI School LLC"',
    '"Green Light Drivers Ed & DUI School LLC" newer_than:180d',
]
GMAIL_SEARCH_QUERY = " OR ".join(CAMPAIGN_SEARCH_QUERIES)
METADATA_HEADERS = ["From", "To", "Subject", "Date"]


def restore_json_file_from_env(path: Path, env_name: str):
    if path.exists():
        return None

    env_value = os.getenv(env_name, "").strip()
    if not env_value:
        return f"{path.name} is missing and {env_name} is not set."

    try:
        parsed_json = json.loads(env_value)
    except json.JSONDecodeError as exc:
        return f"{env_name} is not valid JSON: {exc}"

    try:
        path.write_text(json.dumps(parsed_json, indent=2), encoding="utf-8")
    except OSError as exc:
        return f"Unable to write {path.name} from {env_name}: {exc}"

    return None


def ensure_gmail_api_files_from_env(credentials_env_key=GMAIL_CREDENTIALS_ENV, token_env_key=GMAIL_TOKEN_ENV, credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH):
    errors = [
        error
        for error in (
            restore_json_file_from_env(credentials_path, credentials_env_key),
            restore_json_file_from_env(token_path, token_env_key),
        )
        if error
    ]

    return errors


def profile_secret_path(profile, suffix: str):
    env_key = (getattr(profile, f"gmail_{suffix}_env_key", "") or f"profile_{profile.id}_{suffix}").lower()
    safe_key = "".join(character if character.isalnum() else "_" for character in env_key)
    PROFILE_GMAIL_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILE_GMAIL_DIR / f"{profile.id}_{safe_key}.json"


def gmail_file_config_for_profile(profile=None):
    if not profile:
        return GMAIL_CREDENTIALS_ENV, GMAIL_TOKEN_ENV, CREDENTIALS_PATH, TOKEN_PATH, True

    credentials_env_key = profile.gmail_credentials_env_key or GMAIL_CREDENTIALS_ENV
    token_env_key = profile.gmail_token_env_key or GMAIL_TOKEN_ENV
    uses_default_files = credentials_env_key == GMAIL_CREDENTIALS_ENV and token_env_key == GMAIL_TOKEN_ENV

    if uses_default_files:
        return credentials_env_key, token_env_key, CREDENTIALS_PATH, TOKEN_PATH, True

    is_drivers_ed_profile = getattr(profile, "name", "") == DRIVERS_ED_PROFILE_NAME
    profile_env_present = bool(os.getenv(credentials_env_key, "").strip()) and bool(os.getenv(token_env_key, "").strip())
    legacy_env_present = bool(os.getenv(GMAIL_CREDENTIALS_ENV, "").strip()) and bool(os.getenv(GMAIL_TOKEN_ENV, "").strip())
    if is_drivers_ed_profile and not profile_env_present and (legacy_env_present or (CREDENTIALS_PATH.exists() and TOKEN_PATH.exists())):
        return GMAIL_CREDENTIALS_ENV, GMAIL_TOKEN_ENV, CREDENTIALS_PATH, TOKEN_PATH, True

    return (
        credentials_env_key,
        token_env_key,
        profile_secret_path(profile, "credentials"),
        profile_secret_path(profile, "token"),
        False,
    )


def gmail_configuration_error(profile=None):
    credentials_env_key, token_env_key, credentials_path, token_path, allow_legacy_files = gmail_file_config_for_profile(profile)
    errors = ensure_gmail_api_files_from_env(credentials_env_key, token_env_key, credentials_path, token_path)

    if errors:
        if profile and not allow_legacy_files:
            return base_error(GMAIL_PROFILE_NOT_CONFIGURED_MESSAGE)

        return base_error(
            (
                "Gmail API reply tracking is not configured. "
                f"Set {credentials_env_key} and {token_env_key} in the backend environment, "
                "or provide backend/credentials.json and backend/token.json for local development. "
                + " ".join(errors)
            )
        )

    if not credentials_path.exists():
        return base_error(
            f"Gmail API credentials are missing. Set {credentials_env_key}."
        )

    if not token_path.exists():
        return base_error(
            f"Gmail API token is missing. Set {token_env_key}."
        )

    return None


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


def get_gmail_service(profile=None):
    configuration_error = gmail_configuration_error(profile)
    if configuration_error:
        return None, configuration_error

    deps, error = import_gmail_dependencies()
    if error:
        return None, error

    Credentials = deps["Credentials"]
    InstalledAppFlow = deps["InstalledAppFlow"]
    Request = deps["Request"]
    build = deps["build"]

    credentials = None
    _, _, credentials_path, token_path, _ = gmail_file_config_for_profile(profile)

    try:
        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
                credentials = flow.run_local_server(port=0)

            token_path.write_text(credentials.to_json(), encoding="utf-8")

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


def check_gmail_replies(db, business_profile=None):
    service, error = get_gmail_service(business_profile)
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

        firm_query = db.query(models.Firm.email, models.Firm).filter(models.Firm.email.isnot(None))
        if business_profile:
            firm_query = firm_query.filter(models.Firm.business_profile_id == business_profile.id)

        firms_by_email = {
            normalize_email(email): firm
            for email, firm in firm_query.all()
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
        contacted_query = db.query(models.Firm).filter(
            models.Firm.status.in_(["Email Sent", "Replied"])
        )
        if business_profile:
            contacted_query = contacted_query.filter(models.Firm.business_profile_id == business_profile.id)
        contacted_count = contacted_query.count()
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
