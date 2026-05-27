import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urljoin, urlparse


EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
TIMEOUT_SECONDS = 8
MAX_PAGES = 12

REQUIRED_PATHS = [
    "",
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/team",
    "/attorneys",
    "/lawyers",
    "/locations",
]

PRIORITY_KEYWORDS = [
    "contact",
    "contact-us",
    "contactus",
    "about",
    "about-us",
    "team",
    "attorney",
    "attorneys",
    "lawyer",
    "lawyers",
    "location",
    "locations",
]


def normalize_url(url):
    if not url:
        return ""

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def clean_email(email):
    email = unquote(email or "")
    email = re.sub(r"^mailto:", "", email.strip(), flags=re.IGNORECASE)
    email = email.split("?")[0]
    email = email.replace("%20", "")
    email = email.replace(" ", "")
    return email.strip(".,;:()[]{}<>\"'")


def extract_emails_from_text(text):
    if not text:
        return []

    emails = []

    for email in re.findall(EMAIL_PATTERN, text):
        cleaned = clean_email(email)
        if cleaned:
            emails.append(cleaned)

    return emails


def is_same_domain(base_url, link_url):
    try:
        base_domain = urlparse(base_url).netloc.lower().replace("www.", "")
        link_domain = urlparse(link_url).netloc.lower().replace("www.", "")

        if link_domain == "":
            return True

        return base_domain == link_domain
    except Exception:
        return False


def extract_emails_from_soup(soup):
    emails = set()

    emails.update(extract_emails_from_text(str(soup)))
    emails.update(extract_emails_from_text(soup.get_text(" ")))

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if href.lower().startswith("mailto:"):
            emails.add(clean_email(href))

    footer = soup.find("footer")
    if footer:
        emails.update(extract_emails_from_text(str(footer)))
        emails.update(extract_emails_from_text(footer.get_text(" ")))

        for link in footer.find_all("a", href=True):
            href = link["href"]

            if href.lower().startswith("mailto:"):
                emails.add(clean_email(href))

    return emails


def find_priority_links(base_url, soup):
    links = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        href_lower = href.lower()
        text_lower = link.get_text(" ", strip=True).lower()

        if href_lower.startswith("mailto:"):
            continue

        if not any(keyword in href_lower or keyword in text_lower for keyword in PRIORITY_KEYWORDS):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        page_url = parsed._replace(query="", fragment="").geturl()

        if is_same_domain(base_url, page_url) and page_url not in seen:
            links.append(page_url)
            seen.add(page_url)

    return links


def scrape_page(page_url, base_url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(
            page_url,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return set(), []

        soup = BeautifulSoup(response.text, "html.parser")
        return extract_emails_from_soup(soup), find_priority_links(base_url, soup)
    except Exception:
        return set(), []


def find_email_from_website(url):
    base_url = normalize_url(url)

    if not base_url:
        return []

    all_emails = set()
    pages_to_visit = []
    queued_pages = set()
    checked_pages = set()

    for path in REQUIRED_PATHS:
        page_url = urljoin(base_url, path)

        if page_url not in queued_pages:
            pages_to_visit.append(page_url)
            queued_pages.add(page_url)

    while pages_to_visit and len(checked_pages) < MAX_PAGES:
        page_url = pages_to_visit.pop(0)

        if page_url in checked_pages:
            continue

        checked_pages.add(page_url)

        emails, discovered_links = scrape_page(page_url, base_url)
        all_emails.update(emails)

        for link in discovered_links:
            if len(queued_pages) >= MAX_PAGES:
                break

            if link not in queued_pages and link not in checked_pages:
                pages_to_visit.append(link)
                queued_pages.add(link)

    filtered_emails = []
    seen_emails = set()

    for email in sorted(all_emails, key=str.lower):
        cleaned = clean_email(email)
        lower = cleaned.lower()

        if not re.fullmatch(EMAIL_PATTERN, cleaned):
            continue

        if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".css", ".js")):
            continue

        if "example.com" in lower:
            continue

        if lower not in seen_emails:
            filtered_emails.append(cleaned)
            seen_emails.add(lower)

    return filtered_emails
