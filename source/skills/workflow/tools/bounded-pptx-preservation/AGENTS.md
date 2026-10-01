# 可复用工具索引

- `restore_chart_dependencies.py --source SRC --authored DRAFT --out-dir NEW`：仅恢复通过自动验证的原静态图表依赖，输出待验候选，不能代替文字作者
- `finalize_restoration.mjs --source SRC --authored DRAFT --out-dir NEW --requirements JSON`：同次执行自动保全与当前 Presentations 严格 finalizer，产物为 `NEW/output/final.pptx`
- `tests/`：有界正反例与 CLI/I/O 失败验证

原作者必须为当前 Presentations 要求的 Artifact Tool；不修改任何系统库。静态单图表、单表五部件工作簿是当前支持边界，不能弱化失败条件以让未知输入通过。商业成品与已发布技能保持只读。中间产物放 tmp/，实际复现证据保留于 evidence/。
