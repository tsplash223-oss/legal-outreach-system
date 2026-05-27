import googlemaps
from services.email_finder import find_email_from_website

API_KEY = "AIzaSyCPhbLtBlsQM4MSqjHVgh2WqyNUYwOd-2E"

gmaps = googlemaps.Client(key=API_KEY)


def search_law_firms(keyword, city, state):
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