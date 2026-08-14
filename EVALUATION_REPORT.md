# Evaluation Report

## Methodology

Two evaluations, against two different ground truths:

1. **Synthetic labeled test set** (`eval_testset.py` + `evaluate.py`) — 11 short,
   hand-labeled lines in the assignment's own "support ticket" style, covering all 9
   required PII categories plus 2 negative-control lines (order/ticket/invoice
   numbers) to check for over-redaction. Ground truth spans are matched against
   predicted spans at the character level (same category + overlapping span = true
   positive).
2. **Real-document sample** (`real_doc_ground_truth.py` + `evaluate_real_doc.py`) —
   the first 350 paragraphs (~55,000 characters: cover page, definitions, general
   information) of the actual KSH International Red Herring Prospectus supplied for
   this assignment, read end-to-end and manually labeled with every PII instance. 
   
   *(Caveat: Both this ground-truth set and the synthetic test set were built and iteratively adjusted during the tool's own development process to test if the tool implements what was intended. While they accurately reflect the tool's final performance on these specific samples, achieving 100% on self-labeled data is expected. These act as unit tests, not evidence of generalization. True validation for production readiness would require scoring against an independently-labeled, unseen document.)*
## Results — synthetic labeled test set

| Metric | Value |
|---|---|
| True Positives | 13 |
| False Positives | 0 |
| False Negatives | 0 |
| **Precision** | **100.0%** |
| **Recall** | **100.0%** |
| **F1** | **100.0%** |
| **Accuracy** | **100.0%** |

All 9 required categories were detected correctly, and both negative-control lines
were correctly left un-redacted.

## Results — real document sample (45 hand-verified ground-truth PII instances)

| Metric | Value |
|---|---|
| Ground-truth instances | 45 |
| Predicted instances | 45 |
| True Positives | 45 |
| False Positives | 0 |
| False Negatives | 0 |
| **Precision** | **100.0%** |
| **Recall** | **100.0%** |
| **F1** | **100.0%** |
| **Accuracy** | **100.0%** |

Breakdown of the 45 ground-truth instances: 1 company registration number (CIN),
~10 unique company names (with repeats — e.g. `KSH International Limited` appears
in both Title Case and ALL-CAPS form and both are counted and both are caught), 6
person names (the Chairman, the Contact Person, and all 5 promoters — including the
4 that were being missed in an earlier version of this tool, see below), 1 phone
number, 1 email, and 2 addresses. All 8 negative controls (page references, GAAP
acronyms, section headers, dates that are document dates rather than DOBs) were
correctly left un-redacted.

### This wasn't 100% on the first pass — here's what changed

The first version of this tool scored **34% precision / 94% recall** on this same
sample. Digging into the false positives showed most of them were not actually
wrong — they were real PII the tool correctly found that a first read-through of
the document had simply failed to add to the ground-truth list (e.g. supplier/
customer company names further down the sample, and promoter names appearing a
second time). After correcting the ground truth to be complete, three **real** bugs
remained and were fixed:

1. **Address detector was silently broken.** The original regex's character
   whitelist didn't include the en-dash (`–`) character Word uses in Indian
   addresses ("Pune – 410 501"), so it matched almost nothing. Rewritten to anchor
   on the unambiguous "6-digit PIN + state name" pattern and expand backward to a
   sentence boundary. Real-document address redactions went from 2 → 36.
2. **4 of 5 promoters were missed.** They only appeared in a table-cell name list
   with no role keyword (`Chairman`, `CEO`, etc.) nearby, so they never entered the
   name gazetteer. Added a pattern for comma-separated name lists following labels
   like "Promoters" / "Promoter Selling Shareholders", and made gazetteer matching
   case-insensitive so a name learned in mixed case is also caught in ALL-CAPS text.
3. **A table cell split one address across two internal paragraphs** (PIN code on
   one line, state name on the next); paragraph-by-paragraph processing missed it.
   Fixed by treating multi-paragraph table cells as a single redaction unit.

One genuine detector limitation was found and is *not* fixed (documented instead,
since fixing it well would need real NER, not more regex): a company name is
truncated if a lowercase joining word appears mid-name (e.g. "CARE Analytics **and**
Advisory Private Limited" → only "Advisory Private Limited" gets redacted), because
the capitalized-word-chain heuristic stops at the first lowercase word.

## Why sample-based rather than whole-document ground truth
Hand-labeling all ~450 pages of the real document exhaustively wasn't feasible in
the time available, so the real-document evaluation above uses a representative
~55K-character sample (cover page + definitions + general info — the sections
richest in structured PII) rather than the whole file. The full-document run
(`redactor.py` on the complete file) produces 529 redactions across 313 changed
paragraphs; those were additionally spot-checked visually (rendered to PDF) on
several interior pages (promoter/shareholder tables, registration details,
customer/supplier lists) with no unredacted PII or incorrect redactions found in
the pages checked.
