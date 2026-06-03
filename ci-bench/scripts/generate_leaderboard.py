import csv
import json
from pathlib import Path
import sys

# Add the project root to python path to import image_bench
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

def normalize_psnr(val: float) -> float:
    return max(0.0, min(1.0, (val - 15.0) / 25.0))

def normalize_ssim(val: float) -> float:
    return max(0.0, min(1.0, val))

def normalize_lpips(val: float) -> float:
    return max(0.0, min(1.0, 1.0 - val))

def normalize_niqe(val: float) -> float:
    return max(0.0, min(1.0, (20.0 - val) / 17.0))

def _instance_score(row: dict) -> float:
    psnr, ssim, lpips, niqe = None, None, None, None
    if 'psnr' in row and row['psnr'] and row['psnr'] != 'nan': psnr = float(row['psnr'])
    if 'ssim' in row and row['ssim'] and row['ssim'] != 'nan': ssim = float(row['ssim'])
    if 'lpips' in row and row['lpips'] and row['lpips'] != 'nan': lpips = float(row['lpips'])
    if 'niqe' in row and row['niqe'] and row['niqe'] != 'nan': niqe = float(row['niqe'])

    weighted_parts = []
    if psnr is not None:
        weighted_parts.append((0.3, normalize_psnr(psnr)))
    if ssim is not None:
        weighted_parts.append((0.3, normalize_ssim(ssim)))
    if lpips is not None:
        weighted_parts.append((0.3, normalize_lpips(lpips)))
    if niqe is not None:
        weighted_parts.append((0.1, normalize_niqe(niqe)))

    if not weighted_parts:
        return None

    total_weight = sum(w for w, _ in weighted_parts)
    return sum((w / total_weight) * v for w, v in weighted_parts)


# M1 corresponds to base execution (P1), M2 corresponds to planner-guided (P2)
# The prompt says: "Nano Banana 2 (Gemini 3.1 Flash Image Preview) [P1]"
# "GPT-Image-1.5 [P1]", "Qwen-Image-Edit-2511 [P1]"
# P2 planners: "Gemini 3.1 Pro Preview", "GPT-5", "Qwen3.5-35B-A3B"

MODELS_M1 = {
    "gemini": {"name": "Gemini 3.1 Flash Image Preview", "planner": "N/A", "type": "Commercial"},
    "openai": {"name": "GPT-Image-1.5", "planner": "N/A", "type": "Commercial"},
    "qwen": {"name": "Qwen-Image-Edit-2511", "planner": "N/A", "type": "Open-source"},
}

MODELS_M2 = {
    "gemini": {"name": "Gemini 3.1 Flash Image Preview", "planner": "Gemini 3.1 Pro Preview", "type": "Commercial"},
    "openai": {"name": "GPT-Image-1.5", "planner": "GPT-5", "type": "Commercial"},
    "qwen": {"name": "Qwen-Image-Edit-2511", "planner": "Qwen3.5-35B-A3B", "type": "Open-source"},
}

MODELS_M3 = {
    "gemini": {"name": "Gemini 3.1 Flash Image Preview", "planner": "Gemini 3.1 Pro Preview", "type": "Commercial"},
    "openai": {"name": "GPT-Image-1.5", "planner": "GPT-5", "type": "Commercial"},
    "qwen": {"name": "Qwen-Image-Edit-2511", "planner": "Qwen3.5-35B-A3B", "type": "Open-source"},
}

CATEGORIES = {
    "Ray/Wave Optics": ["cgh"],
    "Calibration": ["lens_distortion"],
    "Computational Sensing": ["tof", "deconv_lensless", "event", "lightfield_view_extrapolation", "lightfield_view_interpolation"],
    "Image Signal Processing": ["demosaicking_hexadeca", "demosaicking_quad", "demosaicking_regular", "hdr", "white_balance", "denoising", "denoising_synthesis"],
    "Inverse Reconstruction": ["cs_block", "rand_mask_subsample", "deconv_spherical_aberration", "deconv_longitudinal_ca", "super_resolution", "inpainting", "deconv_motion_blur"]
}

def get_category_for_task(task_name):
    for cat, tasks in CATEGORIES.items():
        if task_name in tasks:
            return cat
    return None

def load_summary_stats():
    # Read the overall summary stats
    # data/evals/report/summary_stats.csv contains overall average PSNR/SSIM/LPIPS/NIQE for m1/m2 families.
    # But we want individual models. The prompt says we need to read individual CSVs using get_task_scores.
    pass

