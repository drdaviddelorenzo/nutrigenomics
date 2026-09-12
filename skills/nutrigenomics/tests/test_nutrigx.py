"""
test_nutrigenomics.py — Automated test suite for Nutrigenomics
Run with: pytest tests/test_nutrigenomics.py -v

Uses a FIXED synthetic patient (synthetic_patient.csv) with known genotypes
so that all assertions are deterministic and reproducible. This file is NOT
meant to showcase the skill — use examples/generate_patient.py for varied demos.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from parse_input import parse_genetic_file
from extract_genotypes import extract_snp_genotypes
from score_variants import compute_nutrient_risk_scores


SYNTHETIC = Path(__file__).parent / "synthetic_patient.csv"
PANEL     = Path(__file__).parent.parent / "data" / "snp_panel.json"


def load_panel():
    with open(PANEL) as f:
        return json.load(f)


# ── Parsing ────────────────────────────────────────────────────────────────────

def test_parse_23andme():
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    assert len(table) >= 20
    assert "rs1801133" in table
    assert table["rs1801133"] in ("CT", "TC")


def test_all_panel_snps_present():
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    found = sum(1 for v in calls.values() if v["status"] == "found")
    assert found == len(panel), f"Expected all {len(panel)} SNPs found, got {found}"


# ── Extraction ─────────────────────────────────────────────────────────────────

def test_mthfr_heterozygous():
    """Fixed patient has MTHFR C677T = CT (1 risk allele)."""
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    mthfr = calls["rs1801133"]
    assert mthfr["status"] == "found"
    assert mthfr["risk_count"] == 1


def test_vdr_homozygous_risk():
    """Fixed patient has VDR TaqI = CC (2 risk alleles) → drives Elevated vitamin D score."""
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    vdr = calls["rs731236"]
    assert vdr["status"] == "found"
    assert vdr["risk_count"] == 2


def test_aldh2_ref_homozygous():
    """Fixed patient has ALDH2 = GG (0 risk alleles) → Low alcohol risk."""
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    aldh2 = calls["rs671"]
    assert aldh2["status"] == "found"
    assert aldh2["risk_count"] == 0


# ── Scoring ────────────────────────────────────────────────────────────────────

def test_scores_structure():
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    scores = compute_nutrient_risk_scores(calls, panel)
    assert "folate" in scores
    assert "vitamin_d" in scores
    assert "omega3" in scores
    assert "alcohol" in scores
    for domain, data in scores.items():
        if data["score"] is not None:
            assert 0.0 <= data["score"] <= 10.0
        assert data["category"] in ("Low", "Moderate", "Elevated", "Unknown")


def test_vitamin_d_elevated():
    """VDR TaqI hom risk → Vitamin D expected Elevated."""
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    scores = compute_nutrient_risk_scores(calls, panel)
    assert scores["vitamin_d"]["category"] == "Elevated"


def test_alcohol_low():
    """ALDH2 GG ref hom → Alcohol expected Low."""
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    scores = compute_nutrient_risk_scores(calls, panel)
    assert scores["alcohol"]["category"] == "Low"


def test_folate_not_low():
    """MTHFR C677T het → Folate should be Moderate or Elevated, not Low."""
    panel = load_panel()
    table = parse_genetic_file(str(SYNTHETIC), fmt="23andme")
    calls = extract_snp_genotypes(table, panel)
    scores = compute_nutrient_risk_scores(calls, panel)
    assert scores["folate"]["category"] in ("Moderate", "Elevated")


# ── Lactase persistence (rs4988235) ───────────────────────────────────────────
# Adapted from a fix contributed by krudo-taco to the ClawBio nutrigx skill
# (ClawBio/ClawBio@1163f49, MIT). Covers both strand orientations, so the
# strand-flip path in extract_genotypes.py is exercised too.

def _lactose_score(genotype: str) -> dict:
    panel = load_panel()
    calls = extract_snp_genotypes({"rs4988235": genotype}, panel)
    scores = compute_nutrient_risk_scores(calls, panel)
    return {"call": calls["rs4988235"], "score": scores["lactose"]}


def test_rs4988235_panel_polarity_and_citation():
    entry = next(s for s in load_panel() if s["rsid"] == "rs4988235")
    assert entry["ref_allele"] == "A"
    assert entry["risk_allele"] == "G"
    assert entry["pmid"] == "11788828"
    assert entry["inheritance"] == "dominant_protective"


def test_rs4988235_aa_and_tt_are_persistent():
    for genotype in ("AA", "TT"):
        result = _lactose_score(genotype)
        assert result["call"]["status"] == "found"
        assert result["call"]["risk_count"] == 0
        assert result["score"]["category"] == "Low"
        assert result["score"]["score"] == 0.0


def test_rs4988235_ag_and_ct_are_persistent_dominant():
    for genotype in ("AG", "GA", "CT", "TC"):
        result = _lactose_score(genotype)
        assert result["call"]["status"] == "found"
        assert result["call"]["risk_count"] == 1
        assert result["score"]["category"] == "Low"
        assert result["score"]["score"] == 0.0


def test_rs4988235_gg_and_cc_are_non_persistent():
    for genotype in ("GG", "CC"):
        result = _lactose_score(genotype)
        assert result["call"]["status"] == "found"
        assert result["call"]["risk_count"] == 2
        assert result["score"]["category"] == "Elevated"
        assert result["score"]["score"] == 10.0


# ── Reproducibility bundle must not leak the input path ───────────────────────
# Regression test for a privacy defect found by the ClawHub security audit of
# 0.3.2: provenance.json and README_reproducibility.txt both echoed the full
# argument namespace, writing the absolute path of the user's genetic data file
# into artefacts that simultaneously claimed "the input file name and path are
# NOT stored in any artefact".

def test_repro_bundle_does_not_record_input_path(tmp_path):
    import json as _json
    from repro_bundle import create_reproducibility_bundle

    secret = tmp_path / "jane_smith_genome_verysecret.csv"
    secret.write_text("rsid\tchromosome\tposition\tgenotype\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "nutrigenomics_report.md").write_text("# report\n", encoding="utf-8")

    create_reproducibility_bundle(
        input_file=str(secret),
        output_dir=str(out),
        panel_path=str(PANEL),
        args={
            "input": str(secret),
            "output": str(out),
            "format": "23andme",
            "panel": None,
            "no_figures": False,
        },
    )

    for artefact in out.iterdir():
        if artefact.name == "nutrigenomics_report.md":
            continue
        text = artefact.read_text(encoding="utf-8", errors="replace")
        assert str(secret) not in text, f"{artefact.name} leaks the input path"
        assert secret.name not in text, f"{artefact.name} leaks the input filename"
        assert str(tmp_path) not in text, f"{artefact.name} leaks a local path"

    provenance = _json.loads((out / "provenance.json").read_text(encoding="utf-8"))
    assert set(provenance["format_args"]) <= {"format", "no_figures", "custom_panel"}
    assert provenance["version"] != "0.2.8", "version must track the release, not be hardcoded"


# ── Output writes must not follow symlinks ────────────────────────────────────
# Regression test for the ClawHub audit finding "Symlink Following Vulnerability".
# Output filenames are deterministic, so an attacker who can pre-create a symlink
# at one of them could redirect a write outside the validated output directory.

def test_safe_write_refuses_symlink(tmp_path):
    from path_safety import safe_write_text

    target = tmp_path / "escaped.txt"
    link = tmp_path / "report.md"
    link.symlink_to(target)

    try:
        safe_write_text(link, "payload")
    except ValueError as exc:
        assert "symbolic link" in str(exc)
    else:
        raise AssertionError("safe_write_text followed a symlink")

    assert not target.exists(), "write escaped through the symlink"


def test_safe_write_still_overwrites_regular_files(tmp_path):
    from path_safety import safe_write_text

    path = tmp_path / "report.md"
    safe_write_text(path, "first")
    safe_write_text(path, "second")
    assert path.read_text(encoding="utf-8") == "second"
