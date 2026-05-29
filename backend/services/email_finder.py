import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urljoin, urlparse


EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
TIMEOUT_SECONDS = 8
MAX_PAGES = 24
PLAYWRIGHT_MAX_PAGES = 5
PLAYWRIGHT_TIMEOUT_MS = 12000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

HIGH_VALUE_PATHS = [
    "",
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/team",
    "/staff",
    "/attorneys",
    "/attorney",
    "/lawyers",
    "/lawyer",
    "/our-team",
    "/our-attorneys",
    "/professionals",
    "/locations",
    "/office",
    "/offices",
    "/free-consultation",
    "/consultation",
    "/intake",
]

PRIORITY_KEYWORDS = [
    "contact",
    "attorney",
    "attorneys",
    "lawyer",
    "team",
    "staff",
    "about",
    "location",
    "office",
    "consultation",
    "intake",
    "bio",
    "profile",
]

PREFERRED_PREFIXES = [
    "info",
    "contact",
    "intake",
    "office",
    "admin",
    "support",
    "referrals",
]

JUNK_PREFIXES = [
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
]

BAD_EMAIL_MARKERS = [
    "example.com",
    "w3.org",
]

ASSET_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".css",
    ".js",
    ".ico",
)

THIRD_PARTY_MARKERS = [
    "wordpress",
    "wp-",
    "wp_",
    "theme",
    "themes",
    "plugin",
    "plugins",
]


def normalize_url(url):
    if not url:
        return ""

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def get_domain(url):
    try:
        return urlparse(url).netloc.lower().split(":")[0].replace("www.", "")
    except Exception:
        return ""


def clean_email(email):
    email = unquote(email or "")
    email = re.sub(r"^mailto:", "", email.strip(), flags=re.IGNORECASE)
    email = email.split("?")[0]
    email = email.replace("%20", "")
    email = re.sub(r"\s+", "", email)
    return email.strip(".,;:()[]{}<>\"'")


def decode_obfuscated_text(text):
    if not text:
        return ""

    decoded = unquote(text)
    decoded = decoded.replace("&#64;", "@")
    decoded = decoded.replace("&#x40;", "@")
    decoded = decoded.replace("&commat;", "@")
    decoded = decoded.replace("&#46;", ".")
    decoded = decoded.replace("&#x2e;", ".")

    # Law firm sites often write emails as "name [at] domain [dot] com".
    decoded = re.sub(r"\s*(?:\[|\()\s*at\s*(?:\]|\))\s*", "@", decoded, flags=re.IGNORECASE)
    decoded = re.sub(r"(?<=\w)\s+at\s+(?=\w)", "@", decoded, flags=re.IGNORECASE)
    decoded = re.sub(r"\s*(?:\[|\()\s*dot\s*(?:\]|\))\s*", ".", decoded, flags=re.IGNORECASE)
    decoded = re.sub(r"(?<=\w)\s+dot\s+(?=\w)", ".", decoded, flags=re.IGNORECASE)
    decoded = re.sub(r"\s*@\s*", "@", decoded)

    return decoded


def extract_emails_from_text(text):
    if not text:
        return []

    decoded = decode_obfuscated_text(text)
    emails = []

    for email in re.findall(EMAIL_PATTERN, decoded):
        cleaned = clean_email(email)
        if cleaned:
            emails.append(cleaned)

    return emails


def is_same_domain(base_url, link_url):
    try:
        base_domain = get_domain(base_url)
        link_domain = get_domain(link_url)

        if link_domain == "":
            return True

        return base_domain == link_domain
    except Exception:
        return False


def email_matches_firm_domain(email, firm_domain):
    email_domain = email.split("@")[-1].lower()
    return email_domain == firm_domain or email_domain.endswith("." + firm_domain)


def normalize_page_url(base_url, href):
    if not href:
        return ""

    href = href.strip()
    if href.lower().startswith(("mailto:", "tel:", "sms:", "javascript:", "#")):
        return ""

    page_url = urljoin(base_url, href)
    parsed = urlparse(page_url)

    if parsed.scheme not in ("http", "https"):
        return ""

    path = parsed.path
    if path != "/":
        path = path.rstrip("/")

    return parsed._replace(path=path, query="", fragment="").geturl()


