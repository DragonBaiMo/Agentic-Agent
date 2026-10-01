# 可复用工具索引

## native-typography-1 兼容修复

- `scripts/pptx_backend/render_objects.mjs`仅对structured text先赋默认样式、再保留run覆盖；段落局部倍率/固定pt优先，缺省继承整体行距。普通字符串/字符串数组、PSD与图片路径不变
- `examples/pptx-native-typography.json`用现有`assemble_pptx.mjs`真实构建三页功能回归，含中文/英文/数字混排、渐变描边、不同多行间距和旧字符串对照；不是商业设计模板
- `tests/pptx.test.cjs`覆盖赋值顺序、局部间距优先、输入不变和旧调用契约；实际导出与目标应用证据分别记录。字段单位、清除描边与已观察失败见`references/native-style-tokens.md`

## native-first-roles-1 兼容扩展

- `scripts/pptx_project.py`保留旧入口，新增`text_styles`/`style_role`解析与纯色背景验证；`scripts/pptx_backend/contract.py`是唯一实现。未知角色和无效核心样式定位页/对象/角色/字段
- `examples/pptx-native-roles.json`是无外部素材的两页合成回归输入，复制为项目deck.json后用现有`assemble_pptx.mjs`构建；不代表商业视觉模板
- `references/native-style-tokens.md`说明单位、覆盖顺序、完整状态重设、字体/长文与能力证据；`tests/test_native_roles.py`覆盖兼容、拒绝与输入不变
- `semantics.py`在没有background PNG时保留公开API写出的纯色母版；旧PNG母版、fixed_layout与所有PSD工具不变，不创建额外绘图后端

## 1.4.1-rc.3 有界原依赖保全

- `tools/bounded-pptx-preservation/finalize_restoration.mjs --source SRC --authored ARTIFACT_DRAFT --out-dir NEW --requirements JSON`：同次自动证明单原生barChart与五部件inline静态xlsx的对应关系，只恢复原依赖，再严格finalizer与原子发布；原文件只读
- 同目录`restore_chart_dependencies.py`：只输出待验证候选；`bounded_pptx/`为公共证明/恢复实现，`tests/`含正常、拒绝、I/O及包装器失败测试
- 精确支持和拒绝边界见同目录README.md。它不替代现有商业入口，不承担文字作者；其他图表/工作簿结构仍走当前Presentations分析与明确阻断，不放宽检查

## 1.4.0 滚动调度

- `scripts/schedule.py --project PROJECT init/next/return/register/adopt/fail/recover/reconcile/status/report`：原生工具宿主的持久DAG/单写者登记入口，payload 契约见 `references/rolling-scheduling.md`，不会调用模型
- `scripts/scheduling/`：公开 API `Coordinator`、`run`；有 Python 异步工具适配器时按依赖滚动执行，返回立即保存，视觉检查与结果登记解耦；未知超时不重发
- `scripts/benchmark_schedule.py --out NEW_REPORT.json`：可重复的本地调度基准；模拟延迟不是图片服务实测速率
- `tests/test_scheduling*.py`：真实状态/文件/并发/恢复、计时与原生命令接口的正负用例

原有 PSD/PPTX 生产工具与验证不变。协调器活动时共享 receipts/deck/data 只能单写者修改；先记录结果再作长视觉判断。不要把本地基准或客户端在途数写成服务端并行。

## 1.3.0 PPTX 新增

- `scripts/verify_protected_media.py --project PROJECT --plan deck.json --pptx builds/B01/final.pptx --out evidence/media.json`：指定静态PNG的只读字节/页身份/contain几何校验；支持与拒绝条件见`references/protected-png.md`。不作者写入、不自动发布、不支持视频；测试`tests/test_protected*.py`

