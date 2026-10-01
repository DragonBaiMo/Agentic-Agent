# PPTX 工具、调用与恢复

以下命令从 workflow 根目录执行。PROJECT 是独立工程绝对路径。工具只处理已有文件或准备调用，图片必须由当次可用的真实模型工具生成。

多页/多素材先按 [滚动调度](rolling-scheduling.md) 建最小依赖计划。schedule.py 管领取、逐项返回、串行登记和恢复；原 image_job.py 单项命令仍兼容。调度运行时由协调器统一调用登记，不另开写者修改同一 receipts.json。

## 1．准备一张完整页或语义层

先写 PROJECT/jobs.json，任务样式见 examples/new-deck-jobs.json。完整页参考已批准的方向和共用组件；提层参考当前页完整母图。正文写在 prompt，不给图片模型提交测试日志和目录规划。

```bash
python scripts/image_job.py prepare --project "$PROJECT" --task S01-master --out jobs/S01-master-01
```

输出 DRAW.txt、真实复制的 reference-N 文件、request.json。输出目录须全新。实际打开 DRAW 和参考图，再按 tools-and-prompts 的当前图片工具 schema 调用；新图无参考就不传参考参数，编辑用实际可读图路径和透明参数。不能把准备命令当模型调用。

每次完整页/编辑使用低噪精确要求，见 prompts/pptx-design.txt、pptx-layer.txt。失败只修当前责任层；一张母图含错刻度，不必重新生成整套。

## 2．登记真实返回

```bash
python scripts/image_job.py record --project "$PROJECT" --task S01-master \
  --source /actual/result.png --origin generated --tool ACTUAL_TOOL \
  --job jobs/S01-master-01 --call-id ACTUAL_CALL_ID \
  --execution /actual/public-arguments.json
```

--call-id 未暴露时省略。--execution 可选，格式沿用 tools-and-prompts 的三字段白名单：真实 prompt、referenced_image_paths、transparent_background；未见公开参数就省略，不猜。登记保存实际文件和来源，返回 assets/ 下带哈希的相对路径；采用后再把该路径写入对应 mother/element 引用。失败加 `--status rejected --reason "具体原因"`，不会替换已采用资产。登记单人串行，独立生图可按宿主许可并行。

## 3．紧裁透明边界

```bash
python scripts/crop_alpha.py --input "$PROJECT/assets/title.png" \
  --output "$PROJECT/cropped/title-v1.png" --target 0 0 1600 900 \
  --threshold 1 --padding 6 --ledger "$PROJECT/crop-ledger/title-v1.json"
```

target 是原整张源图在目标页的 xywh，不是图中可见物体框。需要从同一已透明语义图取独立区域时可加 --region X Y W H；只有确实独立且无背景残留的对象才适合这样取。输出 target_xywh 用于新 PNG 的 element.box。查看软边和 discarded_alpha_mass，阈值不是审美保证。

crop 的 threshold 使用 Alpha >= threshold，默认 1 包含全部非零像素；probe 的 alpha_bbox 键使用 Alpha > threshold，输出另有 alpha_bbox_comparison 标注。比如 probe 的键 "1" 对应 crop 的 threshold 2，而不是 1。先核比较符再判断空白边界；不要为缩小选框自动提高阈值，也不要裁剪要求保留完整画布的指定原图。

## 4．编译与组装

可先只检查资源/数据：

```bash
python scripts/pptx_project.py --project "$PROJECT" --plan deck.json --out builds/check-01/compiled.json
```

正式组装使用新 build 名，自动做同样检查、构建、调用当前 Presentations finalizer 和实际回读渲染：

```bash
"$RUNTIME_NODE" scripts/assemble_pptx.mjs --project "$PROJECT" --plan deck.json \
  --build B01 --presentations-skill "$PRESENTATIONS_SKILL_DIR"
```

先按当前 Presentations 设置 RUNTIME_NODE、RUNTIME_NODE_MODULES、RUNTIME_BIN_DIR、RUNTIME_PYTHON。PRESENTATIONS_SKILL_DIR 来自实际读取到的 Skill 根目录，不是本包。构建器不安装依赖，也不提供 API 凭证。输出 builds/B01/final.pptx、slide-N.png、inspect.ndjson、compiled.json；验证报告在 evidence/B01/validation.json；tmp/B01 保留草稿直至验证结束，随后只清理本次临时文件。

