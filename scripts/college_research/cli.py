from __future__ import annotations

import argparse
from pathlib import Path

from .collegeschat import collect_collegeschat
from .excel_input import extract_schools_from_xlsx
from .json_io import read_json, write_json
from .merge import build_dataset
from .paths import OUTPUT_DIR, WORK_DIR, ensure_dirs
from .report import build_workbook, validate_workbook


SCHOOLS_JSON = WORK_DIR / "schools.json"
OFFICIAL_JSON = WORK_DIR / "official_sources.json"
COLLEGESCHAT_JSON = WORK_DIR / "collegeschat_raw.json"
DATASET_JSON = WORK_DIR / "research_dataset.json"
OUTPUT_XLSX = OUTPUT_DIR / "志愿院校硬件条件调研表.xlsx"


def cmd_extract_schools(args: argparse.Namespace) -> None:
    ensure_dirs()
    schools = extract_schools_from_xlsx(Path(args.input))
    write_json(SCHOOLS_JSON, schools)
    print(f"提取学校 {len(schools)} 所 -> {SCHOOLS_JSON}")


def cmd_collect_collegeschat(_: argparse.Namespace) -> None:
    ensure_dirs()
    schools = read_json(SCHOOLS_JSON, [])
    if not schools:
        raise SystemExit("work/schools.json 为空，请先运行 extract-schools")
    data = collect_collegeschat(schools)
    write_json(COLLEGESCHAT_JSON, data)
    hit = sum(1 for row in data["fetch_log"] if row.get("page_url"))
    print(f"CollegesChat 命中 {hit}/{len(schools)} -> {COLLEGESCHAT_JSON}")


def cmd_merge(_: argparse.Namespace) -> None:
    ensure_dirs()
    schools = read_json(SCHOOLS_JSON, [])
    official = read_json(OFFICIAL_JSON, [])
    collegeschat = read_json(COLLEGESCHAT_JSON, {"raw_rows": []})
    dataset = build_dataset(schools, official, collegeschat.get("raw_rows", []))
    write_json(DATASET_JSON, dataset)
    print(f"合并完成 -> {DATASET_JSON}")


def cmd_build_xlsx(args: argparse.Namespace) -> None:
    ensure_dirs()
    dataset = read_json(DATASET_JSON, None)
    if dataset is None:
        raise SystemExit("work/research_dataset.json 不存在，请先运行 merge")
    output = Path(args.output) if args.output else OUTPUT_XLSX
    build_workbook(dataset, output)
    print(f"Excel 已生成 -> {output}")


def cmd_validate(args: argparse.Namespace) -> None:
    ensure_dirs()
    schools = read_json(SCHOOLS_JSON, [])
    output = Path(args.output) if args.output else OUTPUT_XLSX
    errors = validate_workbook(output, expected_schools=len(schools) if schools else None)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"验证通过 -> {output}")


def cmd_run(args: argparse.Namespace) -> None:
    cmd_extract_schools(args)
    cmd_collect_collegeschat(args)
    cmd_merge(args)
    cmd_build_xlsx(args)
    cmd_validate(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="college_research")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract-schools")
    extract.add_argument("--input", required=True)
    extract.set_defaults(func=cmd_extract_schools)

    collect = subparsers.add_parser("collect-collegeschat")
    collect.set_defaults(func=cmd_collect_collegeschat)

    merge = subparsers.add_parser("merge")
    merge.set_defaults(func=cmd_merge)

    build = subparsers.add_parser("build-xlsx")
    build.add_argument("--output", default="")
    build.set_defaults(func=cmd_build_xlsx)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--output", default="")
    validate.set_defaults(func=cmd_validate)

    run = subparsers.add_parser("run")
    run.add_argument("--input", required=True)
    run.add_argument("--output", default="")
    run.set_defaults(func=cmd_run)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
