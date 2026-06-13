from __future__ import annotations

import html
import re
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from .config import load_field_mapping, load_slug_overrides


BASE_URL = "https://colleges.chat"
RAW_BASE = "https://raw.githubusercontent.com/CollegesChat/university-information/generated/docs/universities"
HEADERS = {"User-Agent": "Mozilla/5.0"}


@dataclass
class ChatAnswer:
    school: str
    field: str
    question: str
    answer_id: str
    date: str
    excerpt: str
    page_url: str


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


def fetch_text(url: str, timeout: int = 25) -> tuple[int, str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.encoding = response.apparent_encoding or response.encoding
        return response.status_code, response.text
    except requests.RequestException as exc:
        return 0, str(exc)


def normalize_school_name(name: str) -> str:
    return re.sub(r"\s+", "", name).replace("（", "").replace("）", "").replace("(", "").replace(")", "")


def parse_nav_slugs(page: str) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for match in re.finditer(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', page, flags=re.I | re.S):
        href, label_html = match.groups()
        parsed = urlparse(urljoin(f"{BASE_URL}/universities/qing-dao-da-xue/", html.unescape(href)))
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2 or parts[0] != "universities":
            continue
        label = clean_text(html.unescape(strip_tags(label_html))).replace(" ", "")
        if not label:
            continue
        mapping.setdefault(label, [])
        if parts[1] not in mapping[label]:
            mapping[label].append(parts[1])
    return mapping


def slug_candidates(school: str, nav: dict[str, list[str]]) -> list[str]:
    overrides, aliases = load_slug_overrides()
    names = [school] + aliases.get(school, [])
    normalized = {normalize_school_name(name) for name in names}
    candidates: list[str] = []
    for label, slugs in nav.items():
        if normalize_school_name(label) in normalized:
            candidates.extend(slug for slug in slugs if slug not in candidates)
    candidates.extend(slug for slug in overrides.get(school, []) if slug not in candidates)
    return candidates


def parse_source_dates(markdown: str) -> dict[str, str]:
    dates: dict[str, str] = {}
    for line in markdown.splitlines():
        id_match = re.search(r"\b(A\d{4,6})\b", line)
        if not id_match:
            continue
        date_match = re.search(r"(20\d{2})\s*[年/\-.]\s*(\d{1,2})\s*(?:[月/\-.]\s*(\d{1,2}))?", line)
        if date_match:
            year, month, day = date_match.groups()
            dates[id_match.group(1)] = f"{int(year):04d}-{int(month):02d}-{int(day or 1):02d}"
    return dates


def match_field(question: str, mapping: dict[str, list[str]]) -> str | None:
    for field, keywords in mapping.items():
        if any(keyword in question for keyword in keywords):
            return field
    return None


def parse_answers(school: str, page_url: str, markdown: str) -> list[ChatAnswer]:
    mapping = load_field_mapping()
    source_dates = parse_source_dates(markdown)
    answers: list[ChatAnswer] = []
    current_question = ""
    current_field: str | None = None
    current_id = ""
    current_text = ""

    def flush() -> None:
        nonlocal current_id, current_text
        if current_field and current_id and clean_text(current_text):
            answers.append(
                ChatAnswer(
                    school=school,
                    field=current_field,
                    question=current_question,
                    answer_id=current_id,
                    date=source_dates.get(current_id, ""),
                    excerpt=clean_text(current_text)[:220],
                    page_url=page_url,
                )
            )
        current_id = ""
        current_text = ""

    for line in markdown.splitlines():
        heading = re.match(r"^##\s+(?:Q:\s*)?(.+?)\s*$", line)
        if heading:
            flush()
            current_question = heading.group(1).strip()
            current_field = match_field(current_question, mapping)
            continue
        bullet = re.match(r"^\s*[-*]\s+(A\d{4,6})\s*[：:]\s*(.*)$", line)
        if bullet:
            flush()
            current_id = bullet.group(1)
            current_text = bullet.group(2)
            continue
        if current_id and line and not line.startswith("#"):
            current_text += " " + line.strip()
    flush()
    return answers


def html_to_markdownish(page: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.I | re.S)
    text = re.sub(r"<h[12][^>]*>", "\n## ", text, flags=re.I)
    text = re.sub(r"</h[12]>", "\n", text, flags=re.I)
    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.I)
    text = re.sub(r"</li>", "\n", text, flags=re.I)
    return html.unescape(strip_tags(text))


def fetch_school_markdown(school: str, nav: dict[str, list[str]]) -> tuple[str, str, str]:
    for slug in slug_candidates(school, nav):
        raw_url = f"{RAW_BASE}/{slug}.md"
        status, text = fetch_text(raw_url)
        if status == 200 and text.lstrip().startswith("#"):
            return slug, f"{BASE_URL}/universities/{slug}/", text
        page_url = f"{BASE_URL}/universities/{slug}/"
        status, page = fetch_text(page_url)
        if status == 200 and "Q:" in page:
            return slug, page_url, html_to_markdownish(page)
    return "", "", ""


def collect_collegeschat(schools: list[str], delay_seconds: float = 0.25) -> dict[str, object]:
    status, nav_page = fetch_text(f"{BASE_URL}/universities/qing-dao-da-xue/")
    nav = parse_nav_slugs(nav_page) if status == 200 else {}
    raw_rows: list[dict[str, str]] = []
    fetch_log: list[dict[str, str]] = []

    for school in schools:
        slug, page_url, markdown = fetch_school_markdown(school, nav)
        if markdown:
            answers = parse_answers(school, page_url, markdown)
            raw_rows.extend(asdict(answer) for answer in answers)
            fetch_log.append({"school": school, "slug": slug, "page_url": page_url, "answers": str(len(answers))})
        else:
            fetch_log.append({"school": school, "slug": "", "page_url": "", "answers": "0"})
        time.sleep(delay_seconds)

    return {
        "generated_at": date.today().isoformat(),
        "raw_rows": raw_rows,
        "fetch_log": fetch_log,
    }