def extract_emails_from_soup(soup):
    emails = set()

    # Raw HTML includes scripts, data attributes, and hidden markup that may hold emails.
    emails.update(extract_emails_from_text(str(soup)))
    emails.update(extract_emails_from_text(soup.get_text(" ")))

    for tag in soup.find_all(True):
        for value in tag.attrs.values():
            if isinstance(value, (list, tuple)):
                value = " ".join(str(item) for item in value)
            emails.update(extract_emails_from_text(str(value)))

    for script in soup.find_all("script"):
        emails.update(extract_emails_from_text(script.get_text(" ")))

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

        if not any(keyword in href_lower or keyword in text_lower for keyword in PRIORITY_KEYWORDS):
            continue

        page_url = normalize_page_url(base_url, href)

        if page_url and is_same_domain(base_url, page_url) and page_url not in seen:
            links.append(page_url)
            seen.add(page_url)

    return links


def scrape_page(session, page_url, base_url):
    try:
        response = session.get(
            page_url,
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return set(), []

        soup = BeautifulSoup(response.text, "html.parser")
        return extract_emails_from_soup(soup), find_priority_links(base_url, soup)
    except Exception:
        return set(), []


def scrape_with_playwright(page_urls, base_url):
    emails = set()

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return emails

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            for page_url in page_urls[:PLAYWRIGHT_MAX_PAGES]:
                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT_MS)
                    page.wait_for_timeout(1000)

                    html = page.content()
                    visible_text = page.locator("body").inner_text(timeout=3000)
                    soup = BeautifulSoup(html, "html.parser")

                    emails.update(extract_emails_from_text(html))
                    emails.update(extract_emails_from_text(visible_text))
                    emails.update(extract_emails_from_soup(soup))

                    if emails:
                        break
                except Exception:
                    continue

            browser.close()
    except Exception:
        return emails

    return emails


def is_valid_email(email, firm_domain):
    lower = email.lower()

    if not re.fullmatch(EMAIL_PATTERN, email):
        return False

    if lower.endswith(ASSET_EXTENSIONS):
        return False

    if any(marker in lower for marker in BAD_EMAIL_MARKERS):
        return False

    same_domain = email_matches_firm_domain(lower, firm_domain)

    if not same_domain and any(marker in lower for marker in THIRD_PARTY_MARKERS):
        return False

    return True


def email_rank(email, firm_domain):
    lower = email.lower()
    local_part = lower.split("@")[0]
    same_domain = email_matches_firm_domain(lower, firm_domain)
    is_junk = any(local_part.startswith(prefix) for prefix in JUNK_PREFIXES)

    try:
        preferred_index = PREFERRED_PREFIXES.index(local_part)
    except ValueError:
        preferred_index = len(PREFERRED_PREFIXES)

    return (
        0 if same_domain else 1,
        1 if is_junk else 0,
        preferred_index,
        lower,
    )


def clean_filter_and_rank_emails(emails, firm_domain):
    unique_emails = {}

    for email in emails:
        cleaned = clean_email(email)
        lower = cleaned.lower()

        if lower and is_valid_email(cleaned, firm_domain):
            unique_emails[lower] = cleaned

    return sorted(unique_emails.values(), key=lambda email: email_rank(email, firm_domain))


def add_page(pages_to_visit, queued_pages, page_url):
    if page_url and page_url not in queued_pages and len(queued_pages) < MAX_PAGES:
        pages_to_visit.append(page_url)
        queued_pages.add(page_url)


def find_email_from_website(url):
    base_url = normalize_url(url)

    if not base_url:
        return []

    firm_domain = get_domain(base_url)
    all_emails = set()
    pages_to_visit = []
    queued_pages = set()
    checked_pages = []

    for path in HIGH_VALUE_PATHS:
        add_page(pages_to_visit, queued_pages, urljoin(base_url, path))

    try:
        session = requests.Session()

        while pages_to_visit and len(checked_pages) < MAX_PAGES:
            page_url = pages_to_visit.pop(0)

            if page_url in checked_pages:
                continue

            checked_pages.append(page_url)
            emails, discovered_links = scrape_page(session, page_url, base_url)
            all_emails.update(emails)

            # Homepage and law-firm pages often link to attorney bios not covered by fixed paths.
            for link in discovered_links:
                add_page(pages_to_visit, queued_pages, link)

        if not all_emails:
            playwright_pages = checked_pages[:PLAYWRIGHT_MAX_PAGES]
            all_emails.update(scrape_with_playwright(playwright_pages, base_url))
    except Exception:
        return []

    return clean_filter_and_rank_emails(all_emails, firm_domain)
