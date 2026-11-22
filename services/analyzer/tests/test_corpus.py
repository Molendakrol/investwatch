"""Runs the analyzer over the labelled demo corpus and checks quality.

python -m unittest discover -s services/analyzer/tests -v   (from repo root)
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "analyzer"))

from analyzer.engine import analyze  # noqa: E402
from analyzer.register import DEMO_ENTRIES, Register  # noqa: E402

SITE = ROOT / "demo-sites" / "site"
THRESHOLD = 50.0


def corpus():
    register = Register(list(DEMO_ENTRIES))
    for item in json.loads((SITE / "manifest.json").read_text()):
        raw = (SITE / item["path"]).read_text()
        if item["kind"] == "html":
            yield item["module"], item["label"], item["path"], analyze(url="http://demo/" + item["path"], html=raw, register=register)
        elif item["kind"] == "social":
            post = json.loads(raw)
            yield item["module"], item["label"], item["path"], analyze(url=post["url"], text=post["text"], author=post["author"], register=register)
        else:
            for ad in json.loads(raw)["data"]:
                gold = item["items"][ad["ad_snapshot_url"]]
                yield gold["module"], gold["label"], ad["id"], analyze(
                    url=ad["ad_snapshot_url"], text="\n".join(ad["ad_creative_bodies"]), author=ad["page_name"], register=register)


def module_score(result: dict, module: str) -> float:
    return max((a["score"] for a in result["assessments"] if a["module"] == module), default=0.0)


class CorpusTest(unittest.TestCase):
    def test_quality(self):
        rows, tp, fp, fn, tn = [], 0, 0, 0, 0
        for module, label, name, res in corpus():
            s = module_score(res, module)
            pred = s >= THRESHOLD
            tp += pred and label
            fp += pred and not label
            fn += (not pred) and label
            tn += (not pred) and not label
            mark = "OK " if pred == label else "ERR"
            rows.append(f"{mark} {module} gold={int(label)} score={s:5.1f}  {name}")
        print("\n" + "\n".join(rows))
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        print(f"threshold={THRESHOLD} TP={tp} FP={fp} FN={fn} TN={tn} precision={precision:.2f} recall={recall:.2f}")
        self.assertGreaterEqual(precision, 0.8)
        self.assertGreaterEqual(recall, 0.7)


if __name__ == "__main__":
    unittest.main()