def generate():
    leaderboard = []

    # Process M1 models (P1)
    for model_key, meta in MODELS_M1.items():
        # Get unified score
        try:
            eval_dir = project_root / "data" / "evals" / "m1" / model_key
            task_scores = []
            category_scores = {c: [] for c in CATEGORIES.keys()}
            if eval_dir.exists():
                for f in eval_dir.glob("*.csv"):
                    if "matches" in f.name or f.name in ["all_tasks.csv", "selected_prediction_runs.csv"]:
                        continue
                    
                    task_name = f.stem
                    category = get_category_for_task(task_name)
                    
                    instance_scores = []
                    with open(f, 'r', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            score = _instance_score(row)
                            if score is not None:
                                instance_scores.append(score)

                    if instance_scores:
                        task_avg = sum(instance_scores) / len(instance_scores)
                        task_scores.append(task_avg)
                        if category:
                            category_scores[category].append(task_avg)

            unified_score = sum(task_scores) / len(task_scores) if task_scores else 0.0
            cat_avgs = {c: (sum(scores) / len(scores) if scores else 0.0) for c, scores in category_scores.items()}

            leaderboard.append({
                "Protocol": "P1",
                "Model": meta["name"],
                "Planner": meta["planner"],
                "Type": meta["type"],
                "Unified": round(unified_score * 100, 2),
                "Ray/Wave Optics": round(cat_avgs["Ray/Wave Optics"] * 100, 2),
                "Calibration": round(cat_avgs["Calibration"] * 100, 2),
                "Computational Sensing": round(cat_avgs["Computational Sensing"] * 100, 2),
                "Image Signal Processing": round(cat_avgs["Image Signal Processing"] * 100, 2),
                "Inverse Reconstruction": round(cat_avgs["Inverse Reconstruction"] * 100, 2)
            })
        except Exception as e:
            print(f"Error processing M1 {model_key}: {e}")

    # Process M2 models (P2)
    for model_key, meta in MODELS_M2.items():
        try:
            eval_dir = project_root / "data" / "evals" / "m2" / model_key
            task_scores = []
            category_scores = {c: [] for c in CATEGORIES.keys()}
            if eval_dir.exists():
                for f in eval_dir.glob("*.csv"):
                    if "matches" in f.name or f.name in ["all_tasks.csv", "selected_prediction_runs.csv"]:
                        continue
                    
                    task_name = f.stem
                    category = get_category_for_task(task_name)
                    
                    instance_scores = []
                    with open(f, 'r', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            score = _instance_score(row)
                            if score is not None:
                                instance_scores.append(score)
                    
                    if instance_scores:
                        task_avg = sum(instance_scores) / len(instance_scores)
                        task_scores.append(task_avg)
                        if category:
                            category_scores[category].append(task_avg)

            unified_score = sum(task_scores) / len(task_scores) if task_scores else 0.0
            cat_avgs = {c: (sum(scores) / len(scores) if scores else 0.0) for c, scores in category_scores.items()}

            leaderboard.append({
                "Protocol": "P2",
                "Model": meta["name"],
                "Planner": meta["planner"],
                "Type": meta["type"],
                "Unified": round(unified_score * 100, 2),
                "Ray/Wave Optics": round(cat_avgs["Ray/Wave Optics"] * 100, 2),
                "Calibration": round(cat_avgs["Calibration"] * 100, 2),
                "Computational Sensing": round(cat_avgs["Computational Sensing"] * 100, 2),
                "Image Signal Processing": round(cat_avgs["Image Signal Processing"] * 100, 2),
                "Inverse Reconstruction": round(cat_avgs["Inverse Reconstruction"] * 100, 2)
            })
        except Exception as e:
            print(f"Error processing M2 {model_key}: {e}")

    # Process M3 models (P3)
    for model_key, meta in MODELS_M3.items():
        try:
            eval_dir = project_root / "data" / "evals" / "m3" / model_key
            task_scores = []
            category_scores = {c: [] for c in CATEGORIES.keys()}
            if eval_dir.exists():
                for f in eval_dir.glob("*.csv"):
                    if "matches" in f.name or f.name in ["all_tasks.csv", "selected_prediction_runs.csv"]:
                        continue
                    
                    task_name = f.stem
                    category = get_category_for_task(task_name)
                    
                    instance_scores = []
                    with open(f, 'r', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            score = _instance_score(row)
                            if score is not None:
                                instance_scores.append(score)
                    
                    if instance_scores:
                        task_avg = sum(instance_scores) / len(instance_scores)
                        task_scores.append(task_avg)
                        if category:
                            category_scores[category].append(task_avg)

            unified_score = sum(task_scores) / len(task_scores) if task_scores else 0.0
            cat_avgs = {c: (sum(scores) / len(scores) if scores else 0.0) for c, scores in category_scores.items()}

            leaderboard.append({
                "Protocol": "P3",
                "Model": meta["name"],
                "Planner": meta["planner"],
                "Type": meta["type"],
                "Unified": round(unified_score * 100, 2),
                "Ray/Wave Optics": round(cat_avgs["Ray/Wave Optics"] * 100, 2),
                "Calibration": round(cat_avgs["Calibration"] * 100, 2),
                "Computational Sensing": round(cat_avgs["Computational Sensing"] * 100, 2),
                "Image Signal Processing": round(cat_avgs["Image Signal Processing"] * 100, 2),
                "Inverse Reconstruction": round(cat_avgs["Inverse Reconstruction"] * 100, 2)
            })
        except Exception as e:
            print(f"Error processing M3 {model_key}: {e}")

    out_path = project_root / "web" / "data" / "leaderboard.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(leaderboard, f, indent=2)
    print(f"Leaderboard saved to {out_path}")

if __name__ == "__main__":
    generate()
