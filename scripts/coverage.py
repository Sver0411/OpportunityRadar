#!/usr/bin/env python3
"""coverage.py - Search Coverage Ledger（V3）。

用户无法判断"是真的没机会，还是 Agent 没搜到"。
本模块记录每个 region/locale/category/source_family 的查询量、候选量、验证量，
并给出一句自然语言说明。**不得声称"已经搜遍所有机会"**。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: 深度阈值（按 query 数）
DEEP_QUERIES = 4
MEDIUM_QUERIES = 2


class Coverage:
    def __init__(self):
        self.rows = []          # 每个 (region, locale, category, source_family) 一行

    def record(self, region=None, locale=None, category=None, source_family=None,
               query_count=0, candidate_count=0, verified_count=0):
        row = {
            "region": region or "unknown", "locale": locale or "unknown",
            "category": category or "unknown", "source_family": source_family or "general",
            "query_count": int(query_count), "candidate_count": int(candidate_count),
            "verified_count": int(verified_count),
        }
        row["coverage_depth"] = self.depth(row["query_count"])
        self.rows.append(row)
        return row

    @staticmethod
    def depth(queries: int) -> str:
        if queries >= DEEP_QUERIES:
            return "deep"
        if queries >= MEDIUM_QUERIES:
            return "medium"
        return "shallow"

    # ---------- 汇总 ----------
    def by_region(self) -> dict:
        out = {}
        for r in self.rows:
            d = out.setdefault(r["region"], {"queries": 0, "candidates": 0, "verified": 0, "categories": {}})
            d["queries"] += r["query_count"]
            d["candidates"] += r["candidate_count"]
            d["verified"] += r["verified_count"]
            c = d["categories"].setdefault(r["category"], {"queries": 0, "depth": "shallow"})
            c["queries"] += r["query_count"]
            c["depth"] = self.depth(c["queries"])
        return out

    def totals(self) -> dict:
        return {
            "rows": len(self.rows),
            "queries": sum(r["query_count"] for r in self.rows),
            "candidates": sum(r["candidate_count"] for r in self.rows),
            "verified": sum(r["verified_count"] for r in self.rows),
        }

    def natural_language(self) -> str:
        """一句自然语言说明（给用户看，不倒内部日志）。"""
        by_region = self.by_region()
        if not by_region:
            return "本轮没有记录搜索覆盖信息。"
        regions = []
        for region, d in by_region.items():
            deep = [c for c, v in d["categories"].items() if v["depth"] == "deep"]
            shallow = [c for c, v in d["categories"].items() if v["depth"] == "shallow"]
            seg = region
            if shallow:
                seg += f"（{'、'.join(sorted(shallow))}仅浅扫）"
            if deep:
                seg += f"[深扫: {'、'.join(sorted(deep))}]"
            regions.append(seg)
        return ("本轮重点扫描了 " + "、".join(regions) + "；这是有限预算下的覆盖，"
                "不是全互联网完整扫描。")

    def to_dict(self) -> dict:
        return {"totals": self.totals(), "by_region": self.by_region(),
                "rows": self.rows, "statement": self.natural_language()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Search coverage ledger")
    ap.add_argument("--ledger", help="已有 ledger JSON，输出汇总")
    ap.add_argument("--add", action="append", default=[], metavar="region,locale,category,q,cand,verified")
    ap.add_argument("--statement", action="store_true", help="只输出自然语言说明")
    args = ap.parse_args(argv)

    cov = Coverage()
    if args.ledger and os.path.exists(args.ledger):
        with open(args.ledger, encoding="utf-8") as fh:
            data = json.load(fh)
        for r in data.get("rows", []):
            cov.record(**{k: r.get(k) for k in ("region", "locale", "category", "source_family",
                                                "query_count", "candidate_count", "verified_count")})
    for item in args.add:
        parts = [p.strip() for p in item.split(",")]
        parts += ["0"] * (6 - len(parts))
        cov.record(parts[0], parts[1], parts[2], None, int(parts[3] or 0), int(parts[4] or 0),
                   int(parts[5] or 0))
    print(cov.natural_language() if args.statement else json.dumps(cov.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
