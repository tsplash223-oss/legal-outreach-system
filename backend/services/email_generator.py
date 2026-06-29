from html import escape

from database import SessionLocal
import models


DEFAULT_SUBJECT = "Professional Introduction - Green Light Drivers Ed & DUI School LLC"

SIGNATURE_IMAGE_PLACEHOLDER = "{{signature_image}}"
SIGNATURE_IMAGE_HTML = '<img src="cid:signature_image" alt="Signature" style="width:140px; max-width:140px; display:block; margin:8px 0 4px 0;">'

DEFAULT_BODY_TEXT = """Dear {firm_name},

We are reaching out to professional firms in the {city} area to introduce Green Light Drivers Ed & DUI School LLC and the services we provide.

Greetings from Green Light Drivers Ed & DUI School LLC, a Bilingual Driving School at www.greenlightdrivers.com.

We write to introduce our organization and the services we provide as a Georgia DDS-Certified Driving and DUI/Risk reduction School serving teens and adults throughout the State and other States in the United States.

This letter does not serve as a Direct Solicitation or engage in any activity that could be interpreted as Direct Soliciting. Our goal is to network with Great professionals like your firm and introduce our professional services to your firm as a Licensed, Successful Driving School with over 200 5-star Google Ratings, offering Driving Education, Defensive Driving/Driver Improvement, DUI/Risk Reduction programs, and Georgia-approved third-party road tests. We are also providing Clinical evaluations/ASAM thought by Certified Instructors at our Location as professional Resources available to you, as needed or required by your clients in Georgia.

Services We Provide

• DDS-Approved Defensive Driving Courses (In-Class & Virtual through Zoom)
• DUI / Risk Reduction Programs (In-Class & Virtual through Zoom)
• Joshua’s Law Driver Education Courses
• Behind-The-Wheel Driving Lessons (Cars equipped with Cameras and Instructor driving pedals)
• Road Test Preparation
• DDS-Approved On-Site Road Testing
• English and Spanish Programs
• Flexible Scheduling Including Weekends

How Our Services May Help Your Clients

Many drivers require educational or compliance-related services connected to:

• License point reduction
• Court requirements
• Fine reduction eligibility
• License reinstatement processes
• Driving evaluations
• Safe-driving education

Our school focuses on safe driving compliance, driver education, road safety, and professional support for students’ safe driving.

Certified instructors conduct all courses, and we offer both virtual and in-person options to help students meet the Department of Driver Services (DDS) and the Court requirements efficiently and professionally.

Contact Information

Green Light Drivers Ed & DUI School LLC
6110 McFarland Station Drive, Suite 703
Alpharetta, GA 30004

Phone: (770) 685-1600
Email: info@greenlightdrivers.com
Website: https://greenlightdrivers.com

Thank you for your time and consideration. We appreciate the opportunity to introduce our school and would be happy to provide additional information or informational materials for your office at any time.

Sincerely,

{{signature_image}}

Manager
Green Light Drivers Ed & DUI School LLC"""


def render_template_text(template_text, variables):
    rendered = template_text or ""

    for key, value in variables.items():
        rendered = rendered.replace("{" + key + "}", value or "")

    return rendered


def plain_text_to_html(text):
    paragraphs = []

    for block in (text or "").strip().split("\n\n"):
        lines = [line.rstrip() for line in block.splitlines()]

        if not any(line.strip() for line in lines):
            continue

        escaped_lines = [
            SIGNATURE_IMAGE_HTML if line.strip() == SIGNATURE_IMAGE_PLACEHOLDER else escape(line)
            for line in lines
        ]
        paragraphs.append(f"<p>{'<br>'.join(escaped_lines)}</p>")

    return "\n\n".join(paragraphs)


def wrap_email_html(body_html):
    return f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222;">

{body_html}

</body>
</html>
""".strip()


def is_official_template(body_text):
    required_parts = [
        "Dear {firm_name},",
        "Greetings from Green Light Drivers Ed & DUI School LLC",
        "Services We Provide",
        "How Our Services May Help Your Clients",
        "Contact Information",
        SIGNATURE_IMAGE_PLACEHOLDER,
        "Manager\nGreen Light Drivers Ed & DUI School LLC",
    ]

    return all(part in (body_text or "") for part in required_parts)


def get_active_template(business_profile_id: int | None = None):
    db = SessionLocal()

    try:
        query = db.query(models.EmailTemplate).filter(models.EmailTemplate.is_active.is_(True))
        if business_profile_id:
            query = query.filter(models.EmailTemplate.business_profile_id == business_profile_id)
        else:
            query = query.filter(models.EmailTemplate.business_profile_id.is_(None))

        template = query.first()
        profile = None

        if business_profile_id:
            profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.id == business_profile_id).first()

        if not template:
            if profile:
                return {
                    "subject": profile.default_template_subject or DEFAULT_SUBJECT,
                    "body_text": profile.default_template_body or DEFAULT_BODY_TEXT,
                }

            template = models.EmailTemplate(
                name="Main outreach letter",
                subject=DEFAULT_SUBJECT,
                body_html=DEFAULT_BODY_TEXT,
                business_profile_id=business_profile_id,
                is_active=True
            )
            db.add(template)
            db.commit()
            db.refresh(template)
        elif not is_official_template(template.body_text):
            template.subject = DEFAULT_SUBJECT
            template.body_html = DEFAULT_BODY_TEXT
            db.commit()
            db.refresh(template)

        return {
            "subject": template.subject,
            "body_text": template.body_text,
        }
    finally:
        db.close()


def generate_outreach_email(firm_name, city, practice_area, business_profile=None):
    variables = {
        "firm_name": firm_name or "Your Firm",
        "city": city or "your area",
        "practice_area": practice_area or "your practice area",
    }

    business_profile_id = getattr(business_profile, "id", None)
    template = get_active_template(business_profile_id)
    subject = template["subject"] if template else DEFAULT_SUBJECT
    body_text = template["body_text"] if template else DEFAULT_BODY_TEXT
    body_text = body_text.replace("Dear {firm_name} Team,", "Dear {firm_name},")
    rendered_body_text = render_template_text(body_text, variables)

    return {
        "subject": render_template_text(subject, variables),
        "body": wrap_email_html(plain_text_to_html(rendered_body_text))
    }
