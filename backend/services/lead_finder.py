import os
from pathlib import Path

import googlemaps

from dotenv import load_dotenv
from services.email_finder import find_email_from_website

BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ROOT_ENV_PATH)
load_dotenv(BACKEND_ENV_PATH, override=True)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def get_google_maps_client():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or GOOGLE_MAPS_API_KEY

    if not api_key:
        return None

    return googlemaps.Client(key=api_key)


def search_law_firms(keyword, city, state):
    gmaps = get_google_maps_client()

    if not gmaps:
        return []

    query = f"{keyword} in {city}, {state}"

    places_result = gmaps.places(query=query)

    firms = []

    for place in places_result.get("results", [])[:10]:
        place_details = gmaps.place(
            place_id=place["place_id"],
            fields=[
                "name",
                "formatted_address",
                "formatted_phone_number",
                "website",
                "rating",
                "business_status",
            ],
        )

        details = place_details.get("result", {})

        website = details.get("website")

        emails = []
        if website:
            emails = find_email_from_website(website)

        firms.append({
            "firm_name": details.get("name"),
            "address": details.get("formatted_address"),
            "phone": details.get("formatted_phone_number"),
            "website": website,
            "email": emails[0] if isinstance(emails, list) and len(emails) > 0 else None,
            "all_emails_found": emails if isinstance(emails, list) else [],
            "rating": details.get("rating"),
            "business_status": details.get("business_status"),
        })

    return firms
