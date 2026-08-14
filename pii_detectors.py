"""
pii_detectors.py
-----------------
Regex + heuristic detectors for PII redaction.

Design principle: every detector returns a list of (start, end, category, matched_text)
spans found in a block of text. Detectors are independent and are combined + de-duplicated
(longest-match-wins on overlap) by the caller (redactor.py).

Adding a new PII type = write one function that returns spans, then register it in
DETECTORS at the bottom of this file. Nothing else needs to change.
"""

import re

# ---------------------------------------------------------------------------
# 1. STRUCTURED / HIGH-PRECISION PATTERNS (emails, phones, ids, ips, cards)
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Indian-style (+91 xx xxxx xxxx / +91-xxxxxxxxxx) and generic international numbers.
PHONE_RE = re.compile(
    r"(?<![\d/])(?:\+?\d{1,3}[\s\-\.]?)?(?:\(?\d{2,4}\)?[\s\-\.]?){2,4}\d{3,4}(?![\d/])"
)

IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# 13-19 digit sequences, optionally grouped by spaces/dashes (typical card layout).
CARD_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")

DOB_KEYWORD_RE = re.compile(
    r"\b(?:DOB|Date of Birth|D\.O\.B\.?|born on|born)\b[:\-]?\s*"
    r"(\d{4}[/\-\.](?:0?\d|1[0-2])[/\-\.][0-3]?\d|"  # YYYY-MM-DD
    r"[0-3]?\d[/\-\.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[/\-\.]\d{2,4}|" # DD-MMM-YYYY
    r"[0-3]?\d[/\-\.](?:0?\d|1[0-2])[/\-\.]\d{2,4}|" # DD-MM-YYYY
    r"(?:0?\d|1[0-2])[/\-\.][0-3]?\d[/\-\.]\d{2,4}|" # MM-DD-YYYY
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

# Indian PIN-code + state anchor. Matched narrowly (digits/state/optional "India")
# then expanded backward in find_addresses() to the nearest sentence/line boundary,
# which is far more robust than trying to whitelist every punctuation character
# (em/en-dashes, curly quotes, etc.) that can appear in a Word document's address.
PIN_STATE_RE = re.compile(
    r"\d{3}\s?-?\s?\d{3}\b,?\s*"
    r"(?:Maharashtra|Delhi|Karnataka|Tamil Nadu|Gujarat|West Bengal|Telangana|"
    r"Uttar Pradesh|Rajasthan|Punjab|Kerala|Haryana|Madhya Pradesh)\b"
    r"(?:,?\s*India)?",
    re.IGNORECASE,
)

_ADDR_BOUNDARY_RE = re.compile(r"[\n]|[:;]\s*|\.\s+(?=[A-Z0-9])")

CIN_RE = re.compile(r"\bU\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")  # Corporate Identity Number

# ---------------------------------------------------------------------------
# 2. NAME DETECTION (heuristic, dictionary + role-anchored)
# ---------------------------------------------------------------------------
# Real NER (spaCy) is not available in this offline environment, so names are
# detected with two complementary heuristics:
#   (a) role-anchored: "<role keyword> ... being <Name>" / "Contact Person: <Name>"
#   (b) gazetteer: names explicitly harvested once via (a) are also redacted
#       everywhere else they appear verbatim in the document.
# See README for the precision/recall trade-offs of this approach.

ROLE_KEYWORDS = [
    "Contact Person", "Chairman and Executive Director", "Chief Executive Officer",
    "Chief Financial Officer", "Company Secretary", "Managing Director",
    "Joint Managing Director", "Whole-time Director", "Independent Chartered Engineer",
]

NAME_TOKEN = r"[A-Z][a-zA-Z'\.\-]+"
NAME_SEQ = rf"{NAME_TOKEN}(?:[ \t]+{NAME_TOKEN}){{1,3}}"

ROLE_ANCHORED_NAME_RE = re.compile(
    r"(?:" + "|".join(re.escape(k) for k in ROLE_KEYWORDS) + r")"
    r"(?:\*\*)?\s*[:,]?\s*(?:being[,]?\s*)?\**\s*(" + NAME_SEQ + r")",
)

CONTACT_PERSON_RE = re.compile(
    r"Contact\s*Person\*{0,2}:?\**\s*(" + NAME_SEQ + r"(?:\s*/\s*" + NAME_SEQ + r")?)"
)

# Comma/"and"-separated name lists that follow a defined-term label, e.g.:
#   "Promoter Selling Shareholders | Kushal Subbayya Hegde, Pushpa Kushal Hegde,
#    Rajesh Kushal Hegde and Rohit Kushal Hegde"
# This is how prospectuses/RHPs typically enumerate multiple named individuals
# in one place (the glossary), so anchoring here recovers names that never get
# a role-keyword next to them anywhere else in the document.
LIST_LABELS = ["Promoter Selling Shareholders", "Promoters", "Parents Branch",
               "Rajesh Branch", "Rakhi Branch", "Rohit Branch", "Sangeeta Branch"]
NAME_LIST_RE = re.compile(
    r"(?:" + "|".join(re.escape(k) for k in LIST_LABELS) + r")\**\s*[:|]?\s*"
    r"([^\.\n]{1,400})"
)
# A trailing entity-type word tells us where the person-name list ends and
# company/trust names begin (those are handled by find_companies instead).
LIST_STOP_WORDS = {"Family", "Trust", "Private", "Limited", "LLP", "His", "Her",
                    "Promoter", "Promoters", "Selling", "Shareholders", "Group",
                    "Branch", "Company", "Companies"}

# Common legal/financial boilerplate phrases in Title Case that look like names
# but are not — used to suppress false positives from the generic scan.
LEGAL_STOPWORDS = {
    "Book Running Lead Managers", "Red Herring Prospectus", "Registrar of Companies",
    "Companies Act", "Equity Shares", "Offer Price", "Price Band", "Stock Exchanges",
    "Registered Office", "Corporate Office", "Bid Cum Application Form",
    "Designated Stock Exchange", "Anchor Investor", "Book Building Process",
    "Senior Management", "Key Managerial Personnel", "Key Management Personnel",
    "Sponsor Banks", "Offer Agreement", "SEBI Registration", "Number", "Contact Person"
}


def find_emails(text):
    return [(m.start(), m.end(), "EMAIL", m.group()) for m in EMAIL_RE.finditer(text)]


def find_phones(text):
    spans = []
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        # Require a phone-plausible digit count and a '+' or a nearby "Tel"/"Phone" cue
        # to avoid matching plain numbers like page counts or share prices.
        if 9 <= len(digits) <= 13 and ("+" in m.group() or re.search(
                r"(Tel|Phone|Mobile|Contact)", text[max(0, m.start() - 15):m.start()], re.IGNORECASE)):
            spans.append((m.start(), m.end(), "PHONE", m.group()))
    return spans


def find_ips(text):
    return [(m.start(), m.end(), "IP_ADDRESS", m.group()) for m in IPV4_RE.finditer(text)]


def find_ssns(text):
    return [(m.start(), m.end(), "SSN", m.group()) for m in SSN_RE.finditer(text)]


def _luhn_ok(digits):
    total, alt = 0, False
    for d in reversed(digits):
        d = int(d)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def find_credit_cards(text):
    spans = []
    for m in CARD_CANDIDATE_RE.finditer(text):
        digits = re.sub(r"[ \-]", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            spans.append((m.start(), m.end(), "CREDIT_CARD", m.group()))
    return spans


def find_dobs(text):
    spans = []
    for m in DOB_KEYWORD_RE.finditer(text):
        spans.append((m.start(1), m.end(1), "DATE_OF_BIRTH", m.group(1)))
    return spans


def find_addresses(text, backward_window=150):
    """
    Anchor on "<PIN> <State>[, India]" (unambiguous -- this string shape is
    essentially always part of a mailing address in an Indian document), then
    expand backward to the nearest sentence/line/colon boundary to capture the
    street/village/building portion, instead of relying on a single giant regex
    to match punctuation-heavy address text end-to-end (which is brittle against
    en-dashes, curly quotes, etc. -- see README).
    """
    spans = []
    prev_anchor_end = 0
    for m in PIN_STATE_RE.finditer(text):
        anchor_start, anchor_end = m.start(), m.end()
        # Cap backward expansion at the previous address's anchor so two
        # addresses joined without a period in between (e.g. "...Registered
        # Office at X, PIN1, State and its Corporate Office at Y, PIN2,
        # State") don't get merged into a single oversized span that
        # swallows the first address.
        window_start = max(0, anchor_start - backward_window, prev_anchor_end)
        preceding = text[window_start:anchor_start]
        boundary = 0
        for bm in _ADDR_BOUNDARY_RE.finditer(preceding):
            boundary = max(boundary, bm.end())
        start = window_start + boundary
        chunk = text[start:anchor_end]
        stripped = chunk.lstrip()
        start += len(chunk) - len(stripped)
        if anchor_end - start >= 8:
            spans.append((start, anchor_end, "ADDRESS", text[start:anchor_end]))
        prev_anchor_end = anchor_end
    return spans


def find_cins(text):
    return [(m.start(), m.end(), "COMPANY_ID", m.group()) for m in CIN_RE.finditer(text)]


COMMON_CAPITALIZED_WORDS = {
    "Hi", "Hello", "Dear", "Please", "Thanks", "Thank", "Regards", "Order",
    "Ticket", "Date", "Total", "The", "This", "That", "You", "Your", "Our",
    "Company", "Offer", "Equity", "Shares", "Book", "Red", "Herring",
    "Prospectus", "India", "Registrar", "Registered", "Corporate", "General",
    "Details", "Type", "Size", "Investor", "Investors", "Bank", "Limited",
    "Private", "Board", "Securities", "Exchange", "Committee", "Fresh",
    "Issue", "Sale", "Working", "Days", "Bid", "Anchor",
}

# Fallback for plain-language contexts (e.g. support tickets, emails) where
# a name isn't next to a corporate-role keyword: two consecutive Title-Case
# words, filtered against common capitalized words that aren't names.
GENERIC_NAME_RE = re.compile(rf"\b({NAME_TOKEN}\s+{NAME_TOKEN})\b")


def _looks_like_name(candidate):
    words = candidate.split()
    if any(w.strip(".") in COMMON_CAPITALIZED_WORDS for w in words):
        return False
    if candidate in LEGAL_STOPWORDS:
        return False
    return True


_PURE_NAME_RE = re.compile(rf"^{NAME_TOKEN}(?:\s+{NAME_TOKEN})*$")


def _add_names_from_list(list_text, base_offset, add):
    """
    Split a matched "Name1, Name2 and Name3, Some Trust, Some Co Ltd" list on
    commas/"and" and keep only whole pieces that look like a complete
    person's name (2-4 capitalized tokens, none of them Family/Trust/
    Limited/etc). Whole-piece validation (rather than a regex that greedily
    grabs the first 2-4 words of a piece) avoids truncating a longer entity
    name -- e.g. "Waterloo Industrial Park VI Private Limited" must be
    rejected in full, not chopped down to a fake 4-word "person name".
    """
    for piece_m in re.finditer(r"[^,]+?(?=,|\s+and\s+|$)", list_text):
        piece = piece_m.group().strip()
        if not piece or not _PURE_NAME_RE.match(piece):
            continue  # contains punctuation/lowercase words etc -> not a clean name
        words = piece.split()
        if 2 <= len(words) <= 4 and not any(w in LIST_STOP_WORDS for w in words):
            start = base_offset + piece_m.start() + (len(piece_m.group()) - len(piece_m.group().lstrip()))
            add(start, start + len(piece), piece)


def find_names(text, use_generic_fallback=True):
    """
    use_generic_fallback: also flag any bare "Title Case Title Case" bigram
    not on the stopword list. This maximizes recall on casual text (support
    tickets, emails) but hurts precision on dense legal/financial documents
    that are full of Title-Case defined terms (e.g. "Book Building",
    "Fresh Issue"). Callers should disable it for that kind of document and
    rely on role-anchored extraction + the gazetteer instead -- see README.
    """
    spans = []
    covered = []

    def add(start, end, name):
        if name not in LEGAL_STOPWORDS:
            spans.append((start, end, "PERSON_NAME", name))
            covered.append((start, end))

    for m in ROLE_ANCHORED_NAME_RE.finditer(text):
        add(m.start(1), m.end(1), m.group(1).strip())
    for m in CONTACT_PERSON_RE.finditer(text):
        add(m.start(1), m.end(1), m.group(1).strip())
    for m in NAME_LIST_RE.finditer(text):
        _add_names_from_list(m.group(1), m.start(1), add)
    if use_generic_fallback:
        for m in GENERIC_NAME_RE.finditer(text):
            if any(not (m.end(1) <= c[0] or m.start(1) >= c[1]) for c in covered):
                continue
            name = m.group(1).strip()
            if _looks_like_name(name):
                add(m.start(1), m.end(1), name)
    return spans


COMPANY_SUFFIXES = (
    r"Private Limited|Limited|LLP|Pvt\.?\s*Ltd\.?|Inc\.?|Corporation|Corp\.?|"
    r"Co\.?|Bank Limited"
)
COMPANY_RE = re.compile(
    rf"\b(([A-Z][a-zA-Z&\.\-]*\s+)(?:(?:[A-Z][a-zA-Z&\.\-]*|and|of|&)\s+){{0,6}}(?:{COMPANY_SUFFIXES}))\b"
)
GENERIC_COMPANY_STOPWORDS = {
    "Equity Shares Limited",  # never real, guards against odd matches
    "Private Limited", "Limited", "LLP", "Inc.", "Corporation", "Corp.", "Co.", "Bank Limited"
}


def find_companies(text):
    spans = []
    for m in COMPANY_RE.finditer(text):
        name = m.group(1).strip()
        normalized_name = re.sub(r'\s+', ' ', name)
        if normalized_name in GENERIC_COMPANY_STOPWORDS or len(name.split()) < 2:
            continue
        spans.append((m.start(1), m.end(1), "COMPANY_NAME", name))
    return spans


DETECTORS = [
    find_emails,
    find_phones,
    find_ips,
    find_ssns,
    find_credit_cards,
    find_dobs,
    find_addresses,
    find_cins,
    find_names,
    find_companies,
]
