from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from stock_research.cli import run_comparator_evidence
from stock_research.comparator_evidence import (
    build_comparator_evidence_pack,
    render_comparator_markdown,
    render_comparator_markdown_zh,
)


PDD_COMPARATOR_REQUEST = {
    "main_company": {
        "name": "PDD Holdings",
        "ticker": "PDD",
        "market": "US",
    },
    "competitors": [
        "Alibaba",
        "JD",
        "Amazon",
        "SHEIN",
        "TikTok Shop",
        "AliExpress",
    ],
    "battlefields": [
        "China ecommerce",
        "Cross-border ecommerce",
        "Merchant advertising",
        "Logistics",
        "Supply chain",
    ],
}


class ComparatorEvidencePipelineTest(unittest.TestCase):
    def test_comparator_pack_builds_target_company_evidence(self) -> None:
        pack = build_comparator_evidence_pack(PDD_COMPARATOR_REQUEST)

        self.assertEqual(pack["schema_version"], "comparator_evidence_pack_v1")
        self.assertEqual(pack["main_company"]["name"], "PDD Holdings")
        self.assertEqual(len(pack["competitor_map"]), 6)
        self.assertEqual(len(pack["competitor_packs"]), 6)
        self.assertEqual(len(pack["comparison_matrix"]), 6)
        self.assertIn("battlefield_analysis", pack)
        self.assertIn("source_refs", pack)
        self.assertIn("downstream_routing", pack)
        self.assertGreaterEqual(len(pack["battlefield_analysis"]), 8)
        self.assertGreaterEqual(len(pack["source_refs"]), 8)

        tiktok = _pack_by_id(pack, "tiktok-shop")
        self.assertEqual(tiktok["business_overlap"]["level"], "high")
        self.assertEqual(tiktok["threat_to_target"], "high")
        self.assertEqual(tiktok["moat_replication_risk"], "high")
        self.assertIn("Merchant advertising", tiktok["business_overlap"]["battlefields"])
        self.assertEqual(tiktok["evidence_reliability"]["overall"], "medium")
        self.assertIn("Detailed standalone financial statements", tiktok["evidence_reliability"]["unavailable_evidence"])
        self.assertIn("tiktok_shop_seller_terms_us", tiktok["source_refs"])
        self.assertEqual(tiktok["scorecard"]["dimensions"]["acquisition_channel_overlap"], "high")
        self.assertTrue(tiktok["counterevidence_and_uncertainties"])
        self.assertTrue(tiktok["evidence_gaps"])

        alibaba = _matrix_row_by_id(pack, "alibaba")
        self.assertEqual(alibaba["overlap"], "high")
        self.assertEqual(alibaba["business_model_similarity"], "high")
        self.assertEqual(alibaba["valuation_peer_quality"], "partial")

        social = _battlefield_by_name(pack, "Social commerce")
        self.assertEqual(social["evidence_status"], "source_ref_only_pending_excerpt")
        self.assertIn("tiktok_shop_seller_terms_us", social["source_refs"])
        self.assertTrue(social["open_questions"])

        routing = pack["downstream_routing"]
        self.assertIn("Social commerce", routing["moat_agent"]["battlefields"])
        self.assertIn("valuation_peer_quality", routing["valuation_agent"]["competitor_pack_fields"])

        for category in ["business_model", "moat", "growth", "risk", "valuation"]:
            self.assertTrue(pack["implications"][category], category)
            for implication in pack["implications"][category]:
                self.assertIn("PDD Holdings", implication["statement"])
                self.assertTrue(implication["evidence_refs"])

        markdown = render_comparator_markdown(pack)
        self.assertIn("Comparator Evidence Report: PDD Holdings", markdown)
        self.assertIn("This report treats competitors as evidence about the target company", markdown)
        self.assertIn("TikTok Shop", markdown)
        self.assertIn("Fixed questions", markdown)
        self.assertIn("Battlefield Deep Dive", markdown)
        self.assertIn("Source-Grounded Evidence Index", markdown)
        self.assertIn("No investment recommendation", markdown)

        zh_markdown = render_comparator_markdown_zh(pack)
        self.assertIn("竞争对手证据报告：PDD Holdings", zh_markdown)
        self.assertIn("本报告把竞争对手当作理解目标公司的比较证据", zh_markdown)
        self.assertIn("战场级深挖", zh_markdown)
        self.assertIn("真实来源索引", zh_markdown)
        self.assertIn("可复核评分", zh_markdown)
        self.assertIn("对 PDD Holdings 的含义", zh_markdown)
        self.assertIn("TikTok Shop 是 PDD Holdings", zh_markdown)
        self.assertIn("MVP 边界", zh_markdown)

    def test_comparator_cli_writes_json_and_markdown_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "request.json"
            input_path.write_text(json.dumps(PDD_COMPARATOR_REQUEST), encoding="utf-8")

            result = run_comparator_evidence(
                input_path=input_path,
                output_dir=temp_path / "outputs",
                run_id="fixture-pdd-comparators",
            )

            json_path = Path(result["json_path"])
            markdown_path = Path(result["markdown_path"])
            markdown_zh_path = Path(result["markdown_zh_path"])
            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue(markdown_zh_path.exists())
            self.assertEqual(result["competitor_count"], 6)
            self.assertGreaterEqual(result["implication_count"], 5)

            written_pack = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(written_pack["schema_version"], "comparator_evidence_pack_v1")
            self.assertEqual(_pack_by_id(written_pack, "amazon")["valuation_peer_quality"], "not_clean")

            written_markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Comparison Matrix", written_markdown)
            self.assertIn("Valuation Peer Quality", written_markdown)
            self.assertIn("Amazon", written_markdown)

            written_zh_markdown = markdown_zh_path.read_text(encoding="utf-8")
            self.assertIn("对比矩阵", written_zh_markdown)
            self.assertIn("估值可比性", written_zh_markdown)
            self.assertIn("下游 Agent 使用路由", written_zh_markdown)
            self.assertIn("不对目标公司或竞争对手给出买卖建议", written_zh_markdown)


def _pack_by_id(pack: dict, competitor_id: str) -> dict:
    for item in pack["competitor_packs"]:
        if item["competitor_id"] == competitor_id:
            return item
    raise AssertionError(f"Missing competitor pack: {competitor_id}")


def _matrix_row_by_id(pack: dict, competitor_id: str) -> dict:
    for item in pack["comparison_matrix"]:
        if item["competitor_id"] == competitor_id:
            return item
    raise AssertionError(f"Missing comparison matrix row: {competitor_id}")


def _battlefield_by_name(pack: dict, battlefield: str) -> dict:
    for item in pack["battlefield_analysis"]:
        if item["battlefield"] == battlefield:
            return item
    raise AssertionError(f"Missing battlefield: {battlefield}")


if __name__ == "__main__":
    unittest.main()
