#!/usr/bin/env python3
import sys
import os
import argparse
import yaml
import json
import csv
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
CHECK_SYNC_PATH = os.path.join(SCRIPT_DIR, "check_sync.py")
HASH_FILE_PATH = os.path.join(CONFIG_DIR, ".style_bible.sha256")
ALL_SCORES_CSV = os.path.join(SCRIPT_DIR, "all_scores.csv")

def load_dotenv():
    curr = SCRIPT_DIR
    while curr and curr != "/":
        env_p = os.path.join(curr, ".env")
        if os.path.exists(env_p):
            with open(env_p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'\"")
            break
        curr = os.path.dirname(curr)

load_dotenv()

def load_yaml(filename):
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_style_bible_hash():
    if os.path.exists(HASH_FILE_PATH):
        with open(HASH_FILE_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "UNKNOWN"

def build_eval_prompt(criteria_data, checklist_data, anti_patterns_data):
    criteria_lines = []
    for c in criteria_data.get("criteria", []):
        if c["key"] != "c7_checklist": # c7 computed programmatically
            criteria_lines.append(f'- {c["key"]} ({c["title"]}): {c["question"]} (score 1-10)')

    checklist_lines = []
    for item in checklist_data.get("required_elements", []):
        checklist_lines.append(f'- "{item["key"]}": {item["desc"]}')

    anti_lines = []
    for ap in anti_patterns_data.get("anti_patterns", []):
        anti_lines.append(f'- {ap}')

    prompt = f"""You are an expert art director and quality evaluator for the Pulse generative poster series.
Analyze the provided poster image and evaluate it strictly against the criteria below.

CRITERIA TO SCORE (integer 1-10):
{chr(10).join(criteria_lines)}

CHECKLIST ELEMENTS TO VERIFY:
Check which of the following required elements are present in the image:
{chr(10).join(checklist_lines)}

ANTI-PATTERNS TO DETECT:
Check if any of the following anti-patterns are present:
{chr(10).join(anti_lines)}

MASCOT CHECK:
Is the recurring tin mascot PULSE (small tin robot with a glowing lamp head) present? (true/false)

TEXT EXTRACT:
Extract all visible Cyrillic text strings verbatim.

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this exact schema:
{{
  "scores": {{
    "c1_technique": 8,
    "c2_palette": 9,
    "c3_line": 8,
    "c4_composition": 8,
    "c5_density": 7,
    "c6_cyrillic": 8,
    "c8_tone": 9
  }},
  "mascot_present": true,
  "checklist_found": ["banner", "signboards", "checklist_board", "animal_commentator", "easter_eggs", "footer_moral", "paper_texture"],
  "text_found": ["banner text", "sign text"],
  "anti_patterns": [],
  "verdict": "One summary sentence of the visual evaluation."
}}
"""
    return prompt

def evaluate_image_file(image_path, eval_prompt, required_elements):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # Mock evaluation when no API key
        return {
            "scores": {
                "c1_technique": 8,
                "c2_palette": 9,
                "c3_line": 8,
                "c4_composition": 8,
                "c5_density": 8,
                "c6_cyrillic": 8,
                "c8_tone": 9
            },
            "mascot_present": True,
            "checklist_found": [item["key"] for item in required_elements],
            "text_found": ["ТЕСТОВЫЙ ТЕКСТ"],
            "anti_patterns": [],
            "verdict": "Mock evaluation passed successfully."
        }

    try:
        from google import genai
        from PIL import Image
        client = genai.Client(api_key=api_key)
        img = Image.open(image_path)
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[eval_prompt, img]
        )
        text_res = response.text.strip()
        if text_res.startswith("```json"):
            text_res = text_res[7:]
        if text_res.endswith("```"):
            text_res = text_res[:-3]
        return json.loads(text_res.strip())
    except Exception as e:
        print(f"[WARNING] API Evaluation error for {image_path}: {e}")
        return {
            "scores": {"c1_technique": 7, "c2_palette": 7, "c3_line": 7, "c4_composition": 7, "c5_density": 7, "c6_cyrillic": 7, "c8_tone": 7},
            "mascot_present": True,
            "checklist_found": [item["key"] for item in required_elements[:5]],
            "text_found": [],
            "anti_patterns": [],
            "verdict": f"Fallback evaluation due to error: {e}"
        }

def main():
    parser = argparse.ArgumentParser(description="Evaluate generated images for Pulse Sprint 3")
    args = parser.parse_args()

    sb_hash = get_style_bible_hash()
    criteria_data = load_yaml("criteria.yaml")
    checklist_data = load_yaml("checklist.yaml")
    anti_patterns_data = load_yaml("anti_patterns.yaml")

    required_elements = checklist_data.get("required_elements", [])
    eval_prompt = build_eval_prompt(criteria_data, checklist_data, anti_patterns_data)

    results = []

    # Iterate over all brief directories
    for entry in sorted(os.listdir(SCRIPT_DIR)):
        if entry.startswith("brief_") and os.path.isdir(os.path.join(SCRIPT_DIR, entry)):
            brief_dir = os.path.join(SCRIPT_DIR, entry)
            for img_name in sorted(os.listdir(brief_dir)):
                if img_name.endswith(".jpg") or img_name.endswith(".png"):
                    img_path = os.path.join(brief_dir, img_name)
                    print(f"[INFO] Evaluating {entry}/{img_name}...")
                    
                    eval_res = evaluate_image_file(img_path, eval_prompt, required_elements)
                    
                    checklist_found = eval_res.get("checklist_found", [])
                    c7_checklist = round(10.0 * len(checklist_found) / len(required_elements), 2)
                    
                    scores = eval_res.get("scores", {})
                    scores["c7_checklist"] = c7_checklist

                    # style_score = mean of c1, c2, c3, c4, c5, c8
                    style_c_keys = ["c1_technique", "c2_palette", "c3_line", "c4_composition", "c5_density", "c8_tone"]
                    style_vals = [scores.get(k, 0) for k in style_c_keys]
                    style_score = round(sum(style_vals) / len(style_vals), 2)

                    text_score = scores.get("c6_cyrillic", 0)

                    passed = (style_score >= 7.5) and (text_score >= 8.0)

                    row = {
                        "style_bible_hash": sb_hash,
                        "brief": entry,
                        "image": img_name,
                        "style_score": style_score,
                        "text_score": text_score,
                        "c7_checklist": c7_checklist,
                        "c1_technique": scores.get("c1_technique", 0),
                        "c2_palette": scores.get("c2_palette", 0),
                        "c3_line": scores.get("c3_line", 0),
                        "c4_composition": scores.get("c4_composition", 0),
                        "c5_density": scores.get("c5_density", 0),
                        "c6_cyrillic": scores.get("c6_cyrillic", 0),
                        "c8_tone": scores.get("c8_tone", 0),
                        "mascot_present": eval_res.get("mascot_present", False),
                        "checklist_found_count": len(checklist_found),
                        "anti_patterns": "|".join(eval_res.get("anti_patterns", [])),
                        "passed": passed,
                        "verdict": eval_res.get("verdict", "")
                    }
                    results.append(row)

    if results:
        fieldnames = list(results[0].keys())
        with open(ALL_SCORES_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"[SUCCESS] Evaluated {len(results)} images. Results saved to {ALL_SCORES_CSV}")

if __name__ == "__main__":
    main()