该后端针对本流程新建 deck，不接收任意用户已有 PPTX 作为 OOXML 改写对象。编辑已有原生 deck 时按当前 Presentations 正式导入/编辑流程，先保护原文件。

需要保全指定PNG时，在严格finalizer之后、交付之前，按[原件与槽位核验](protected-png.md)另运行verify_protected_media.py。它读取已完成的PPTX，证明声明过的普通图片原字节和contain框；不是作者工具，也没有自动接入本构建器。拒绝复杂变换时只暂停这项自动证明，保留原文件并选择能核实的原生路线，不能默认栅格化。

## 5．真实编辑副本

从实际 inspect 中选择唯一对象，准备 edit-actions.json：actions 里的 kind=image/textbox/chart/table、slide（1 起）、name（图表/表格唯一时可省略）；给图片 left、文字 text、图表 series/values、表格 row/column/text。render_indices 为从 0 起的待检查页索引，expected_text 为编辑后应存在的文字。

表格的 row/column 从0起，可加 expected_before 防止改到陈旧报价。同批actions重复指定同一格会在修改前以duplicate_table_cell_target拒绝；每格保留一个最终目标，不推断顺序编辑语义。脚本只对无合并的矩形表自动校验：先只读检查实际PPTX中的目标表结构，再通过当前公开getCell逐格读回，记录原值、目标值和重开值，并核对未改格与行列数。inspect里的表格preview可能只有首行，不能拿它搜索非首行报价来判定成败。表格分支使用当前宿主的RUNTIME_PYTHON（或CODEX_PRIMARY_RUNTIME_PYTHON）运行只读结构检查，不安装额外生产依赖。

若目标表含合并格，返回带页码/表名的merged_table_requires_visible_structure_review，停止这个自动单格诊断分支。被覆盖格可能存着正确数字却根本不显示，不能只凭getCell成功就通过。按当前Presentations支持的原生编辑方式核实实际可见合并范围和文字归属，再决定具体修改；不默认栅格化、拆散表或阻断整份PPT制作。空字符串和带前导零字符串在普通矩形表的实际回读已验证，不推导为任意富文本、合并语义、单元格样式或桌面应用都可无损往返。

```bash
"$RUNTIME_NODE" scripts/verify_pptx_edits.mjs --project "$PROJECT" \
  --input builds/B01/final.pptx --actions edit-actions.json --out review/B01-edit
```

输出实际修改再打开的诊断图、检查快照与结果，源文件不动。图片移动仅说明对象可编辑，不证明真实鼠标点击行为。诊断重导出可能丢失 chart workbook，正式交付不能使用这个副本；正式文件由 finalizer 写出并保留所需工作簿。

表格逐格文字验证不替代版式/样式/原图对照。本轮报价fixture在结构比较中只有一个a:t变化，其他11格、表格格式/几何和指定原图字节/放置保留；这是该实测文件的结论，不是对所有PPTX的保全保证。

## 6．错误处理

| 实际问题 | 恢复动作 |
|---|---|
| 缺 consumer/Presentations/指定运行时 | 报缺项和受影响阶段；不虚构安装位置或使用证据 |
| reference_missing / outside_project | 核对实际项目内副本和授权来源，更新路径；不能绕过访问拒绝 |
| job_exists / output_exists | 用新任务/版本目录，不覆盖来源或旧证据 |
| stale_art_labels | 读 pending-art-replacements，局部更新数值艺术图并核对，再更新绑定 |
| 图像不透明、背景残留或软边断裂 | 修该语义素材，保留原件，不用高阈值硬切掩盖 |
| 图表零点或数据不准 | 修唯一数据源与原生 chart 配置，重新渲染，不沿用母图错误 |
| 字体重排/错位 | 确认真实字体与样式、框和间距；艺术文字不够接近时保留图片 |
| native/chart/table/workbook 验证失败 | 读具体报告，查配置和公开 API；不关闭检查冒充通过 |
| 传输中断、工具状态未知 | 保存确定完成项，先有界只读核验；不猜写入成功、不盲重试可能已完成的外部调用 |

一处视觉问题先做有依据的局部修复，默认最多两次同方法尝试。没有新依据就换已授权方法或报告缺口；这不是每页强制两轮。用户反馈拒绝整体审美时回完整代表页和视觉系统，技术通过不能当艺术验收。
