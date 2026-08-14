"""
evaluate.py
-----------
Computes precision / recall / F1 / accuracy of the detectors against the
hand-labeled synthetic test set in eval_testset.py, matched at the
character-span level per line. Also runs the gazetteer-building step per
line (simulating how names get "learned" then re-matched) so PERSON_NAME /
COMPANY_NAME behave the same way they do in the real docx pipeline.

Run: python3 evaluate.py
"""

import pii_detectors as det
from eval_testset import LABELED_LINES
from redactor import detect_all, build_gazetteer


def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end <= b_start or a_start >= b_end)


def evaluate():
    all_text = "\n".join(line for line, _ in LABELED_LINES)
    gaz_names, gaz_companies = build_gazetteer(all_text, use_generic_fallback=True)

    tp, fp, fn = [], [], []

    for line, ground_truth in LABELED_LINES:
        gt_spans = []
        for cat, txt in ground_truth:
            idx = line.find(txt)
            gt_spans.append((idx, idx + len(txt), cat, txt))

        pred_spans = detect_all(line, gaz_names, gaz_companies, use_generic_fallback=True)

        matched_gt = set()
        for p in pred_spans:
            found_match = False
            for i, g in enumerate(gt_spans):
                if i in matched_gt:
                    continue
                if g[2] == p[2] and overlaps(p[0], p[1], g[0], g[1]):
                    matched_gt.add(i)
                    tp.append((line, p))
                    found_match = True
                    break
            if not found_match:
                fp.append((line, p))
        for i, g in enumerate(gt_spans):
            if i not in matched_gt:
                fn.append((line, g))

    precision = len(tp) / (len(tp) + len(fp)) if (tp or fp) else float("nan")
    recall = len(tp) / (len(tp) + len(fn)) if (tp or fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    # "Jaccard Index / IoU" here is calculated over the set of spans.
    total_gt = len(tp) + len(fn)
    total_pred = len(tp) + len(fp)
    iou = len(tp) / max(total_gt, total_pred) if max(total_gt, total_pred) else float("nan")

    print(f"True Positives : {len(tp)}")
    print(f"False Positives: {len(fp)}")
    print(f"False Negatives: {len(fn)}")
    print(f"Precision      : {precision:.2%}")
    print(f"Recall         : {recall:.2%}")
    print(f"F1             : {f1:.2%}")
    print(f"Jaccard / IoU  : {iou:.2%}")

    if fp:
        print("\nFalse Positives (over-redaction):")
        for line, p in fp:
            print(f"  [{p[2]}] '{p[3]}'  <- \"{line}\"")
    if fn:
        print("\nFalse Negatives (missed PII):")
        for line, g in fn:
            print(f"  [{g[2]}] '{g[3]}'  <- \"{line}\"")

    return {"tp": len(tp), "fp": len(fp), "fn": len(fn),
            "precision": precision, "recall": recall, "f1": f1, "iou": iou}


if __name__ == "__main__":
    evaluate()
