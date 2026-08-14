"""
eval_testset.py
----------------
A small hand-labeled synthetic test set used to compute precision/recall/
accuracy for the redactor. The real KSH Red Herring Prospectus is used for
the end-to-end deliverable, but it does not naturally contain SSNs, credit
card numbers, IP addresses, or dates of birth -- so those categories cannot
be evaluated on it. This synthetic "support ticket log" style test set gives
labeled ground truth for all 9 required PII categories plus a few
adversarial "should NOT be redacted" lines (order numbers, ticket IDs) to
measure precision / false positives, per the assignment's evaluation
criteria.
"""

# Each tuple: (raw_text_line, [(category, exact_substring), ...] ground truth)
LABELED_LINES = [
    ("Hi, this is Rashi Patil writing in about my order.",
     [("PERSON_NAME", "Rashi Patil")]),
    ("You can reach me at rashi.patil@gmail.com or call +91 9876543210.",
     [("EMAIL", "rashi.patil@gmail.com"), ("PHONE", "+91 9876543210")]),
    ("Please escalate this to Rohan Dey, rohan.dey@gmail.com, phone +91 9123456780.",
     [("PERSON_NAME", "Rohan Dey"), ("EMAIL", "rohan.dey@gmail.com"),
      ("PHONE", "+91 9123456780")]),
    ("I work at Initech Private Limited and my manager is Vikram Mehta.",
     [("COMPANY_NAME", "Initech Private Limited"), ("PERSON_NAME", "Vikram Mehta")]),
    ("My mailing address is 221B Baker Street, 400001, Maharashtra, India.",
     [("ADDRESS", "221B Baker Street, 400001, Maharashtra, India")]),
    ("For verification, my SSN is 123-45-6789.",
     [("SSN", "123-45-6789")]),
    ("The refund was declined on card 4111 1111 1111 1111.",
     [("CREDIT_CARD", "4111 1111 1111 1111")]),
    ("Date of birth: 04/12/1990, as per my ID.",
     [("DATE_OF_BIRTH", "04/12/1990")]),
    ("The error log shows requests originating from 192.168.1.42 repeatedly.",
     [("IP_ADDRESS", "192.168.1.42")]),
    ("Order #ORD-58291 was placed on 2024-01-05 and Ticket #4471 is still open.",
     []),  # negative control: order/ticket numbers should NOT be redacted
    ("Total amount due is 4500 and the invoice number is 88213.",
     []),  # negative control: plain numbers should NOT be redacted
]


def flatten_ground_truth():
    """Return list of (line_idx, category, text) for every labeled entity."""
    out = []
    for i, (_, ents) in enumerate(LABELED_LINES):
        for cat, txt in ents:
            out.append((i, cat, txt))
    return out
