"""Generate the fictional Acme Services Ltd policy PDFs in docs/.

    pip install reportlab
    python -m scripts.make_sample_docs

Everything in these documents is invented for demonstration. The generated PDFs are committed
so the project works without reportlab; run this script only to change the documents.
"""

from pathlib import Path

from reportlab import rl_config
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

rl_config.invariant = 1  # byte-for-byte reproducible PDFs (no timestamps / random IDs)

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"

DOCUMENTS = {
    "HR_Policy.pdf": {
        "title": "Human Resources Policy",
        "meta": "Version 3.2  |  Effective 1 January 2026  |  Owner: Head of People",
        "sections": [
            ("1. Purpose and Scope", [
                "This policy sets out the terms and expectations that apply to everyone who works for Acme Services Ltd. "
                "It applies to permanent employees, fixed-term contractors and interns unless a contract states otherwise. "
                "Questions about this policy should be sent to the People team at people@acme.example.",
            ]),
            ("2. Working Hours", [
                "Standard working hours are 40 hours per week, Monday to Friday, from 08:00 to 17:00 with a one-hour unpaid lunch break. "
                "With line manager approval, staff may start between 07:00 and 10:00 and finish accordingly, provided they complete a full working day.",
                "Employees in eligible roles may work remotely for up to two days per week. Remote working days must be recorded in the team calendar.",
            ]),
            ("3. Probation", [
                "Every new permanent employee serves a probation period of three months. A review meeting is held at the end of the second month, "
                "and a confirmation decision is made before the end of the third month.",
                "Probation may be extended once, by up to three months, if performance targets have not yet been met. "
                "During probation, either the employee or the company may end the employment by giving seven days' written notice.",
            ]),
            ("4. Notice Period", [
                "After confirmation, an employee who wishes to resign must give 30 days' written notice. "
                "Employees in senior management roles must give 60 days' notice.",
                "The company will give the same notice period when it ends employment for reasons other than gross misconduct. "
                "Notice may be paid in lieu at the company's discretion.",
            ]),
            ("5. Code of Conduct", [
                "All staff are expected to act honestly, treat colleagues and customers with respect, and protect company information. "
                "Any conflict of interest must be declared in writing to the People team within five working days of the employee becoming aware of it.",
                "Gifts or hospitality worth more than KES 5,000 received from a customer or supplier must also be declared. "
                "Harassment and discrimination of any kind are not tolerated. Concerns can be reported to the People team or confidentially to ethics@acme.example.",
            ]),
            ("6. Performance Reviews", [
                "Performance is reviewed formally once a year in January, with an informal mid-year check-in in July. "
                "Employees are rated on a scale of 1 to 5, where 3 means meets expectations.",
                "A rating below 2 triggers a 90-day performance improvement plan agreed between the employee, the line manager and the People team. "
                "Two consecutive ratings below 2 may lead to the disciplinary process.",
            ]),
            ("7. Disciplinary Process", [
                "The disciplinary process has four stages: a verbal warning, a written warning, a final written warning and dismissal. "
                "Serious misconduct may lead directly to dismissal.",
                "Employees must receive at least three working days' notice of a disciplinary hearing and may be accompanied by a colleague. "
                "Decisions are confirmed in writing within five working days of the hearing.",
            ]),
            ("8. Expenses", [
                "Reasonable business expenses are reimbursed when they are approved by the line manager and supported by receipts. "
                "Expense claims must be submitted within 30 days of the expense being incurred. Claims submitted later than 30 days may be rejected.",
                "Purchases of goods and services for the company must follow the Procurement Policy and cannot be claimed as personal expenses.",
            ]),
        ],
    },
    "Leave_Policy.pdf": {
        "title": "Leave Policy",
        "meta": "Version 2.4  |  Effective 1 January 2026  |  Owner: Head of People",
        "sections": [
            ("1. Purpose", [
                "This policy explains the leave that employees of Acme Services Ltd are entitled to and how to request it. "
                "The leave year runs from 1 January to 31 December. All leave requests are made through the HR portal.",
            ]),
            ("2. Annual Leave", [
                "Full-time employees are entitled to 21 working days of paid annual leave per leave year. Leave accrues at 1.75 days per month.",
                "Requests are approved by the line manager, who should respond within three working days. "
                "Leave of more than 10 consecutive working days requires at least four weeks' notice. "
                "New employees may take annual leave during probation only with their line manager's approval.",
            ]),
            ("3. Carrying Leave Forward", [
                "Employees may carry forward a maximum of five unused annual leave days into the next leave year. "
                "Carried-forward days must be used by 31 March, after which they are forfeited.",
                "Unused leave above the five-day limit is not paid out, except when employment ends.",
            ]),
            ("4. Sick Leave", [
                "Employees are entitled to 14 days of sick leave on full pay in each leave year, followed by up to 14 days on half pay. "
                "Employees must notify their line manager before 09:00 on the first day of absence.",
                "A medical certificate is required for any absence of more than two consecutive days. Sick leave cannot be carried forward.",
            ]),
            ("5. Maternity Leave", [
                "Female employees are entitled to three months of maternity leave on full pay. "
                "Employees should notify the People team at least four weeks before the intended start date, where possible, "
                "and provide a medical certificate confirming the expected due date. Annual leave continues to accrue during maternity leave.",
            ]),
            ("6. Paternity Leave", [
                "Male employees are entitled to two weeks of paternity leave on full pay. "
                "Paternity leave must be taken within three months of the birth or adoption of the child. "
                "Employees should give at least two weeks' notice where possible.",
            ]),
            ("7. Compassionate Leave", [
                "Up to five working days of paid compassionate leave may be taken on the death of a spouse, child, parent or sibling. "
                "Up to two working days may be taken for the death of other close relatives.",
                "Additional time may be taken as annual leave or unpaid leave.",
            ]),
            ("8. Study Leave", [
                "After 12 months of service, employees may take up to 10 days of paid study leave per year to sit approved professional or academic examinations. "
                "Evidence of registration for the examination must be submitted with the request.",
            ]),
            ("9. Unpaid Leave and Public Holidays", [
                "Unpaid leave of up to 30 days may be granted at the discretion of the department head and requires approval from the Head of People.",
                "Acme Services Ltd observes all Kenyan public holidays. A public holiday that falls on a Sunday is observed on the following Monday.",
            ]),
        ],
    },
    "IT_Support_Guide.pdf": {
        "title": "IT Support Guide",
        "meta": "Version 5.1  |  Effective 1 March 2026  |  Owner: IT Service Desk",
        "sections": [
            ("1. Getting Help", [
                "The IT Service Desk is available Monday to Friday from 07:30 to 18:00. "
                "Raise a ticket through the service portal, email it-help@acme.example, or call extension 4100. "
                "For a critical outage affecting many users, always call extension 4100 rather than emailing.",
            ]),
            ("2. Priority Levels and Response Times", [
                "Every ticket is given a priority that sets how quickly it is handled.",
                "P1 Critical means a system is down for all users. The Service Desk responds within 15 minutes and aims to resolve the issue within 4 hours.",
                "P2 High means a major function is unavailable for a team. Response is within 1 hour and resolution within 8 hours.",
                "P3 Normal means an issue affecting one user, usually with a workaround. Response is within 4 hours and resolution within 3 working days.",
                "P4 Low means a request or minor issue. Response is within 1 working day and resolution within 10 working days.",
            ]),
            ("3. Password Policy", [
                "Passwords must be at least 14 characters long and must be changed every 90 days. The last 10 passwords cannot be reused. "
                "An account is locked after five failed sign-in attempts.",
                "Locked accounts can be unlocked through the self-service portal, or by the Service Desk after your identity has been verified. "
                "Never share your password with anyone, including IT staff.",
            ]),
            ("4. Multi-Factor Authentication", [
                "Multi-factor authentication (MFA) is mandatory for email, the VPN and the HR portal. Use the company-approved authenticator app on your phone.",
                "If you lose your phone or it is stolen, contact the Service Desk immediately. "
                "A temporary bypass code, valid for 24 hours, can be issued once your identity is confirmed.",
            ]),
            ("5. VPN and Remote Access", [
                "Staff working remotely must connect to the company VPN before using internal systems such as the file server or the finance application. "
                "The VPN client may only be installed on company-managed devices. Personal devices may access web email only.",
            ]),
            ("6. Laptops and Equipment", [
                "New equipment is requested by the line manager through the service portal. Standard-issue laptops are replaced every three years.",
                "If a company device is lost or stolen, report it to the Service Desk and to security@acme.example within two hours so that it can be remotely locked and wiped. "
                "Lost devices must also be reported to the police and the report number supplied to IT.",
            ]),
            ("7. Software Installation", [
                "Only software from the approved Software Catalogue may be installed. "
                "Requests for other software must be approved by IT Security, who will assess licensing and security risks. "
                "Unlicensed or pirated software is strictly prohibited.",
            ]),
            ("8. Backups and File Recovery", [
                "Files saved on network drives and in the company cloud storage are backed up every night. Files saved only on a laptop are not backed up. "
                "Deleted files can be restored for up to 30 days after deletion by raising a P3 ticket.",
            ]),
            ("9. Reporting Phishing", [
                "Do not click links or open attachments in suspicious emails. Forward the email as an attachment to security@acme.example and then delete it.",
                "If you have already clicked a link or entered your password, change your password and call the Service Desk on extension 4100 immediately.",
            ]),
        ],
    },
    "Procurement_Policy.pdf": {
        "title": "Procurement Policy",
        "meta": "Version 4.0  |  Effective 1 February 2026  |  Owner: Finance Director",
        "sections": [
            ("1. Purpose and Scope", [
                "This policy ensures that Acme Services Ltd buys goods and services fairly, transparently and at good value. "
                "It applies to all purchases made on behalf of the company, regardless of the budget they are paid from.",
            ]),
            ("2. Approval Thresholds", [
                "Purchases below KES 50,000 must be approved by the requester's line manager. "
                "Purchases from KES 50,000 up to and including KES 500,000 must be approved by the department head and Finance.",
                "Purchases above KES 500,000 and up to KES 5,000,000 must be approved by the Finance Director. "
                "Purchases above KES 5,000,000 must be approved by the Managing Director. "
                "Purchases must never be split into smaller orders to avoid a threshold.",
            ]),
            ("3. Quotations and Tenders", [
                "For purchases below KES 50,000, one written quotation is sufficient. "
                "For purchases from KES 50,000 to KES 500,000, at least three written quotations must be obtained.",
                "Purchases above KES 500,000 require a formal tender, with invitations sent to at least five suppliers "
                "and bids evaluated by a panel of at least three people.",
            ]),
            ("4. Approved Suppliers", [
                "Goods and services may only be bought from suppliers on the Approved Supplier List. "
                "To be registered, a supplier must provide a valid business registration certificate, a current tax compliance certificate and verified bank details.",
                "The list is reviewed every year, and suppliers with repeated performance problems may be removed.",
            ]),
            ("5. Purchase Orders", [
                "No purchase may be made without a purchase order (PO) issued by the Procurement team. "
                "Procurement issues a PO within two working days of receiving an approved requisition. "
                "Invoices that do not quote a valid PO number will not be paid.",
            ]),
            ("6. Payment Terms", [
                "Suppliers are paid within 30 days of the company receiving both a valid invoice and the goods or services. "
                "Payments are made in two payment runs each month: on the 15th and on the last working day of the month.",
            ]),
            ("7. Conflicts of Interest", [
                "Employees must declare in writing any personal or financial relationship with a supplier or bidder before taking part in a purchasing decision. "
                "An employee with a declared conflict must not evaluate bids or approve payments for that supplier.",
            ]),
            ("8. Emergency Purchases", [
                "In an emergency, such as a safety risk or an outage of a critical service, a department head may approve a purchase without quotations.",
                "A retrospective purchase order must be raised within three working days, and all emergency purchases are reported to the Finance Director each month.",
            ]),
        ],
    },
}


def build_pdf(path: Path, title: str, meta: str, sections: list[tuple[str, list[str]]]) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=20, leading=24, spaceAfter=4)
    meta_style = ParagraphStyle("DocMeta", parent=styles["Normal"], fontSize=9, textColor="#555555", alignment=1, spaceAfter=10)
    heading = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=6)

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(2 * cm, 1.2 * cm, f"Acme Services Ltd  |  {title}  |  Fictional sample document for demonstration")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    story = [Paragraph(title, title_style), Paragraph(meta, meta_style)]
    for heading_text, paragraphs in sections:
        story.append(Paragraph(heading_text, heading))
        story.extend(Paragraph(text, body) for text in paragraphs)
        story.append(Spacer(1, 2))

    SimpleDocTemplate(
        str(path), pagesize=A4, title=f"Acme Services Ltd - {title}", author="Acme Services Ltd (fictional)",
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2.2 * cm,
    ).build(story, onFirstPage=footer, onLaterPages=footer)


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    for filename, spec in DOCUMENTS.items():
        build_pdf(DOCS_DIR / filename, spec["title"], spec["meta"], spec["sections"])
        print("wrote", DOCS_DIR / filename)


if __name__ == "__main__":
    main()
