---
name: college-research
description: Use this skill when an agent needs to read a volunteer list Excel, research Chinese university hardware and campus life conditions, supplement with CollegesChat evidence, and produce a readable Excel research workbook.
---

# College Research

Use this skill to convert a user's volunteer-list workbook into `output/志愿院校硬件条件调研表.xlsx`. The agent gathers official public information; the scripts extract school names, collect CollegesChat evidence, merge fields, and generate Excel.

## Required Reading

Before acting, read:

1. `references/agent-workflow.md`
2. `references/data-contract.md`

## Operating Rules

- The input is an `.xlsx` volunteer table supplied by the user.
- Extract the school list first, keep the original order, and do not add schools that are not present in the user's table unless the user asks.
- Official fields such as level, city, campuses, and campus addresses must come from school or authority sources whenever possible.
- The old `宿舍地理位置` meaning is replaced by `校区具体地址`; write concrete campus addresses down to road and number when verified.
- Rename `周围商圈情况` to `生活条件`.
- Remove `CollegesChat命中状态`, `问卷证据概况`, `冲突提示`, and the `说明` sheet from the final workbook.
- CollegesChat is questionnaire evidence, not official school fact. Include the corresponding question text, answer summary, and month; do not keep answer IDs like `A34370`.
- If a fact cannot be found, leave the cell blank or mark it as `待补充/待核验`; do not infer.

## Script Workflow

Run commands from this skill directory.

```powershell
conda run -n base python scripts/run.py extract-schools --input input\志愿表.xlsx
```

The agent then researches official sources and writes `work/official_sources.json`.

```powershell
conda run -n base python scripts/run.py collect-collegeschat
conda run -n base python scripts/run.py merge
conda run -n base python scripts/run.py build-xlsx
conda run -n base python scripts/run.py validate
```

One-shot script phase after official sources are prepared:

```powershell
conda run -n base python scripts/run.py run --input input\志愿表.xlsx
```

## Output

The final workbook is `output/志愿院校硬件条件调研表.xlsx` with sheets:

- `汇总表`
- `原始摘录`
- `字段映射`

The summary cells should start with a compact human-readable conclusion, then show `近年问卷摘录（n条）` with question text and month for traceability.

## Verification

Before returning the file, run:

```powershell
conda run -n base python scripts/run.py validate
```

Validation should confirm sheet names, school count, deleted columns, and absence of CollegesChat answer IDs.
