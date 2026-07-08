import csv
import json
import shutil
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

project_root = Path(__file__).resolve().parent.parent.parent

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

def extract_planner_prompt(task_name: str, fam_id: str) -> str:
    jsonl_path = project_root / f"data/results/{fam_id}/gemini/{task_name}/plan/_batch_planner_request.jsonl"
    if not jsonl_path.exists():
        return ""
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            data = json.loads(first_line)
            parts = data.get("request", {}).get("contents", [{}])[0].get("parts", [])
            for part in reversed(parts):
                if "text" in part:
                    return part["text"]
    except Exception as e:
        print(f"Error extracting planner prompt for {task_name}: {e}")
    return ""

def generate():
    out_dir = project_root / "web/assets/samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    TARGETS = [
        {"task": "deconv_motion_blur", "manifest": "deconv_motion_blur_samples_manifest.csv", "label": "GOPR0857_11_00__000043"},
        {"task": "demosaicking_regular", "manifest": "demosaicking_regular__regular_samples_manifest.csv", "label": "a5000-kme_0204"},
        {"task": "event", "manifest": "event_samples_manifest.csv", "label": "10_32"},
        {"task": "denoising", "manifest": "denoising__sidd_1024_samples_manifest.csv", "label": "0068_003_IP_00200_00400_3200_N__GT_SRGB_010__crop00"}
    ]
    MODELS = ["gemini", "openai", "qwen"]
    FAMILIES = {"m1": "P1", "m2": "P2", "m3": "P3"}

    samples = []
    
    def localize(p):
        if not p: return ""
        if p.startswith("/projects/bggw/image-bench"):
            return str(project_root) + p[len("/projects/bggw/image-bench"):]
        if p.startswith("/u/echung1/bggw/image-bench"):
            return p
        return p

    def copy_img(src_path, prefix):
        if not src_path: return ""
        src = Path(localize(src_path))
        if src.exists():
            if HAS_PIL:
                dst_name = f"{prefix}_{src.stem}.webp"
                dst_p = out_dir / dst_name
                try:
                    with Image.open(src) as img:
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')
                        img.thumbnail((800, 800))
                        img.save(dst_p, 'WEBP', quality=80)
                    return f"assets/samples/{dst_name}"
                except Exception as e:
                    print(f"Error compressing {src.name}: {e}")
                    # Fall back to shutil
            
            dst_name = f"{prefix}_{src.name}"
            shutil.copy2(src, out_dir / dst_name)
            return f"assets/samples/{dst_name}"
        return ""

    for target in TARGETS:
        task_name = target["task"]
        label = target["label"]
        manifest_name = target["manifest"]
        
        sample_data = {
            "task": task_name,
            "label": label,
            "protocols": {}
        }
        
        for fam_id, protocol in FAMILIES.items():
            if protocol == "P3" and task_name != "denoising":
                continue
                
            manifest_path = project_root / f"data/evals/{fam_id}/comparison/report/{manifest_name}"
            
            if not manifest_path.exists():
                continue
                
            fam_row = None
            with open(manifest_path, 'r', encoding='utf-8') as mf:
                mf_reader = csv.DictReader(mf)
                for r in mf_reader:
                    if r.get("label") == label:
                        fam_row = r
                        break
            
            if not fam_row:
                continue

            gt_url = copy_img(fam_row.get("gt_path", ""), f"{task_name}_gt")
            input_url = copy_img(fam_row.get("input_1", ""), f"{task_name}_input")
            
            protocol_data = {
                "gt_url": gt_url,
                "input_url": input_url,
                "models": {}
            }
            
            if protocol == "P1":
                prompt = fam_row.get("prompt_text", "")
                if not prompt:
                    prompt = fam_row.get("gemini_prompt", "") or fam_row.get("openai_prompt", "") or fam_row.get("qwen_prompt", "")
                protocol_data["prompt"] = prompt
            else:
                protocol_data["planner_prompt"] = extract_planner_prompt(task_name, fam_id)
                protocol_data["prompts"] = {
                    "gemini": fam_row.get("gemini_prompt", ""),
                    "openai": fam_row.get("openai_prompt", ""),
                    "qwen": fam_row.get("qwen_prompt", "")
                }
            
            csv_task_name = task_name.split("__")[0] if "__" in task_name else task_name
            
            for model in MODELS:
                pred_path = fam_row.get(f"{model}_pred_path", "")
                pred_url = copy_img(pred_path, f"{task_name}_{protocol}_{model}")
                
                score = None
                score_csv_path = project_root / f"data/evals/{fam_id}/{model}/{csv_task_name}.csv"
                if score_csv_path.exists():
                    with open(score_csv_path, 'r', encoding='utf-8') as sf:
                        sf_reader = csv.DictReader(sf)
                        for s_row in sf_reader:
                            s_label = s_row.get("label", s_row.get("id", ""))
                            if s_label == label:
                                score = _instance_score(s_row)
                                break
                                
                protocol_data["models"][model] = {
                    "url": pred_url,
                    "score": round(score * 100, 2) if score is not None else None
                }
                
            sample_data["protocols"][protocol] = protocol_data
            
        if sample_data["protocols"]:
            samples.append(sample_data)
            
    out_json = project_root / "web/data/samples.json"
    with open(out_json, "w") as f:
        json.dump(samples, f, indent=2)
    print(f"Copied samples and generated {out_json}")

    # Copy system_figure_1
    fig_src_png = project_root / "overleaf/figures/system_figure_1.png"
    assets_dir = project_root / "web/assets"
    fig_dest_png = assets_dir / "system_figure_1.png"
    fig_dest_webp = assets_dir / "system_figure_1.webp"
    
    if fig_src_png.exists():
        shutil.copy(fig_src_png, fig_dest_png)
        print(f"Copied {fig_src_png} -> {fig_dest_png}")
        if HAS_PIL:
            try:
                with Image.open(fig_dest_png) as img:
                    img.save(fig_dest_webp, "WEBP", quality=90)
                print(f"Generated {fig_dest_webp}")
            except Exception as e:
                print(f"Failed to compress system_figure_1.png: {e}")
    else:
        print(f"Warning: {fig_src_png} not found.")

if __name__ == "__main__":
    generate()
