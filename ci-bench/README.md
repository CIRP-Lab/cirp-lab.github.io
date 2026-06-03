# CIBench Website Content & Pipeline Docs

This directory contains the source code for the CIBench leaderboard website. Follow the instructions below to update the leaderboard data, gallery samples, stats, and run the site locally.

## Project Structure

```bash
web/
├── assets/             # Images, system figures, and copied thumbnails
├── css/                # Styling (style.css)
├── data/               # Source JSON files used by the UI
│   ├── leaderboard.json  # Model rankings and scores (generated)
│   ├── samples.json      # Gallery metadata and prompt logs (generated)
│   └── stats.json        # Total tasks and stats (manual/generated)
├── js/
│   └── app.js          # Core front-end logic (sorting, grids, rendering)
├── scripts/
│   ├── copy_assets.py  # Script to copy VLM outputs and convert to WebP
│   └── generate_leaderboard.py  # Aggregates scores and builds leaderboard.json
├── index.html          # Main HTML structure
└── README.md           # This file
```

---

## 1. Updating the Leaderboard Scores

The leaderboard values are aggregated dynamically from VLM evaluation outputs located in `/data/evals/`.

To rebuild the leaderboard rankings and generate `web/data/leaderboard.json`, run:

```bash
# From the project root:
python3 web/scripts/generate_leaderboard.py
```

### Adding new models or planners:
Edit the model dictionaries in `web/scripts/generate_leaderboard.py` (e.g., `MODELS_M1`, `MODELS_M2`, `MODELS_M3`) with the corresponding directory names and UI labels.

---

## 2. Updating Gallery Visualizations

The interactive gallery loads images and prompts dynamically based on `web/data/samples.json`.

To configure which tasks and specific rows/samples are featured in the gallery:
1. Open `web/scripts/copy_assets.py`.
2. Modify the `TARGETS` array by adding/editing the task dictionary:
   ```python
   TARGETS = [
       {"task": "deconv_motion_blur", "manifest": "deconv_motion_blur_samples_manifest.csv", "label": "GOPR0857_11_00__000043"},
       {"task": "event", "manifest": "event_samples_manifest.csv", "label": "10_32"}
   ]
   ```
3. Run the copy script to pull the original input, GT, and predictions into `web/assets/samples/` and update `samples.json`:

```bash
# Recommended (runs in project environment with PIL for WebP compression):
cd web
uv run python scripts/copy_assets.py

# Fallback (regular copy without WebP thumbnailing if PIL is missing):
python3 scripts/copy_assets.py
```

---

## 3. Modifying General Content (Affiliations, Notes, BibTeX)

All static text is configured directly in `web/index.html`:
- **Affiliations & Links:** Handled inside the `<header>` block (lines 53-78).
- **Notes:** Disclaimers regarding preliminary results are located under the Teaser image, and mathematical/scoring disclaimers are located under the Leaderboard table.
- **Citation:** The Citation section block (lines 228-241) is currently set as a placeholder note until the pre-print is officially published.

---

## 4. Local Deployment

To view changes live in your browser:

```bash
cd web
python3 -m http.server 8000
```
Open `http://localhost:8000` in your web browser.
