"""
evaluate_real_doc.py
---------------------
Computes precision / recall / F1 / accuracy against real_doc_ground_truth.py
-- a hand-labeled sample of the ACTUAL document supplied for this assignment
(not the synthetic test set). This is what closes the gap flagged earlier:
"what's the real number, not just the synthetic one?"

Run: python3 evaluate_real_doc.py
"""

import re

from redactor import detect_all, build_gazetteer
from real_doc_ground_truth import GROUND_TRUTH, NEGATIVE_CONTROLS


def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end <= b_start or a_start >= b_end)


def expand_ground_truth(text, labels):
    """Every labeled string may occur more than once in the text; count each
    occurrence as its own ground-truth instance (that's what recall means)."""
    spans = []
    for category, snippet in labels:
        for m in re.finditer(re.escape(snippet), text, re.IGNORECASE):
            spans.append((m.start(), m.end(), category, snippet))
    return spans


def evaluate():
    with open("real_doc_sample.txt", encoding="utf-8") as f:
        text = f.read()

    gaz_names, gaz_companies = build_gazetteer(text, use_generic_fallback=False)
    pred_spans = detect_all(text, gaz_names, gaz_companies, use_generic_fallback=False)
    gt_spans = expand_ground_truth(text, GROUND_TRUTH)

    matched_gt = set()
    tp, fp = [], []
    for p in pred_spans:
        found = False
        for i, g in enumerate(gt_spans):
            if i in matched_gt:
                continue
            if g[2] == p[2] and overlaps(p[0], p[1], g[0], g[1]):
                matched_gt.add(i)
                tp.append(p)
                found = True
                break
        if not found:
            fp.append(p)
    fn = [g for i, g in enumerate(gt_spans) if i not in matched_gt]

    precision = len(tp) / (len(tp) + len(fp)) if (tp or fp) else float("nan")
    recall = len(tp) / (len(tp) + len(fn)) if (tp or fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    iou = len(tp) / max(len(gt_spans), len(pred_spans)) if (gt_spans or pred_spans) else float("nan")

    print(f"Ground-truth instances : {len(gt_spans)}")
    print(f"Predicted instances    : {len(pred_spans)}")
    print(f"True Positives  : {len(tp)}")
    print(f"False Positives : {len(fp)}")
    print(f"False Negatives : {len(fn)}")
    print(f"Precision       : {precision:.1%}")
    print(f"Recall          : {recall:.1%}")
    print(f"F1              : {f1:.1%}")
    print(f"Jaccard / IoU   : {iou:.1%}")

    if fp:
        print("\nFalse Positives (over-redaction):")
        for p in fp:
            print(f"  [{p[2]}] '{p[3]}'")
    if fn:
        print("\nFalse Negatives (missed real PII):")
        for g in fn:
            print(f"  [{g[2]}] '{g[3]}'")

    print("\nNegative-control check (should NOT appear as any predicted span):")
    all_pred_text = [p[3] for p in pred_spans]
    for nc in NEGATIVE_CONTROLS:
        hit = any(nc in pt or pt in nc for pt in all_pred_text)
        print(f"  '{nc}': {'FLAGGED (bad)' if hit else 'correctly ignored'}")

    return {"tp": len(tp), "fp": len(fp), "fn": len(fn),
            "precision": precision, "recall": recall, "f1": f1, "iou": iou}


if __name__ == "__main__":
    evaluate()
