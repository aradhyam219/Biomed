from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from biomedical_extractor.craft import (
    CRAFT_MODULE_VARIANTS,
    CRAFT_SCORED_TYPES,
    evaluate_craft,
    load_craft,
    validate_craft_report_arithmetic,
)
from biomedical_extractor.entity_extraction import Entity


def _annotation_xml(
    *,
    text_source: str,
    mention_id: str,
    spans: tuple[tuple[int, int], ...],
    spanned_text: str,
    ontology_id: str,
) -> str:
    span_xml = "".join(
        f'<span start="{start}" end="{end}" />' for start, end in spans
    )
    return (
        f'<annotations textSource="{text_source}">'
        f"<annotation><mention id=\"{mention_id}\" />"
        f"{span_xml}<spannedText>{spanned_text}</spannedText></annotation>"
        f"<classMention id=\"{mention_id}\"><mentionClass id=\"{ontology_id}\">"
        f"label</mentionClass></classMention></annotations>"
    )


class CRAFTTests(unittest.TestCase):
    def _make_release(self, root: Path) -> None:
        text = "BRCA1 aspirin mouse"
        text_dir = root / "articles" / "txt"
        ids_dir = root / "articles" / "ids"
        text_dir.mkdir(parents=True)
        ids_dir.mkdir(parents=True)
        (text_dir / "1.txt").write_text(text, encoding="utf-8")
        (ids_dir / "craft-ids-train.txt").write_text("1\n", encoding="utf-8")
        (ids_dir / "craft-ids-dev.txt").write_text("", encoding="utf-8")
        (ids_dir / "craft-ids-test.txt").write_text("", encoding="utf-8")
        for module, variant in CRAFT_MODULE_VARIANTS.items():
            directory = root / "concept-annotation" / module / variant / "knowtator"
            directory.mkdir(parents=True)
            if module == "PR":
                xml = (
                    '<annotations textSource="1.txt">'
                    '<annotation><mention id="pr-1" /><span start="0" end="5" />'
                    '<spannedText>BRCA1</spannedText></annotation>'
                    '<annotation><mention id="pr-2" /><span start="0" end="5" />'
                    '<span start="14" end="19" />'
                    '<spannedText>BRCA1 ... mouse</spannedText></annotation>'
                    '<classMention id="pr-1"><mentionClass id="PR:1">label</mentionClass></classMention>'
                    '<classMention id="pr-2"><mentionClass id="PR:2">label</mentionClass></classMention>'
                    '</annotations>'
                )
            elif module == "CHEBI":
                xml = _annotation_xml(
                    text_source="1.txt",
                    mention_id="chebi-1",
                    spans=((6, 13),),
                    spanned_text="aspirin",
                    ontology_id="CHEBI:1",
                )
            elif module == "NCBITaxon":
                xml = _annotation_xml(
                    text_source="1.txt",
                    mention_id="taxon-1",
                    spans=((14, 19),),
                    spanned_text="mouse",
                    ontology_id="NCBITaxon:1",
                )
            else:
                xml = _annotation_xml(
                    text_source="1.txt",
                    mention_id=f"{module}-1",
                    spans=((0, 5),),
                    spanned_text="BRCA1",
                    ontology_id=f"{module}:1",
                )
            (directory / "1.txt.knowtator.xml").write_text(xml, encoding="utf-8")

    def test_load_craft_validates_offsets_and_keeps_mapping_accounting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_release(root)
            dataset = load_craft(root)

        self.assertEqual(len(dataset.documents), 1)
        document = dataset.documents[0]
        self.assertEqual(document.text[0:5], "BRCA1")
        self.assertEqual(document.text[6:13], "aspirin")
        self.assertEqual(document.text[14:19], "mouse")
        statuses = {mention.mapping_status for mention in document.mentions}
        self.assertEqual(statuses, {"scored", "unsupported", "ambiguous"})
        self.assertEqual(
            sum(mention.mapping_status == "scored" for mention in document.mentions),
            3,
        )
        self.assertEqual(
            sum(mention.mapping_status == "ambiguous" for mention in document.mentions),
            1,
        )

    def test_craft_evaluation_reuses_exact_metrics_and_arithmetic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_release(root)
            dataset = load_craft(root)

        predictions = {
            "AIONER": {
                "PMID:1": (
                    Entity("a1", "BRCA1", "Gene", 0, 5, 0.9),
                    Entity("a2", "aspirin", "Chemical", 6, 13, 0.9),
                    Entity("a3", "mouse", "Species", 14, 19, 0.9),
                )
            },
            "HunFlair2": {
                "PMID:1": (
                    Entity("h1", "BRCA1", "Gene", 0, 5, 0.9),
                    Entity("h2", "aspirin", "Chemical", 6, 13, 0.9),
                    Entity("h3", "mouse", "Species", 14, 19, 0.9),
                )
            },
        }
        report = evaluate_craft(dataset, predictions)
        validate_craft_report_arithmetic(report)

        for model in ("AIONER", "HunFlair2"):
            self.assertEqual(
                report["models"][model]["metrics"]["micro"]["f1"], 1.0
            )
            self.assertEqual(
                report["models"][model]["counts"]["gold_scored_mentions"], 3
            )
            self.assertEqual(
                report["models"][model]["counts"]["gold_ambiguous_mentions"], 1
            )
        self.assertEqual(set(report["mapping"]["scored_types"]), set(CRAFT_SCORED_TYPES))


if __name__ == "__main__":
    unittest.main()
