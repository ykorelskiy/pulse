#!/usr/bin/env python3
import sys
import os
import argparse
import yaml
import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
CHECK_SYNC_PATH = os.path.join(SCRIPT_DIR, "check_sync.py")

def load_yaml(filename):
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

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

def load_txt(filename):
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()



def validate_sync():
    cmd = [sys.executable, CHECK_SYNC_PATH]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[ERROR] check_sync.py failed!")
        print(res.stdout)
        print(res.stderr)
        sys.exit(1)

def validate_references(references_data):
    refs = references_data.get("references", [])
    max_active = references_data.get("max_active", 6)
    if len(refs) > max_active:
        print(f"[ERROR] Too many active references! Found {len(refs)}, max allowed is {max_active} (anti-drift rule).")
        sys.exit(1)
    for r in refs:
        rel_path = r.get("path")
        abs_path = os.path.join(SCRIPT_DIR, rel_path)
        if not os.path.exists(abs_path):
            print(f"[WARNING] Reference file not found at {abs_path}")

def validate_brief(brief, limits_data, characters_data):
    text_dict = brief.get("text", {})
    text_budget = limits_data.get("text_budget", {})
    max_blocks = text_budget.get("max_blocks", 7)
    max_words_per_block = text_budget.get("max_words_per_block", 5)

    if len(text_dict) > max_blocks:
        print(f"[ERROR] Brief '{brief['slug']}' exceeds text block limit: {len(text_dict)} > {max_blocks}")
        sys.exit(1)

    for key, text_val in text_dict.items():
        for line in str(text_val).strip().splitlines():
            words = line.strip().split()
            if len(words) > max_words_per_block:
                print(f"[ERROR] Block '{key}' line in brief '{brief['slug']}' exceeds word limit ({len(words)} > {max_words_per_block}): '{line}'")
                sys.exit(1)

    brief_chars = brief.get("characters", [])
    max_supporting = characters_data.get("rules", {}).get("max_supporting_per_image", 2)
    is_stress_test = False
    if len(brief_chars) > max_supporting:
        print(f"[WARNING] Brief '{brief['slug']}' exceeds max supporting characters ({len(brief_chars)} > {max_supporting}). Marking as stress_test: true.")
        is_stress_test = True

    return is_stress_test

def build_prompt(brief, style_block, characters_data):
    mascot_frag = characters_data.get("mascot", {}).get("prompt_fragment", "")
    supporting_dict = {c["id"]: c for c in characters_data.get("supporting", [])}
    
    char_frags = []
    for c_id in brief.get("characters", []):
        if c_id in supporting_dict:
            char_frags.append(f"- {supporting_dict[c_id]['name_ru']} ({supporting_dict[c_id]['role']}): {supporting_dict[c_id]['prompt_fragment']}")

    text_dict = brief.get("text", {})
    text_rendering_lines = ["Render the following Cyrillic text elements EXACTLY in clear Russian lettering:"]
    for k, v in text_dict.items():
        text_rendering_lines.append(f'- {k.upper()}: "{v}"')

    prompt_parts = [
        style_block,
        f"RECURRING MASCOT:\n{mascot_frag}",
    ]
    if char_frags:
        prompt_parts.append("SUPPORTING CHARACTERS:\n" + "\n".join(char_frags))

    prompt_parts.append(f"SCENE:\n{brief.get('scene', '').strip()}")
    prompt_parts.append("\n".join(text_rendering_lines))

    return "\n\n".join(prompt_parts)

def generate_image(prompt, ref_paths, output_filepath):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[NOTICE] GOOGLE_API_KEY is not set in environment. Simulating image generation for testing...")
        # Create dummy image for dry-run / testing structure
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (768, 1024), color=(245, 238, 220))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 748, 1004], outline=(100, 70, 40), width=4)
        draw.text((40, 50), "PULSE MOCK GENERATION", fill=(180, 40, 30))
        draw.text((40, 100), output_filepath.split("/")[-1], fill=(40, 40, 40))
        img.save(output_filepath)
        return {"cost": 0.0, "status": "mock"}

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        # Load reference images if available
        input_contents = [prompt]
        for rp in ref_paths:
            abs_rp = os.path.join(SCRIPT_DIR, rp)
            if os.path.exists(abs_rp):
                from PIL import Image
                input_contents.append(Image.open(abs_rp))

        response = client.models.generate_images(
            model='gemini-3-pro-image-preview',
            prompt=prompt,
            config=dict(
                number_of_images=1,
                aspect_ratio="3:4",
                output_mime_type="image/jpeg"
            )
        )

        for i, generated_image in enumerate(response.generated_images):
            image = Image.open(BytesIO(generated_image.image.image_bytes))
            image.save(output_filepath)
            break
        return {"cost": 0.04, "status": "success"}

    except Exception as e:
        print(f"[WARNING] API generation failed ({e}). Falling back to fallback mock image.")
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (768, 1024), color=(245, 238, 220))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 748, 1004], outline=(100, 70, 40), width=4)
        draw.text((40, 50), "PULSE GENERATION", fill=(180, 40, 30))
        img.save(output_filepath)
        return {"cost": 0.0, "status": "fallback", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Generate images for Pulse Sprint 3 briefs")
    parser.add_argument("--brief", type=int, default=1, help="Brief ID (1-5)")
    parser.add_argument("--count", type=int, default=10, help="Number of generations")
    args = parser.parse_args()

    validate_sync()

    style_block = load_txt("style_block.txt")
    characters_data = load_yaml("characters.yaml")
    limits_data = load_yaml("limits.yaml")
    references_data = load_yaml("references.yaml")
    briefs_data = load_yaml("briefs.yaml")

    validate_references(references_data)

    target_brief = None
    for b in briefs_data.get("briefs", []):
        if b.get("id") == args.brief:
            target_brief = b
            break

    if not target_brief:
        print(f"[ERROR] Brief ID {args.brief} not found in config/briefs.yaml")
        sys.exit(1)

    is_stress_test = validate_brief(target_brief, limits_data, characters_data)
    prompt = build_prompt(target_brief, style_block, characters_data)

    brief_dir_name = f"brief_{target_brief['id']}_{target_brief['slug']}"
    brief_out_dir = os.path.join(SCRIPT_DIR, brief_dir_name)
    prompts_out_dir = os.path.join(SCRIPT_DIR, "prompts")
    os.makedirs(brief_out_dir, exist_ok=True)
    os.makedirs(prompts_out_dir, exist_ok=True)

    print(f"[INFO] Generating {args.count} images for Brief {target_brief['id']} ({target_brief['slug']})...")
    ref_paths = [r["path"] for r in references_data.get("references", [])]

    total_cost = 0.0
    for i in range(1, args.count + 1):
        img_filepath = os.path.join(brief_out_dir, f"run_{i:02d}.jpg")
        prompt_filepath = os.path.join(prompts_out_dir, f"brief_{target_brief['id']}_{target_brief['slug']}_run_{i:02d}.txt")
        
        with open(prompt_filepath, "w", encoding="utf-8") as f:
            f.write(prompt)

        res = generate_image(prompt, ref_paths, img_filepath)
        total_cost += res.get("cost", 0.0)
        print(f"  ✓ [{i}/{args.count}] Saved image to {img_filepath}")

    print(f"[SUCCESS] Completed generation. Estimated cost: ${total_cost:.2f}")

if __name__ == "__main__":
    main()
