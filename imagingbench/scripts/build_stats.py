import re
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent

def generate():
    md_path = project_root / "docs/M1_M2_TASK_IO_SUMMARY.md"
    if not md_path.exists():
        print(f"Not found: {md_path}")
        return

    content = md_path.read_text()
    
    # We want to extract basic stats from Overall section
    stats = {
        "Total Models Evaluated": "6",
        "Total Tasks": "5 Categories / 20 Tasks",
        "Outputs Evaluated": "2900",
        "Images Processed": "5074"
    }
    
    out_json = project_root / "web/data/stats.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Generated {out_json}")

if __name__ == "__main__":
    generate()
