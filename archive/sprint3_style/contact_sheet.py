#!/usr/bin/env python3
import csv
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ALL_SCORES_CSV = os.path.join(SCRIPT_DIR, "all_scores.csv")
HTML_OUT = os.path.join(SCRIPT_DIR, "contact_sheet.html")

def main():
    if not os.path.exists(ALL_SCORES_CSV):
        print(f"[ERROR] Scores file not found at {ALL_SCORES_CSV}")
        return

    rows = []
    with open(ALL_SCORES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    html_content = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>PULSE Sprint 3 — Contact Sheet</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1a1a1a; color: #eee; margin: 20px; }
        h1 { color: #f5cf87; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #2a2a2a; border-radius: 8px; padding: 12px; border: 1px solid #444; }
        .card.pass { border-color: #4caf50; }
        .card.fail { border-color: #f44336; }
        .card img { width: 100%; height: auto; border-radius: 4px; display: block; }
        .info { margin-top: 10px; font-size: 13px; }
        .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }
        .badge.pass { background: #2e7d32; color: #fff; }
        .badge.fail { background: #c62828; color: #fff; }
        .scores { display: flex; justify-content: space-between; margin-top: 8px; font-weight: bold; }
    </style>
</head>
<body>
    <h1>PULSE Sprint 3 — Contact Sheet & Scores</h1>
    <p>Style Bible Hash: <code>""" + (rows[0]["style_bible_hash"] if rows else "N/A") + """</code></p>
    <div class="grid">
"""

    for r in rows:
        img_rel = os.path.join(r["brief"], r["image"])
        passed = r["passed"].lower() == "true"
        status_cls = "pass" if passed else "fail"
        status_text = "PASS" if passed else "FAIL"

        html_content += f"""
        <div class="card {status_cls}">
            <img src="{img_rel}" alt="{r['brief']} {r['image']}">
            <div class="info">
                <div><strong>{r['brief']}</strong> - {r['image']}</div>
                <div class="scores">
                    <span>Style: {r['style_score']}</span>
                    <span>Text: {r['text_score']}</span>
                    <span class="badge {status_cls}">{status_text}</span>
                </div>
                <div style="margin-top:4px; font-size: 11px; color: #aaa;">{r['verdict']}</div>
            </div>
        </div>
"""

    html_content += """
    </div>
</body>
</html>
"""

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[SUCCESS] Contact sheet generated at {HTML_OUT}")

if __name__ == "__main__":
    main()
