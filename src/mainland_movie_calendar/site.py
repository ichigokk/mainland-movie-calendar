from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
from typing import Any


def render_index(
    state: dict[str, Any],
    *,
    today: date,
    public_base_url: str,
) -> str:
    calendar_url = f"{public_base_url.rstrip('/')}/calendar.ics"
    webcal_url = calendar_url.replace("https://", "webcal://", 1)
    movies = [
        movie
        for movie in state.get("movies", [])
        if date.fromisoformat(movie["release_date"]) >= today and movie.get("status") != "released"
    ]
    rows = "\n".join(
        (
            "<tr>"
            f'<td><time datetime="{escape(movie["release_date"])}">'
            f"{escape(movie['release_date'])}</time></td>"
            f'<td><a href="{escape(movie["source_url"])}">{escape(movie["title"])}</a></td>'
            f"<td>{escape(' / '.join(movie.get('countries', [])))}</td>"
            f"<td>{'待定' if movie.get('status') == 'withdrawn' else '已定档'}</td>"
            "</tr>"
        )
        for movie in movies
    )
    updated = escape(state.get("generated_at") or "尚未更新")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="自动更新的中国大陆院线电影定档日历">
  <title>中国大陆院线电影日历</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{ max-width: 880px; margin: 0 auto; padding: 48px 20px 80px; line-height: 1.6; }}
    h1 {{ line-height: 1.2; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 28px 0; }}
    .button {{
      display: inline-block;
      padding: 10px 16px;
      border-radius: 10px;
      background: #1677ff;
      color: white;
      text-decoration: none;
    }}
    .secondary {{ background: #555; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid #8885;
      text-align: left;
      vertical-align: top;
    }}
    .note {{ padding: 14px 16px; border-left: 4px solid #f0a000; background: #f0a00018; }}
    footer {{ margin-top: 36px; color: #777; }}
  </style>
</head>
<body>
  <main>
    <h1>中国大陆院线电影日历</h1>
    <p>国产片与进口片一并收录。订阅一次，新增定档与档期变化会自动更新。</p>
    <div class="actions">
      <a class="button" href="{escape(webcal_url)}">订阅 Apple 日历</a>
      <a class="button secondary" href="{escape(calendar_url)}">下载 ICS</a>
    </div>
    <p class="note">
      档期可能临时变化，请以片方或购票平台最新公告为准。
      当前数据来自豆瓣电影“即将上映”页面。
    </p>
    <h2>即将上映</h2>
    <table>
      <thead><tr><th>日期</th><th>片名</th><th>制片国家/地区</th><th>状态</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </main>
  <footer>最后生成：{updated} · 每日自动更新 · MIT 开源</footer>
</body>
</html>
"""


def write_index(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
