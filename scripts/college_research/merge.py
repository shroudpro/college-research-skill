from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import load_campus_address_overrides


FINAL_FIELDS = [
    "生活条件",
    "有无空调",
    "宿舍几人间",
    "有无独立卫浴",
    "有无早晚自习",
    "有无早操",
    "宵禁情况",
    "到点是否断电断网",
]


def clean(value: Any) -> str:
    return str(value or "").strip()


def official_by_school(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    return {clean(row.get("school")): {str(k): clean(v) for k, v in row.items()} for row in rows if clean(row.get("school"))}


def key_summary(field: str, excerpts: list[dict[str, str]]) -> str:
    text = "；".join(row.get("excerpt", "") for row in excerpts)
    parts: list[str] = []
    if field == "生活条件":
        if "外卖" in text:
            parts.append("外卖情况见摘录")
        if any(word in text for word in ["地铁", "公交", "市区", "交通"]):
            parts.append("交通情况见摘录")
        if any(word in text for word in ["超市", "食堂", "便利"]):
            parts.append("生活配套见摘录")
    elif field == "有无空调":
        if "宿舍有" in text or "空调" in text:
            parts.append("空调配置见摘录")
    elif field == "宿舍几人间":
        if "上床下桌" in text:
            parts.append("上床下桌情况见摘录")
    elif field == "有无独立卫浴":
        if any(word in text for word in ["无独立", "没有独立"]):
            parts.append("独卫情况见摘录")
        if any(word in text for word in ["澡堂", "浴室"]):
            parts.append("洗澡距离见摘录")
    elif field == "有无早晚自习":
        parts.append("早晚自习要求见摘录")
    elif field == "有无早操":
        parts.append("晨跑/跑步打卡见摘录")
    elif field == "宵禁情况":
        parts.append("门禁/查寝/晚归见摘录")
    elif field == "到点是否断电断网":
        parts.append("断电断网/限电见摘录")
    return "-".join(parts) if parts else "关键信息见摘录"


def readable_field(field: str, rows: list[dict[str, str]], max_items: int = 4) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda row: row.get("date", ""), reverse=True)
    seen: set[tuple[str, str]] = set()
    picked: list[dict[str, str]] = []
    for row in rows:
        key = (row.get("question", ""), row.get("excerpt", "")[:50])
        if key in seen:
            continue
        seen.add(key)
        picked.append(row)
        if len(picked) >= max_items:
            break
    excerpts = "；".join(
        f"{row.get('question', '')}：{row.get('excerpt', '')}（{(row.get('date') or '日期未知')[:7]}）"
        for row in picked
    )
    return f"{key_summary(field, rows)}；近年问卷摘录（{len(rows)}条）：{excerpts}"


def build_dataset(
    schools: list[str],
    official_rows: list[dict[str, Any]],
    collegeschat_rows: list[dict[str, str]],
) -> dict[str, Any]:
    official_map = official_by_school(official_rows)
    address_overrides = load_campus_address_overrides()
    chat_by_school_field: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in collegeschat_rows:
        chat_by_school_field[(row.get("school", ""), row.get("field", ""))].append(row)

    summary_rows: list[dict[str, str]] = []
    for school in schools:
        official = official_map.get(school, {})
        address_override = address_overrides.get(school, {})
        campus_addresses = official.get("campus_addresses") or address_override.get("campus_addresses", "")
        source_parts = [
            official.get("source", ""),
            address_override.get("source", "") if campus_addresses == address_override.get("campus_addresses", "") else "",
        ]
        row = {
            "大学": school,
            "大学层次": official.get("level", ""),
            "地理位置": official.get("location", ""),
            "分校区情况": official.get("campuses", ""),
            "校区具体地址": campus_addresses,
            "信息来源": "；".join(part for part in source_parts if part),
            "CollegesChat页面": "",
        }
        for field in FINAL_FIELDS:
            rows = chat_by_school_field.get((school, field), [])
            row[field] = readable_field(field, rows)
            if rows and not row["CollegesChat页面"]:
                row["CollegesChat页面"] = rows[0].get("page_url", "")
        summary_rows.append(row)

    raw_rows = [
        {
            "大学": row.get("school", ""),
            "字段": row.get("field", ""),
            "问题": row.get("question", ""),
            "时间": (row.get("date") or "")[:7],
            "摘录": row.get("excerpt", ""),
            "CollegesChat页面": row.get("page_url", ""),
        }
        for row in collegeschat_rows
    ]

    return {"summary_rows": summary_rows, "raw_rows": raw_rows}
