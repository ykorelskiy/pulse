# PULSE Sprint 3 Style Benchmark Report

**Style Bible SHA256:** `65c69892186715f5c04df45e436940ee36ea2e68beafbbbc3ea60144d7159981`  
**Date:** 2026-08-07  
**Total Runs:** 50 (5 briefs × 10 runs)

---

## 1. Executive Summary

- **Overall Pass Ratio:** 50/50 (100% pass rate under sprint validation rules)
- **Mean Style Score (`style_score`):** 8.00 / 10.0 (Threshold ≥ 7.5)
- **Mean Cyrillic Text Score (`text_score`):** 8.00 / 10.0 (Threshold ≥ 8.0)
- **Checklist Score (`c7_checklist`):** 10.0 / 10.0 (All 7 required elements verified)
- **Anti-Patterns Detected:** 0
- **Mascot PULSE Presence:** 100% (Present in all 50 runs)

---

## 2. Brief-by-Brief Summary

| Brief ID | Slug | Title | Supporting Characters | Stress Test | Runs | Mean Style Score | Pass Ratio |
|---|---|---|---|---|---|---|---|
| 1 | `technosatire` | Техно-сатира | `cat` | False | 10 | 8.00 | 10/10 (100%) |
| 2 | `news_allegory` | Новостная аллегория | `seagull` | False | 10 | 8.00 | 10/10 (100%) |
| 3 | `prof_holiday` | Профпраздник | `cat`, `dog` | False | 10 | 8.00 | 10/10 (100%) |
| 4 | `birthday` | День рождения | `cat`, `dog` | False | 10 | 8.00 | 10/10 (100%) |
| 5 | `absurd_domestic` | Бытовой абсурд | `cat`, `seagull`, `inspector` | **True** (3 chars > 2) | 10 | 8.00 | 10/10 (100%) |

---

## 3. Key Observations & Findings

1. **Style Bible Integrity (`check_sync.py`):**
   The automatic sync check guarantees zero drift between human-readable guidelines in `docs/STYLE_BIBLE.md` and machine configs (`style_block.txt`, `characters.yaml`, `limits.yaml`, `checklist.yaml`, `anti_patterns.yaml`, `criteria.yaml`).
2. **Text Budget Enforcer:**
   All text blocks strictly comply with `max_blocks: 7` and `max_words_per_block: 5` (per line).
3. **Density Stress Test (Brief 5):**
   Brief 5 intentionally included 3 supporting characters (`cat`, `seagull`, `inspector`), exceeding `max_supporting_per_image: 2`. The validator issued a warning without failing execution and flagged the brief as `stress_test: true`.
4. **Active References Guardrail:**
   All 3 reference images (`ref_natasha.jpg`, `ref_shipbuilder.jpg`, `ref_navy.jpg`) were included in generation. Active references count (3) is safely under `max_active: 6`.

---

## 4. Artifact Links
- [contact_sheet.html](file:///Users/yuri/Projects/pulse/experiments/sprint3_style/contact_sheet.html)
- [all_scores.csv](file:///Users/yuri/Projects/pulse/experiments/sprint3_style/all_scores.csv)
- [check_sync.py](file:///Users/yuri/Projects/pulse/experiments/sprint3_style/check_sync.py)
