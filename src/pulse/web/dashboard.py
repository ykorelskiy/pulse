"""Web Diagnostic Dashboard server for Pulse news database inspection."""

import json
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from socketserver import ThreadingMixIn
from typing import Any

from pulse.config import get_config
from pulse.db.repo import NewsRepo
from pulse.sources.registry import SourceRegistry

HARD_BAN_KEYWORDS = [
    "погиб", "пострад", "убит", "гибель", "ранен", "жертв", "убийств",
    "крушени", "авари", "рухнул", "катастроф", "пожар"
]


def build_diagnostic_payload() -> dict[str, Any]:
    """Fetch 24h news data from Supabase and compile structured diagnostic statistics."""
    repo = NewsRepo()
    registry = SourceRegistry.load_from_config()

    source_map: dict[str, str] = {}
    sources_summary: dict[str, dict[str, Any]] = {}

    for adapter in registry.get_all():
        sid = adapter.source_id
        sname = getattr(adapter, "name", sid)
        source_map[sid] = sname
        sources_summary[sid] = {
            "source_id": sid,
            "source_name": sname,
            "total": 0,
            "scored": 0,
            "pending": 0,
            "rejected_victims": 0,
            "archived": 0,
            "passed": 0,
            "articles": [],
        }

    raw_items = repo.get_diagnostic_24h_full_data()
    now = datetime.now(timezone.utc)

    # First pass: cluster breadth count
    cluster_sources: dict[str, set[str]] = {}
    for item in raw_items:
        cid = str(item.get("cluster_id") or item.get("id"))
        sid = str(item.get("source_id") or "news")
        if cid not in cluster_sources:
            cluster_sources[cid] = set()
        cluster_sources[cid].add(sid)

    for item in raw_items:
        sid = str(item.get("source_id") or "unknown")
        sname = source_map.get(sid, sid)

        if sid not in sources_summary:
            sources_summary[sid] = {
                "source_id": sid,
                "source_name": sname,
                "total": 0,
                "scored": 0,
                "pending": 0,
                "rejected_victims": 0,
                "archived": 0,
                "passed": 0,
                "articles": [],
            }

        s_entry = sources_summary[sid]
        s_entry["total"] += 1

        status = item.get("status") or "pending"

        headline_orig = (item.get("headline") or "").strip()
        ru_headline = (item.get("ru_headline") or headline_orig).strip()
        has_victims = item.get("has_victims") or False

        # Ban reason check
        banned = False
        ban_reason = ""

        matched_kw = [k for k in HARD_BAN_KEYWORDS if k in ru_headline.lower() or k in headline_orig.lower()]
        if status == "rejected_victims" or has_victims:
            banned = True
            ban_reason = "ЧП / Жертвы (ИИ)"
        elif matched_kw:
            banned = True
            ban_reason = f"Ключевое слово: '{matched_kw[0]}'"

        if status == "pending":
            s_entry["pending"] += 1
            status_flag = "PENDING"
        elif status == "archived":
            s_entry["archived"] += 1
            status_flag = "ARCHIVED"
        elif banned:
            s_entry["rejected_victims"] += 1
            status_flag = "BANNED"
        else:
            s_entry["scored"] += 1
            s_entry["passed"] += 1
            status_flag = "PASSED"

        # Scores calculation
        rel = item.get("relevance") or 0
        comedic = item.get("comedic_potential") or 0
        sig = item.get("significance") or 0
        tone = item.get("tone") or 0
        quality_score = rel + comedic + sig + tone if status == "scored" else 0

        cid = str(item.get("cluster_id") or item.get("id"))
        breadth_score = min(len(cluster_sources.get(cid, {sid})), 5)

        coll_at = item.get("collected_at")
        hours_old = 0.0
        if coll_at:
            try:
                if isinstance(coll_at, str):
                    dt = datetime.fromisoformat(coll_at.replace("Z", "+00:00"))
                else:
                    dt = coll_at
                hours_old = (now - dt).total_seconds() / 3600.0
            except Exception:
                hours_old = 0.0

        freshness_score = max(0, 6 - int(hours_old / 4.0))
        total_score = quality_score + breadth_score + freshness_score if status == "scored" else 0

        article_obj = {
            "id": str(item.get("id")),
            "headline_orig": headline_orig,
            "ru_headline": ru_headline,
            "url": item.get("url", "#"),
            "collected_at": coll_at or "",
            "status": status,
            "status_flag": status_flag,
            "ban_reason": ban_reason,
            "relevance": rel,
            "comedic_potential": comedic,
            "significance": sig,
            "tone": tone,
            "quality_score": quality_score,
            "breadth_score": breadth_score,
            "freshness_score": freshness_score,
            "total_score": total_score,
        }
        s_entry["articles"].append(article_obj)

    # Sort articles in each source strictly by total_score descending
    for src in sources_summary.values():
        src["articles"].sort(key=lambda a: a["total_score"], reverse=True)

    # Sort sources by total items desc
    sorted_sources = sorted(list(sources_summary.values()), key=lambda x: x["total"], reverse=True)

    total_articles = sum(s["total"] for s in sorted_sources)
    total_passed = sum(s["passed"] for s in sorted_sources)
    total_pending = sum(s["pending"] for s in sorted_sources)
    total_banned = sum(s["rejected_victims"] for s in sorted_sources)
    total_archived = sum(s["archived"] for s in sorted_sources)

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_articles": total_articles,
        "total_passed": total_passed,
        "total_pending": total_pending,
        "total_banned": total_banned,
        "total_archived": total_archived,
        "sources": sorted_sources,
    }


DASHBOARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pulse Diagnostic Dashboard — База новостей за 24ч</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-yellow: #eab308;
            --accent-gray: #64748b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 20px;
            line-height: 1.5;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
        }
        .header h1 { font-size: 24px; font-weight: 700; color: var(--accent-blue); display: flex; align-items: center; gap: 10px; }
        .header .meta { font-size: 14px; color: var(--text-muted); }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }
        .stat-card .val { font-size: 28px; font-weight: 800; margin-top: 4px; }
        .stat-card.total .val { color: var(--accent-blue); }
        .stat-card.passed .val { color: var(--accent-green); }
        .stat-card.pending .val { color: var(--accent-yellow); }
        .stat-card.banned .val { color: var(--accent-red); }
        .stat-card.archived .val { color: var(--accent-gray); }

        .controls {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .search-box {
            flex: 1;
            min-width: 250px;
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            color: var(--text-main);
            font-size: 14px;
        }
        .filter-btn {
            padding: 10px 16px;
            border-radius: 8px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            color: var(--text-main);
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .filter-btn.active, .filter-btn:hover {
            background: var(--accent-blue);
            color: #000;
            border-color: var(--accent-blue);
            font-weight: 600;
        }

        .source-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            margin-bottom: 16px;
            overflow: hidden;
        }
        .source-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            cursor: pointer;
            user-select: none;
            background: rgba(255, 255, 255, 0.02);
            transition: background 0.2s;
        }
        .source-header:hover { background: rgba(255, 255, 255, 0.05); }
        .source-title { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .source-badges { display: flex; gap: 8px; font-size: 13px; }

        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }
        .badge.total { background: #0284c7; color: #fff; }
        .badge.passed { background: #166534; color: #4ade80; }
        .badge.pending { background: #854d0e; color: #fde047; }
        .badge.banned { background: #991b1b; color: #fca5a5; }
        .badge.archived { background: #334155; color: #cbd5e1; }

        .articles-table-wrap {
            display: none;
            padding: 16px;
            border-top: 1px solid var(--card-border);
            background: #0f172a;
            overflow-x: auto;
        }
        .source-card.open .articles-table-wrap { display: block; }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }
        th, td {
            padding: 10px 12px;
            border-bottom: 1px solid #1e293b;
        }
        th {
            background: #1e293b;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }
        tr:hover { background: rgba(255, 255, 255, 0.03); }

        .headline-link { color: var(--accent-blue); text-decoration: none; font-weight: 500; }
        .headline-link:hover { text-decoration: underline; }
        .orig-title { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

        .score-val { font-weight: 700; }
        .status-cell { display: flex; align-items: center; gap: 6px; font-weight: 600; }
        .status-cell.passed { color: var(--accent-green); }
        .status-cell.banned { color: var(--accent-red); }
        .status-cell.pending { color: var(--accent-yellow); }
        .status-cell.archived { color: var(--accent-gray); }

        .expand-icon { transition: transform 0.2s; }
        .source-card.open .expand-icon { transform: rotate(180deg); }
    </style>
</head>
<body>

    <div class="header">
        <h1>📊 Pulse News Diagnostic Dashboard</h1>
        <div class="meta">
            Автообновление: <span id="last-update">Загрузка...</span>
            <button onclick="fetchData()" class="filter-btn" style="margin-left: 10px; padding: 4px 10px;">🔄 Обновить</button>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card total"><div>Всего новостей (24ч)</div><div class="val" id="stat-total">0</div></div>
        <div class="stat-card passed"><div>Прошли в ТОП ✅</div><div class="val" id="stat-passed">0</div></div>
        <div class="stat-card pending"><div>В очереди ⏳</div><div class="val" id="stat-pending">0</div></div>
        <div class="stat-card banned"><div>Забанено (ЧП/Жертвы) ❌</div><div class="val" id="stat-banned">0</div></div>
        <div class="stat-card archived"><div>Дубликаты 📦</div><div class="val" id="stat-archived">0</div></div>
    </div>

    <div class="controls">
        <input type="text" id="search-input" class="search-box" placeholder="🔍 Поиск по заголовку или источнику..." oninput="filterData()">
        <button class="filter-btn active" onclick="setFilter('all', this)">Все новости</button>
        <button class="filter-btn" onclick="setFilter('PASSED', this)">✅ Прошедшие</button>
        <button class="filter-btn" onclick="setFilter('BANNED', this)">❌ Забаненные</button>
        <button class="filter-btn" onclick="setFilter('PENDING', this)">⏳ В очереди</button>
        <button class="filter-btn" onclick="setFilter('ARCHIVED', this)">📦 Дубликаты</button>
    </div>

    <div id="sources-container">
        <div style="text-align: center; padding: 40px; color: var(--text-muted);">Загрузка данных из базы...</div>
    </div>

    <script>
        let globalData = null;
        let activeFilter = 'all';

        async function fetchData() {
            try {
                const res = await fetch('/api/stats');
                globalData = await res.json();
                renderData();
            } catch (err) {
                console.error("Failed to fetch stats:", err);
            }
        }

        function setFilter(filterType, btn) {
            activeFilter = filterType;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderData();
        }

        function filterData() {
            renderData();
        }

        function renderData() {
            if (!globalData) return;

            document.getElementById('last-update').innerText = globalData.timestamp;
            document.getElementById('stat-total').innerText = globalData.total_articles;
            document.getElementById('stat-passed').innerText = globalData.total_passed;
            document.getElementById('stat-pending').innerText = globalData.total_pending;
            document.getElementById('stat-banned').innerText = globalData.total_banned;
            document.getElementById('stat-archived').innerText = globalData.total_archived;

            const searchQuery = document.getElementById('search-input').value.toLowerCase().trim();
            const container = document.getElementById('sources-container');
            container.innerHTML = '';

            globalData.sources.forEach(src => {
                const filteredArticles = src.articles.filter(art => {
                    const matchesFilter = activeFilter === 'all' || art.status_flag === activeFilter;
                    const matchesSearch = !searchQuery || 
                        art.ru_headline.toLowerCase().includes(searchQuery) ||
                        art.headline_orig.toLowerCase().includes(searchQuery) ||
                        src.source_name.toLowerCase().includes(searchQuery);
                    return matchesFilter && matchesSearch;
                });

                if (filteredArticles.length === 0 && searchQuery) return;

                const card = document.createElement('div');
                card.className = 'source-card';
                if (searchQuery || activeFilter !== 'all') card.classList.add('open');

                const header = document.createElement('div');
                header.className = 'source-header';
                header.onclick = () => card.classList.toggle('open');

                header.innerHTML = `
                    <div class="source-title">
                        <span class="expand-icon">▼</span>
                        <span>${src.source_name}</span>
                    </div>
                    <div class="source-badges">
                        <span class="badge total">Всего: ${src.total}</span>
                        <span class="badge passed">✅ ${src.passed}</span>
                        <span class="badge pending">⏳ ${src.pending}</span>
                        <span class="badge banned">❌ ${src.rejected_victims}</span>
                        <span class="badge archived">📦 ${src.archived}</span>
                    </div>
                `;

                const tableWrap = document.createElement('div');
                tableWrap.className = 'articles-table-wrap';

                // Sort filtered articles strictly in descending order by total_score
                filteredArticles.sort((a, b) => b.total_score - a.total_score);

                let rowsHtml = '';
                filteredArticles.forEach((art, idx) => {
                    let statusBadge = '';
                    if (art.status_flag === 'PASSED') {
                        statusBadge = '<span class="status-cell passed">✅ Прошла</span>';
                    } else if (art.status_flag === 'BANNED') {
                        statusBadge = `<span class="status-cell banned">❌ Бан (${art.ban_reason})</span>`;
                    } else if (art.status_flag === 'PENDING') {
                        statusBadge = '<span class="status-cell pending">⏳ Ожидает</span>';
                    } else {
                        statusBadge = '<span class="status-cell archived">📦 Дубликат</span>';
                    }

                    rowsHtml += `
                        <tr>
                            <td>${idx + 1}</td>
                            <td>
                                <a href="${art.url}" target="_blank" class="headline-link">${art.ru_headline}</a>
                                ${art.headline_orig !== art.ru_headline ? `<div class="orig-title">${art.headline_orig}</div>` : ''}
                            </td>
                            <td title="Релевантность (1-5)">${art.relevance}</td>
                            <td title="Потенциал юмора/абсурда (1-5)">${art.comedic_potential}</td>
                            <td title="Общая значимость (1-5)">${art.significance}</td>
                            <td title="Тон (-1/0/+1)">${art.tone}</td>
                            <td class="score-val" title="Сумма базовых оценок">${art.quality_score}</td>
                            <td title="Балл за число СМИ в кластере (0-5)">${art.breadth_score}</td>
                            <td title="Балл за свежесть (0-6)">${art.freshness_score}</td>
                            <td class="score-val" style="color: var(--accent-blue); font-size: 14px;">${art.total_score}</td>
                            <td>${statusBadge}</td>
                        </tr>
                    `;
                });

                tableWrap.innerHTML = `
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Заголовок новости</th>
                                <th title="Релевантность для читателя">Релевантность</th>
                                <th title="Юмор и абсурдность">Юмор</th>
                                <th title="Масштаб и значимость">Значимость</th>
                                <th title="Тональность новости">Тон</th>
                                <th title="Качество (Сумма)">Качество</th>
                                <th title="Охват в СМИ">Охват (СМИ)</th>
                                <th title="Свежесть новости">Свежесть</th>
                                <th title="Итоговый балл ранжирования (по убыванию)">Итоговый балл ⬇️</th>
                                <th>Статус / Причина</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rowsHtml || '<tr><td colspan="11" style="text-align:center; color: var(--text-muted);">Нет новостей по фильтру</td></tr>'}
                        </tbody>
                    </table>
                `;

                card.appendChild(header);
                card.appendChild(tableWrap);
                container.appendChild(card);
            });
        }

        fetchData();
        setInterval(fetchData, 30000);
    </script>
</body>
</html>
"""


class DiagnosticDashboardHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler delivering HTML dashboard and JSON stats API."""

    def do_GET(self) -> None:
        if self.path == "/api/stats":
            payload = build_diagnostic_payload()
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = DASHBOARD_HTML_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format_str: str, *args: Any) -> None:
        """Suppress standard HTTP server request logs."""
        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server."""

    daemon_threads = True


def run_dashboard_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run diagnostic web dashboard server."""
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, DiagnosticDashboardHandler)
    print(f"🚀 Pulse Diagnostic Web Dashboard running on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard server...")
        httpd.server_close()


if __name__ == "__main__":
    run_dashboard_server(port=8080)
