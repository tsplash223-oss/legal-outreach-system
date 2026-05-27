def generate_outreach_email(firm_name, city, practice_area):

    subject = "Professional Introduction - Green Light Drivers Ed & DUI School LLC"

    body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222;">

<p>Dear {firm_name} Team,</p>

<p>
We are reaching out to professional firms in the {city} area to introduce Green Light Drivers Ed & DUI School LLC and the services we provide.
</p>

<p>
Greetings from Green Light Drivers Ed & DUI School LLC, a Bilingual Driving School at 
www.greenlightdrivers.com.
</p>

<p>
We write to introduce our organization and the services we provide as a Georgia DDS-Certified Driving and DUI/Risk reduction School serving teens and adults throughout the State and other States in the United States.
</p>

<p>
This letter does not serve as a Direct Solicitation or engage in any activity that could be interpreted as Direct Soliciting. Our goal is to network with Great professionals like your firm and introduce our professional services to your firm as a Licensed, Successful Driving School with over 200 5-star Google Ratings, offering Driving Education, Defensive Driving/Driver Improvement, DUI/Risk Reduction programs, and Georgia-approved third-party road tests. We are also providing Clinical evaluations/ASAM taught by Certified Instructors at our Location as professional Resources available to you, as needed or required by your clients in Georgia.
</p>

<p><strong>Services We Provide</strong></p>

<ul>
<li>DDS-Approved Defensive Driving Courses (In-Class & Virtual through Zoom)</li>
<li>DUI / Risk Reduction Programs (In-Class & Virtual through Zoom)</li>
<li>Joshua’s Law Driver Education Courses</li>
<li>Behind-The-Wheel Driving Lessons (Cars equipped with Cameras and Instructor driving pedals)</li>
<li>Road Test Preparation</li>
<li>DDS-Approved On-Site Road Testing</li>
<li>English and Spanish Programs</li>
<li>Flexible Scheduling Including Weekends</li>
</ul>

<p><strong>How Our Services May Help Your Clients</strong></p>

<p>
Many drivers require educational or compliance-related services connected to:
</p>

<ul>
<li>License point reduction</li>
<li>Court requirements</li>
<li>Fine reduction eligibility</li>
<li>License reinstatement processes</li>
<li>Driving evaluations</li>
<li>Safe-driving education</li>
</ul>

<p>
Our school focuses on safe driving compliance, driver education, road safety, and professional support for students’ safe driving.
</p>

<p>
Certified instructors conduct all courses, and we offer both virtual and in-person options to help students meet the Department of Driver Services (DDS) and the Court requirements efficiently and professionally.
</p>

<p><strong>Contact Information</strong></p>

<p>
Green Light Drivers Ed & DUI School LLC<br>
6110 McFarland Station Drive, Suite 703<br>
Alpharetta, GA 30004
</p>

<p>
Phone: (770) 685-1600<br>
Email: info@greenlightdrivers.com<br>
Website: https://greenlightdrivers.com
</p>

<p>
Thank you for your time and consideration. We appreciate the opportunity to introduce our school and would be happy to provide additional information or informational materials for your office at any time.
</p>

<p>Sincerely,</p>



<p style="margin-top:5px;">
Manager<br>
<strong>Green Light Drivers Ed & DUI School LLC</strong>
</p>

</body>
</html>
"""

    return {
        "subject": subject,
        "body": body.strip()
    }