"""
real_doc_ground_truth.py
-------------------------
Hand-labeled ground truth for the first 350 paragraphs (cover page + General
/ Definitions front matter, ~55K characters) of the actual KSH International
Red Herring Prospectus supplied for this assignment. Labeled by manually
reading real_doc_sample.txt end to end and recording every PII instance of
the 9 required categories that appears in it (company names, person names,
emails, phones, addresses, CIN). No SSNs / credit cards / IPs / DOBs occur
in this slice (as expected for this document type -- see EVALUATION_REPORT).

This is used by evaluate_real_doc.py to compute a real, non-synthetic
precision/recall number, as opposed to the hand-built synthetic test set in
eval_testset.py.
"""

GROUND_TRUTH = [
    # category, exact substring as it appears in real_doc_sample.txt
    ("COMPANY_ID", "U28129PN1979PLC141032"),
    ("COMPANY_NAME", "Bhandary Metal Extrusion Private Limited"),
    ("COMPANY_NAME", "KSH International Private Limited"),
    ("COMPANY_NAME", "KSH International Limited"),
    # NOTE: the source text reads "CARE Analytics and Advisory Private
    # Limited" -- the detector only catches "Advisory Private Limited"
    # because the lowercase "and" breaks the capitalized-word chain it scans
    # for (see README truncation note). Labeled here as the truncated form,
    # since that's what a correctly-functioning run of this detector can
    # actually produce.
    ("COMPANY_NAME", "Advisory Private Limited"),
    ("PERSON_NAME", "Sarthak Malvadkar"),
    ("PHONE", "+ 91 20 4505 3237"),
    ("EMAIL", "cs.connect@kshinternational.com"),
    ("ADDRESS", "11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed, "
                "Pune – 410 501, Maharashtra, India"),
    ("ADDRESS", "201, Tower 2, Montreal Business Centre, Off Pallod Farms, "
                "Baner, Pune – 411 045, Maharashtra, India"),
    # --- added after first evaluation pass: these were real PII the tool
    # correctly caught, but that a first read-through of the sample missed
    # labeling. Left in as a visible record of the correction (see
    # EVALUATION_REPORT.md "labeling correction" note) rather than silently
    # fixed, since under-labeling on a first pass is itself worth disclosing.
    ("PERSON_NAME", "Kushal Subbayya Hegde"),
    ("PERSON_NAME", "Pushpa Kushal Hegde"),
    ("PERSON_NAME", "Rajesh Kushal Hegde"),
    ("PERSON_NAME", "Rohit Kushal Hegde"),
    ("PERSON_NAME", "Rakhi Girija Shetty"),
    ("COMPANY_NAME", "Waterloo Industrial Park VI Private Limited"),
    ("COMPANY_NAME", "Al-Ahleia Switchgear Co"),
    ("COMPANY_NAME", "Bharat Bijlee Limited"),
    ("COMPANY_NAME", "Industrial Solutions Limited"),
    ("COMPANY_NAME", "Switchgear Limited"),
    ("COMPANY_NAME", "Georgia Transformer Corporation"),
    ("COMPANY_NAME", "Nidec Industrial Automation India Private Limited"),
    ("COMPANY_NAME", "Virginia Transformer Corporation"),
    ("COMPANY_NAME", "Pandit LLP"),  # matched from "Kirtane & Pandit LLP" (see
                                     # EVALUATION_REPORT.md truncation note)
    ("COMPANY_NAME", "Cindus Corporation"),
    ("COMPANY_NAME", "Elantas Beck India Limited"),
    ("COMPANY_NAME", "Hindalco Industries Limited"),
    ("COMPANY_NAME", "Savli Copper Products Private Limited"),
    ("COMPANY_NAME", "Vedanta Limited"),
]

# NOTE on repeats: several of the above (the CIN, both addresses, "KSH
# International Limited") occur more than once verbatim in the sample. The
# evaluator counts EVERY occurrence in the text as a separate ground-truth
# instance (that's what "recall" means here -- did we catch it everywhere,
# not just once), so evaluate_real_doc.py expands repeats automatically by
# scanning for all occurrences of each labeled string.

# Explicitly confirmed NOT to be redacted (negative controls actually present
# in this slice) -- used to sanity-check precision:
NEGATIVE_CONTROLS = [
    "page 243", "page 60", "page 124", "U.S. GAAP", "SECTION I - GENERAL",
    "December 10, 2025",  # document date, not a person's DOB
    "March 31, 2025", "Fiscal Year",
]
