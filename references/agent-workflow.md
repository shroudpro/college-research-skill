# 联网 Agent 工作流

本 skill 假设 agent 只有联网检索能力，没有浏览器插件、没有默认 skills。脚本负责确定性处理，agent 只负责公开信息检索和补证据。

## 1. 输入

用户把志愿表 `.xlsx` 放入 `input/`。

先运行：

```powershell
conda run -n base python scripts/run.py extract-schools --input input\志愿表.xlsx
```

读取：

```text
work/schools.json
```

## 2. 检索官方公开信息

对 `work/schools.json` 中每所学校检索：

- 大学层次
- 地理位置
- 分校区情况
- 校区具体地址，尽量精确到“xx路xx号”
- 官方来源 URL

优先级：

1. 学校官网：学校简介、学校概况、招生网、官网页脚。
2. 学校官方招生章程、新生入学须知。
3. 教育主管部门或学校官方微信公众号文章。
4. 其他来源只能作为线索，不直接写成确定事实。

## 3. 写入 `work/official_sources.json`

格式必须是数组：

```json
[
  {
    "school": "青岛大学",
    "level": "公办综合类本科；山东省属重点高校",
    "location": "山东省青岛市",
    "campuses": "浮山校区、金家岭校区、松山校区",
    "campus_addresses": "浮山校区：山东省青岛市崂山区宁夏路308号；金家岭校区：山东省青岛市崂山区松岭路93号；松山校区：山东省青岛市市北区登州路38号",
    "source": "https://www.qdu.edu.cn/xxgk/xxjj.htm"
  }
]
```

规则：

- 不确定就留空。
- 多校区地址用 `；` 分隔。
- 不要把第三方问答写进官方来源字段。
- 不要写“据说”“可能”等未核实词。

## 4. 运行脚本化流程

```powershell
conda run -n base python scripts/run.py collect-collegeschat
conda run -n base python scripts/run.py merge
conda run -n base python scripts/run.py build-xlsx
conda run -n base python scripts/run.py validate
```

## 5. 质量检查

交付前确认：

- `汇总表` 学校数量等于 `work/schools.json` 学校数量。
- `说明` sheet 不存在。
- 不存在 `CollegesChat命中状态`、`问卷证据概况`、`冲突提示` 三列。
- 单元格内不出现 `A34370` 这类答卷 ID。
- 每条问卷摘录有问题文本和月份，例如 `有独立卫浴吗？：无独立卫浴（2026-06）`。
