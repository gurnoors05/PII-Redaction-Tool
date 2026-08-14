# PII Redaction Tool

## What this does

This tool reads the Red Herring Prospectus (.docx) and finds personal/sensitive
information in it, then replaces it with fake but realistic-looking data. Every
time the same real name/email/company shows up, it gets replaced with the same
fake value, so the document still reads naturally.

## How it works

The script goes through the document twice:

1. **First pass** — it scans the whole file just looking for high-confidence
   stuff: things like "Contact Person: <Name>", "Chief Executive Officer ...
   being <Name>", or company names ending in "Limited", "LLP", "Inc.", etc.
   This builds a small list of real names/companies that actually show up in
   this document.

2. **Second pass** — it goes through every paragraph, table cell, header, and
   footer, and redacts everything: emails, phones, IPs, SSNs, credit cards,
   dates of birth, addresses, company registration numbers (CIN), plus any
   name/company from the list built in step 1 — even if it's written in ALL
   CAPS somewhere else in the document.

Every real value always maps to the same fake value (using `fake_values.py`),
so "Rohan Dey" becomes the same fake name everywhere it appears, matching the
example in the assignment.

### Why regex instead of an NER model

Regex works really well for things that follow a fixed pattern — email, phone,
SSN, credit card (I also added a Luhn checksum check to cut down false
matches). For names and addresses, regex is naturally weaker, so I anchored
detection to keywords like "Contact Person:" or "Chairman ... being" instead
of just guessing "two capitalized words = a name." That guess-based approach
would go wrong a lot in this document, because it's full of Title-Case terms
like "Book Building Process" or "Fresh Issue" that aren't names at all.

## What gets redacted (and what doesn't, on purpose)

Redacted: full names, emails, phone numbers, company names, addresses (PIN-code
based), SSNs, credit card numbers, dates of birth, IP addresses, and company
registration numbers (CIN — added as a bonus since it's basically an SSN for a
company).

**Not redacted, on purpose:** order numbers, ticket numbers, invoice numbers,
page numbers, money amounts, and legal terms like "the Offer" or "QIB
Portion." These aren't personal information, and redacting them would just
make the document harder to read for no privacy benefit. I added a few test
cases specifically to check the tool leaves these alone.

## How well it actually works

**On a small test set I wrote myself** (11 lines in the same style as the
assignment's example): 100% precision, 100% recall.

**On a real sample from the actual document** (first 350 paragraphs, about
55,000 characters — cover page, definitions, general info section): 100%
precision, 100% recall against 45 PII instances I checked by hand.


The first version of this tool did much worse on the real document — only 34%
precision and 94% recall. Here's what was actually wrong and how I fixed it:

1. **Addresses were barely being caught.** The regex for matching address text
   didn't include the "–" dash character that Word uses in Indian addresses
   (like "Pune – 410 501"), so almost every address slipped through. I rewrote
   it to look for the PIN code + state name instead, which is a much more
   reliable anchor. Address redactions went from 2 to 36.
2. **4 out of 5 company promoters were being missed.** They only showed up in
   a table listing names, with no keyword like "Chairman" or "CEO" nearby, so
   they never got added to the list of known names. I added a pattern that
   catches comma-separated name lists after labels like "Promoters." I also
   made the name matching case-insensitive, so a name found once in normal
   case also gets caught later in ALL CAPS.
3. **One address was split across two lines inside a table cell** — the PIN
   code was on one line and the state name on the next. Since I was
   processing paragraph by paragraph, it never saw them together. Fixed by
   treating a whole table cell as one unit when it has multiple lines.

**Known limitations (things I'm choosing not to fix right now):**

1. The address detector only understands Indian-style addresses (street +
   6-digit PIN + state name + India). Addresses in other formats won't be
   caught at all.
2. Company names get cut short if there's a lowercase joining word in the
   middle, like "and." So "CARE Analytics **and** Advisory Private Limited"
   only gets partly redacted, as "Advisory Private Limited." Fixing this
   properly would really need an actual NER model, not more regex.
3. I use a list of common non-name phrases (like "Senior Management" or "Key
   Managerial Personnel") to stop them from being wrongly picked up as
   person names when they appear right after something like "Contact
   Person:". This only blocks phrases I've already found — if the document
   used a different generic phrase I haven't seen, it could slip through
   undetected.
4. Dates of birth can be ambiguous. If both parts of a date are 12 or under
   (like 03/04/1990), there's no way to know for sure if it's day/month or
   month/day. The regex accepts both formats, but the fake date it generates
   might swap day and month compared to what a person would assume.

## How to add a new type of PII

1. Write a function `find_x(text)` in `pii_detectors.py` that returns matches
   as `(start, end, "X_CATEGORY", matched_text)`.
2. Add it to the `DETECTORS` list at the bottom of that file.
3. Add a `fake_x(original)` method in `fake_values.py`, and register it in
   `FakeValueFactory.get()`.
4. (Optional) Give it a priority in `CATEGORY_PRIORITY` in `redactor.py` if it
   needs to win or lose against other overlapping matches.

That's it — nothing else needs to change.

## Files in this folder

- `pii_detectors.py` — all the detection logic
- `fake_values.py` — generates the fake replacement values
- `redactor.py` — runs everything (`python3 redactor.py in.docx out.docx audit.csv`)
- `eval_testset.py` — my hand-written test cases
- `evaluate.py` — checks precision/recall against those test cases
- `real_doc_ground_truth.py` — my hand-labeled list of real PII from the actual document
- `evaluate_real_doc.py` — checks precision/recall against the real document sample
- `EVALUATION_REPORT.md` — full results and how I measured them
- `redacted_output.docx` — the final redacted file
- `audit_log.csv` — a log of every redaction made (original value → fake value)

## Running it

```bash
python3 redactor.py "Red Herring Prospectus.docx" redacted_output.docx audit_log.csv
python3 evaluate.py
python3 evaluate_real_doc.py
```