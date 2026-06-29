from services.gmail_reply_tracker import get_gmail_service

service, error = get_gmail_service()

if error:
    print("ERROR:", error.message if hasattr(error, "message") else error)
else:
    print("SUCCESS: token.json created or refreshed.")