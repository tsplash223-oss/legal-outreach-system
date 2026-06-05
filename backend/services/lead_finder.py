import os
import logging
from pathlib import Path

import googlemaps

from dotenv import load_dotenv
from services.email_finder import find_email_from_website

logger = logging.getLogger(__name__)

BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ROOT_ENV_PATH)
load_dotenv(BACKEND_ENV_PATH, override=True)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("API_KEY")


class GoogleMapsConfigurationError(Exception):
    pass


class GoogleMapsSearchError(Exception):
    pass


def get_google_maps_api_key():
    return os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("API_KEY") or GOOGLE_MAPS_API_KEY


def get_google_maps_client():
    api_key = get_google_maps_api_key()

    if not api_key:
        raise GoogleMapsConfigurationError(
            "Google Maps is not configured. Set GOOGLE_MAPS_API_KEY or API_KEY in backend/.env."
        )

    return googlemaps.Client(key=api_key)


def search_law_firms(keyword, city, state):
    api_key = get_google_maps_api_key()
    logger.info("Google Maps API key loaded: %s", bool(api_key))
    logger.info("Searching Google Places: keyword=%s city=%s state=%s", keyword, city, state)

    gmaps = get_google_maps_client()

    query = f"{keyword} in {city}, {state}"

    try:
        places_result = gmaps.places(query=query)
    except googlemaps.exceptions.ApiError as exc:
        logger.exception("Google Places API error for keyword=%s city=%s state=%s", keyword, city, state)
        raise GoogleMapsSearchError(f"Google Places API error: {exc}") from exc
    except googlemaps.exceptions.Timeout as exc:
        logger.exception("Google Places request timed out for keyword=%s city=%s state=%s", keyword, city, state)
        raise GoogleMapsSearchError("Google Places request timed out.") from exc
    except googlemaps.exceptions.TransportError as exc:
        logger.exception("Google Places transport error for keyword=%s city=%s state=%s", keyword, city, state)
        raise GoogleMapsSearchError(f"Google Places request failed: {exc}") from exc

    places = places_result.get("results", [])
    logger.info("Google Places results found: %s", len(places))

    firms = []

    for place in places[:10]:
        try:
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
        except googlemaps.exceptions.ApiError as exc:
            logger.exception("Google Place Details API error for keyword=%s city=%s state=%s", keyword, city, state)
            raise GoogleMapsSearchError(f"Google Place Details API error: {exc}") from exc
        except googlemaps.exceptions.Timeout as exc:
            logger.exception("Google Place Details request timed out for keyword=%s city=%s state=%s", keyword, city, state)
            raise GoogleMapsSearchError("Google Place Details request timed out.") from exc
        except googlemaps.exceptions.TransportError as exc:
            logger.exception("Google Place Details transport error for keyword=%s city=%s state=%s", keyword, city, state)
            raise GoogleMapsSearchError(f"Google Place Details request failed: {exc}") from exc

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

    logger.info("Firms returned from lead finder: %s", len(firms))

    return firms
