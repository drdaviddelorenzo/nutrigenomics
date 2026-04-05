"""
repro_bundle.py — Creates reproducibility artefacts for Nutrigenomics
Outputs: README_reproducibility.txt, environment.yml, checksums.txt
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


CONDA_ENV = """name: nutrigenomics
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - numpy>=1.26
  - pandas>=2.2
  - matplotlib>=3.8
  - seaborn>=0.13
  - pip
  - pip:
    
"""


def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return "FILE_NOT_FOUND"


def create_reproducibility_bundle(input_file: str, output_dir: str, panel_path: str, args: dict):
    output_dir = Path(output_dir).resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # README_reproducibility.txt
    cmd_args = " ".join(f"--{k.replace('_', '-')} {v}" for k, v in args.items() if v and k != "synthetic")
    instructions = f"""Nutrigenomics reproducibility notes
Generated: {timestamp}
Version: 0.2.4

This skill does not generate executable scripts. To reproduce the analysis manually:
1. Create the conda environment from environment.yml
2. Run: python nutrigenomics.py {cmd_args}
3. Verify outputs with checksums.txt

Local-only safety notes:
- no network access is required
- input files must be local .txt, .csv, or .vcf files
- outputs are written only inside the chosen working directory
"""
    (output_dir / "README_reproducibility.txt").write_text(instructions, encoding="utf-8")

    # environment.yml
    (output_dir / "environment.yml").write_text(CONDA_ENV, encoding="utf-8")

    # checksums.txt
    files_to_checksum = [
        input_file,
        panel_path,
        str(output_dir / "nutrigenomics_report.md"),
    ]
    checksum_lines = [f"# Nutrigenomics checksums — {timestamp}"]
    for fp in files_to_checksum:
        chk = sha256_file(fp)
        checksum_lines.append(f"{chk}  {Path(fp).name}")

    (output_dir / "checksums.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    # provenance.json
    provenance = {
        "tool": "Nutrigenomics",
        "version": "0.2.4",
        "timestamp": timestamp,
        "input_file": Path(input_file).name,
        "args": args,
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
