"""Generate the reviewer-readable catalogue from its single authoritative JSON source."""
import argparse
from pathlib import Path
from pipeline.query import CATALOGUE

ROOT = Path(__file__).resolve().parents[1]


def render():
    lines = ["# KPI Catalogue", "", "Generated from `docs/kpi_catalogue.json`; edit that source and run `python -m pipeline.catalogue`.", ""]
    for metric in CATALOGUE:
        lines.extend([f"## {metric['name']}", "", metric["definition"], ""])
        for label,key in (("Grain","grain"),("Filters and Exclusions","exclusions"),("Proposed Owner","owner"),("Known Limitations","limitations")):
            lines.extend([f"**{label}:** {metric[key]}", ""])
        lines.extend([f"**Sources:** {', '.join(metric['sources'])}", ""])
        query = f"[{metric['sql']}](../sql/kpis/{metric['sql']})" if metric["supported"] else "Unavailable with supplied evidence"
        lines.extend([f"**Query:** {query}", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    destination = ROOT / "docs/kpi_catalogue.md"
    content = render()
    if args.check:
        if not destination.exists() or destination.read_text(encoding="utf-8") != content:
            raise SystemExit("Catalogue is stale; run python -m pipeline.catalogue")
    else:
        destination.write_text(content,encoding="utf-8")


if __name__ == "__main__":
    main()
