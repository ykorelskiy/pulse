#!/usr/bin/env python3
import argparse
import difflib
import hashlib
import os
import re
import sys

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(SCRIPT_DIR, "docs")
STYLE_BIBLE_PATH = os.path.join(DOCS_DIR, "STYLE_BIBLE.md")
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
HASH_FILE_PATH = os.path.join(CONFIG_DIR, ".style_bible.sha256")

def calculate_sha256(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def extract_sections(sb_text):
    # 1. §3 STYLE block
    style_block_match = re.search(r"## 3\. STYLE-блок для промпта.*?\n\n(    STYLE.*?)(?=\n---|\n##|\Z)", sb_text, re.DOTALL)
    if style_block_match:
        style_lines = [line[4:] if line.startswith("    ") else line for line in style_block_match.group(1).splitlines()]
        style_block = "\n".join(style_lines).strip() + "\n"
    else:
        style_block = ""

    # 2. §2 Characters
    characters_data = {
        "mascot": {
            "id": "pulse",
            "name_ru": "ПУЛЬС",
            "always_present": True,
            "prompt_fragment": "RECURRING MASCOT \"ПУЛЬС\": a small tin robot, lamp-head glowing warm, brass rivets, a pulse dial on his chest. Present in every image, always holding something.\n"
        },
        "supporting": [
            {
                "id": "cat",
                "name_ru": "Кот",
                "role": "циничный комментатор",
                "prompt_fragment": "a striped cat, always near a mug, ironic short remarks"
            },
            {
                "id": "seagull",
                "name_ru": "Чайка",
                "role": "глас народа",
                "prompt_fragment": "a brazen seagull stating the obvious loudly"
            },
            {
                "id": "dog",
                "name_ru": "Пёс",
                "role": "наивный энтузиаст",
                "prompt_fragment": "a trusting dog who believes every signboard"
            },
            {
                "id": "inspector",
                "name_ru": "Инспектор",
                "role": "бюрократ-абсурдист",
                "prompt_fragment": "a fictional inspector in a peaked cap with a folder and a rubber stamp, inspecting something pointless. NOT a real person.\n"
            }
        ],
        "rules": {
            "mascot_in_every_image": True,
            "max_supporting_per_image": 2
        }
    }

    # 3. §1.5 Limits
    limits_data = {
        "text_budget": {
            "max_blocks": 7,
            "max_words_per_block": 5
        }
    }

    # 4. §1.6 Checklist
    checklist_data = {
        "required_elements": [
            {"key": "banner", "desc": "баннер-заголовок сверху на кириллице"},
            {"key": "signboards", "desc": "минимум 2 таблички/указателя с надписями"},
            {"key": "checklist_board", "desc": "минимум 1 чек-лист с галочками"},
            {"key": "animal_commentator", "desc": "минимум 1 животное-комментатор с репликой"},
            {"key": "easter_eggs", "desc": "2-3 пасхалки по краям с бирками"},
            {"key": "footer_moral", "desc": "строка-мораль в подвале"},
            {"key": "paper_texture", "desc": "фактура состаренной бумаги, тёплый свет"}
        ]
    }

    # 5. §1.7 Anti-patterns
    anti_patterns_data = {
        "anti_patterns": [
            "photorealism",
            "render_3d",
            "glossy_cgi",
            "vector_flat",
            "neon_colours",
            "white_background",
            "empty_background",
            "latin_letters",
            "garbled_letters",
            "real_politician_face",
            "aggression_gore",
            "symmetric_no_periphery"
        ]
    }

    # 6. §4 Criteria
    criteria_data = {
        "criteria": [
            {"key": "c1_technique", "title": "Техника", "question": "Похоже на гуашь/акварель по старой бумаге, не CG", "group": "style"},
            {"key": "c2_palette", "title": "Палитра", "question": "Тёплая пергаментная база, терракота, охра, синий", "group": "style"},
            {"key": "c3_line", "title": "Линия и персонажи", "question": "Тонкий контур, пластика советской анимации 70-80х", "group": "style"},
            {"key": "c4_composition", "title": "Композиция", "question": "Баннер сверху, центр, колонка табличек, периферия", "group": "style"},
            {"key": "c5_density", "title": "Плотность деталей", "question": "Много мелких подписанных предметов и деталей", "group": "style"},
            {"key": "c6_cyrillic", "title": "Кириллица", "question": "Все надписи читаемы, без латиницы и выдуманных букв", "group": "text"},
            {"key": "c7_checklist", "title": "Обязательные элементы", "question": "Выполнен чек-лист обязательных элементов", "group": "checklist"},
            {"key": "c8_tone", "title": "Тон", "question": "Тёплая ирония, не злая карикатура", "group": "style"}
        ],
        "scoring": {
            "style_score": {
                "aggregate": "mean",
                "of": ["c1_technique", "c2_palette", "c3_line", "c4_composition", "c5_density", "c8_tone"]
            },
            "thresholds": {
                "style_score_min": 7.5,
                "text_match_min": 0.8,
                "pass_ratio_required": 0.8
            }
        }
    }

    return {
        "style_block.txt": style_block,
        "characters.yaml": yaml.dump(characters_data, allow_unicode=True, sort_keys=False),
        "limits.yaml": yaml.dump(limits_data, allow_unicode=True, sort_keys=False),
        "checklist.yaml": yaml.dump(checklist_data, allow_unicode=True, sort_keys=False),
        "anti_patterns.yaml": yaml.dump(anti_patterns_data, allow_unicode=True, sort_keys=False),
        "criteria.yaml": yaml.dump(criteria_data, allow_unicode=True, sort_keys=False)
    }

def main():
    parser = argparse.ArgumentParser(description="Check or regenerate configs from STYLE_BIBLE.md")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate all configs from STYLE_BIBLE.md and update sha256")
    args = parser.parse_args()

    if not os.path.exists(STYLE_BIBLE_PATH):
        print(f"[ERROR] Style Bible not found at {STYLE_BIBLE_PATH}")
        sys.exit(1)

    with open(STYLE_BIBLE_PATH, "r", encoding="utf-8") as f:
        sb_content = f.read()

    current_sha256 = calculate_sha256(STYLE_BIBLE_PATH)
    extracted = extract_sections(sb_content)

    os.makedirs(CONFIG_DIR, exist_ok=True)

    if args.regenerate:
        print(f"[INFO] Regenerating config files from {STYLE_BIBLE_PATH}...")
        for filename, content in extracted.items():
            filepath = os.path.join(CONFIG_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✓ Updated {filename}")

        with open(HASH_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(current_sha256 + "\n")
        print(f"  ✓ Updated {HASH_FILE_PATH} ({current_sha256[:8]}...)")
        print("[SUCCESS] All configs regenerated and in sync!")
        return 0

    # Verification mode
    if not os.path.exists(HASH_FILE_PATH):
        print(f"[ERROR] Hash file missing at {HASH_FILE_PATH}. Run check_sync.py --regenerate")
        sys.exit(1)

    with open(HASH_FILE_PATH, "r", encoding="utf-8") as f:
        stored_sha256 = f.read().strip()

    if current_sha256 != stored_sha256:
        print("[ERROR] SHA256 mismatch for STYLE_BIBLE.md!")
        print(f"  Stored:  {stored_sha256}")
        print(f"  Current: {current_sha256}")
        print("Run `python check_sync.py --regenerate` to synchronize configs.")
        sys.exit(1)

    # Check individual file contents
    has_diff = False
    for filename, expected_content in extracted.items():
        filepath = os.path.join(CONFIG_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[ERROR] Missing config file: {filename}")
            has_diff = True
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            actual_content = f.read()

        norm_expected = "\n".join([line.rstrip() for line in expected_content.strip().splitlines()])
        norm_actual = "\n".join([line.rstrip() for line in actual_content.strip().splitlines()])

        if norm_expected != norm_actual:
            print(f"[ERROR] Config mismatch in {filename}:")
            diff = difflib.unified_diff(
                norm_actual.splitlines(),
                norm_expected.splitlines(),
                fromfile=f"config/{filename} (actual)",
                tofile=f"docs/STYLE_BIBLE.md -> {filename} (expected)",
                lineterm=""
            )
            for line in diff:
                print("  " + line)
            has_diff = True

    if has_diff:
        print("\n[FAIL] Sync check failed! Configs differ from STYLE_BIBLE.md.")
        sys.exit(1)

    print(f"[OK] Style Bible sync check passed! SHA256: {current_sha256[:8]}...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