- `scripts/image_job.py prepare/record`：准备逐页真实参考和纯视觉正文；登记真实模型返回，复用 execution_record，不调用模型
- `scripts/crop_alpha.py`：透明语义素材紧裁并记录源/裁剪/目标框和位置补偿；见 pptx-tools
- `scripts/pptx_project.py`：编译 deck.json 与 data.json，拒绝过期艺术标签，输出局部替换任务
- `scripts/pptx_backend/contract.py`：路径/对象/数据约束公共实现；不执行表达式、不自动批准艺术图
- `scripts/assemble_pptx.mjs`：调用当前 Presentations 的真实 JavaScript API、finalizer 与导出回读渲染
- `scripts/pptx_backend/build_paths.mjs`：组装入口内部先核并独占新建 builds/tmp/evidence 同名空间；旧回执或中间文件不覆盖，测试 `tests/build_paths.test.cjs`
- `scripts/pptx_backend/render_objects.mjs`：按资源定位独立图片/原生文字/图表/表格；不绘制装饰图形
- `scripts/pptx_backend/semantics.py`：对本构建器新导出的包写语义名称、真实共用背景母版与页级固定版式
- `scripts/verify_pptx_edits.mjs`：编辑真实 PPTX 测试副本、保存重开；不把诊断副本作为正式交付
- `scripts/pptx_backend/verify_table_edits.mjs`：上述入口内部的普通矩形表逐格读回，检查目标、未改格和维度；测试 `tests/verify_table_edits.test.cjs`
- `scripts/pptx_backend/inspect_plain_tables.py SOURCE.pptx ACTIONS.json`：只读识别实际页关系/目标表，拒绝合并与歧义表的自动单格诊断；测试 `tests/test_plain_table_guard.py`，不修改PPTX内容
- `tests/test_pptx_support.py`：新数据契约、裁边和图片任务的正负用例

PSD 原命令与数据契约保持不变。内容/文案先加载同级或已安装 consumer-first-writing。PPTX 新开发先加载当前 Presentations，按其当前 API/运行时执行，不硬编码开发机路径。

## PSD 既有工具

- `scripts/project.py`：doctor/init/status/snapshot/restore/compile；开始和续做新项目
- `scripts/project_io.py`：路径隔离、原子 JSON、plan 到 manifest 共享逻辑
- `scripts/visual_job.py`：按 plan 导出一张图的 DRAW/reference/request，不调用模型
- `scripts/record_asset.py`：保存真实生成/上传/历史素材，登记来源和失败状态
- `scripts/execution_record.py`：record_asset 内部复用；白名单保存真实调用的公开正文/附件身份/透明参数，不推断后台绑定
- `scripts/environment_check.py`、`scripts/doctor.cjs`：project.py doctor 内部复用；只读检查实际运行时、公开包名加载、同一解析包的版本元数据和所选字体路径；Node加载/版本未知/版本匹配分别报告
- `scripts/measure_text.cjs`：`node scripts/measure_text.cjs --config manifest.json --layer 原生层名 [--target-width 像素]`；测真实逐字 advance 与可选 tracking，不改配置
- `scripts/review_assets.py`：gallery/viewer/move，候选与真实图层诊断
- `scripts/deliver_project.py`：final/review/diagnostic 源包、CRC/哈希验证

- `scripts/assemble.cjs`：`node scripts/assemble.cjs --config examples/future-lab.json --out output/demo`，真实 PSD 和预览
- `scripts/probe_assets.py`：`python scripts/probe_assets.py image.png`，只读尺寸和 Alpha；输出 alpha_bbox_comparison 说明严格大于阈值，边界测试 `tests/test_alpha_thresholds.py`
- `scripts/verify_psd.py`：独立技术验证；参数见 `references/manifest.md`
- `scripts/review_psd.py`：验证器内部复用的实际图层合成/对照/隐藏视图，不直接调用模型
- `tests/contract.test.cjs`、`tests/render.test.cjs`、`tests/test_verify.py`：维护者回归测试
- `tests/test_project.py`：初始化、来源、角色过滤、拒收、恢复与诊断包
- `tests/test_production_support.py`、`tests/measure_text.test.cjs`：材质模板路由、Alpha 分布、公开调用记录、环境失败路径、行宽计算
- `tests/test_pipeline.py`：真实旧素材经新项目桥接、构建、独立解析、审阅导出与源包

业务文字和诊断字符串存于配置、resources。依赖锁定。临时文件放 `tmp/`，不打包 node_modules、虚拟环境、密钥、字体或用户未要求的图片。不要为艺术质量新增代码门禁；测试只保证打包能力。修改后同步维护本索引和变更说明。
