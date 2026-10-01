# 两个源包 → 1.0 问题 → 1.1 恢复映射

这是 1.1.0 对来源的历史审计，不是 1.2.0 的交互默认。当前保留母版与图层架构两个可合并节点，明确全自动则自主继续；见 interaction-and-layers.md。本表的能力均保留，当前新增项见变更与验证.md。

## 诊断结论

1.0 并非完全没有功能：已保留真实 PSD 组装、两类文字、可调位置、独立解析、隐藏视图和视觉容错。问题在于它把“去掉阻碍工作的门禁”错误扩大成“删掉生产协调与具体操作说明”。主入口只有高层动作，随后直接给 Future Lab 的固定重建命令，新的 AI 必须自行发明“需求怎样变成计划/素材/配置”这座桥。

具体缺口是可检验的：新任务没有初始化/导入/请求/登记/编译路径；没有明确每阶段文件与前进条件；多候选、暂停续做、回退、来源保存、移动诊断、可切换本地审阅页、工程打包没有对应可执行入口。把这些说成“减少门禁”不成立。此前代码测试通过证明的是包装器可运行，不能证明另一位 AI 能独立执行完整生产。

此次检查的是三个实际 ZIP，不用文件数量或字数代替语义审计：LayerForge 3.1.0、build-layered-poster、实际交付的 workflow 1.0.0。原 ZIP 和旧版本均保留。以下 L 指 layerforge-psd/，B 指 build-layered-poster/，W 指本包。

## 能力逐项映射

| 来源职责与证据文件 | 1.0 实际情况 | 1.1 的可用路径与处理 |
|---|---|---|
| L workflow/workflow.yaml：single_design、candidate_gallery、existing_design | 已有图/新图被一句话提及；多候选没有工作路径 | SKILL 第 0/2 阶段明确入口，new-poster.plan、gallery、master 登记 |
| L references/cli.md init/status；B workflow.md 交付契约 | 无新工程入口，只能修改旧例图 JSON | project.py init/status；project-contract 给输入和输出数据流 |
| L brief.schema、SKILL 完整含字设计 | 原则保留，原生预排如何接入不清 | 阶段 1/2、new-task-walkthrough 的完整候选分支；艺术中间图不得充当最终分层背景 |
| L review-design/select/gallery | 只说保留基准，缺候选选择操作 | 真实候选保留，编号画廊；按 interaction 选择，用历史来源登记切换 master |
| L interaction、authorize/decide | 取消卡点方向正确，但确认选项未成契约 | autonomous/master_only/staged + stop_at；保留真实授权与看图批准区别，无强制 A/B/C 票据 |
| L plan.schema、contracts：语义所有权、copy_ids | 有类型描述，没有完整计划到执行的对应 | plan.layers、project-contract、compile_plan；图片文案只取所属角色，native 从 copy_id 取原文 |
| L 七类语义 | 已保留 kind，缺生成层面的操作深度 | 第 3/4 阶段明确用途、excludes、遮挡、文字归属；不强制七类齐全 |
| L geometry：主体框/效果框/xyxy | 只保留笼统视觉定位；未提示旧坐标转换 | target_box/effect_box 用 xywh，显式说明 xyxy 转换及 crop/destination 含义 |
| L 原位 identity 与 B crop/destination | 已支持微调；这一点应保留 | 同画布优先、等比优先、允许轻量注册；不恢复“不许移动一像素”的门禁 |
| L 玻璃/阴影/弱 Alpha 与 B alpha probe | 规则和探测器保留 | 继续保留，补充源图/目标透明性区别、材质范围与恢复动作 |
| L 背景/遮挡补全 | 保留一句原则 | 第 3/4 阶段及背景/层提示模板明确补全、前后拆分、推断边界 |
| L requests、prompts/design/layer、copy 过滤 | 仅文档中的几段例句，缺可调用模板 | prompts/design.txt、background.txt、layer.txt；visual_job 按计划生成 DRAW，实际角色过滤 |
| L export_visual_job、capsule | 完全移除最小图像任务导出 | visual_job 输出 DRAW/reference/request；明确准备不等于模型已调用 |
| L host-bridge、bind-dispatch | 有通用工具说明，无关联请求文件的实际过程 | 实际引用文件与哈希进入 request，当前宿主 schema 由执行者使用；真实后台绑定不可见仍记不可见 |
| L register/registry | 无来源登记工具，只有历史例子 | record_asset：immutable 素材、来源/调用 ID、请求正文、真实尺寸/哈希；失败不替换 active |
| L conversation_history | 1.0 未提供恢复登记路径 | origin=user_supplied/generated/conversation_history，历史不冒充新调用；未知 Prompt 不补造 |
| L capability probe / reset-probe | 只剩“两次重试”概念 | 恢复表明确排查实际 schema/引用/透明、改变假设再试；保留失败，不使用换 ID 无限刷重试 |
| L diagnose/repair-finish/rollback | 只有局部修复口号 | snapshot/restore 保留计划/来源指针和原料；新构建 B02；原因→责任动作故障表 |
| L pause/resume、state 持久化 | 无状态组织与续做操作 | plan/resume_note/receipts/status，明确下一步；没有复刻互锁状态机 |
| B 原生文字与字体 | 已保留，是 1.0 的有效能力 | 继续保留；plan native_text 可编译，复杂文字边界明确，不能替代图片艺术字 |
| B 图片形态文字路径 | 后端可用，但新项目例子不明显 | 香水示例同时包含图片艺术标题、瓶身图片标签、native caption，整个流程不混淆 |
| B Node 分组/文字缓存/组装器 | 保留并扩展 blend/opacity/z/hidden | 后端不重写；新项目桥接到同一个已测试 assembler |
| L normal/screen/multiply/overlay | 1.0 已恢复四种 | 继续保留，不维护两套互相不一致的 PSD writer |
| B 双解析器、真实重建 | 已保留，取消 MAE 艺术门槛正确 | 继续基础检查，按层身份核对 native 文字；技术通过不等于看图批准 |
| L inspect-views、B toggle | 只保留隐藏，删除移动 | verify_psd 的 toggle + review_assets move；只动诊断内存，不改生产 PSD |
| L review-page、tools/artifact_views、review.html | 删除 | 复用原包审阅页面资源；review_assets 从实际 PSD 导出图层和本地 HTML。初始全层可见与最终显隐区别已注明 |
| L evaluation 三维度 | 1.0 部分保留，但没有操作对应 | 设计观感、重建/语义、交付/编辑能力分开；第 6 阶段列实际观察与可选工具 |
| L delivery：final/review/diagnostic、哈希/CRC | 只说“交付 PSD 和预览” | deliver_project 三模式；START_HERE 模板，选中素材/计划/来源/配置，CRC 和字节哈希 |
| L handoff、B local-execution | 没有统一工程树与接手顺序 | SKILL 工程树，recovery-and-handoff，stage 输入/动作/输出/前进条件 |
| L replay_design、B 例图重建 | 历史重建成为唯一具体执行样例 | 重建继续可用，但主入口区分 replay；新任务用 plan 初始化并编译，不冒称复刻原生图成功 |
| B Future Lab 案例、实际四次提示词 | 素材和提示词留存，案例理由压缩 | 保留真实案例/历史提示词与资产；明确历史无字参考不等于新版推荐完整母图 |
| 两包不冒充 Photoshop/Adobe 能力 | 已保留 | 继续保留；权限拒绝、字体依赖、应用验证范围写入交接 |
| L 严格签票、逐层 pass/unknown 门禁 | 删除 | 不恢复阻碍性的逐层机器批准；用户要求的确认由 interaction 保留 |
| L 全图/局部 SSIM、edgeF1、直方图与 B MAE 阈值 | 删除默认评分 | 不恢复自动艺术评分；如用户明确要求数值研究可另外做诊断，不能替代看图或拖延交付 |

## 兼容与明确没有恢复的东西

1.1 是 workflow 的功能修订，不兼容 LayerForge 的原 25 条 CLI 命令名或 state 数据结构；表中是职责映射，不冒称 API 原封不动。旧用户工程应保留副本，按 project-contract 迁移实际素材/计划。build-layered-poster 的组装配置继续直接可用。

没有增加真实蒙版、智能对象、复杂 native 排版或 Photoshop API；源包本来也没有提供全部这些能力。保留软 Alpha 与图层不等于承诺这些高级编辑对象。没有新生图调用来证明新版提示词成功率；此次验证分为软件功能验证和独立接手程序走查，分别记录。

## 源文件身份

- L ZIP SHA-256：cedfe6530f1042f665d011b26df6260113e7198daf5dcde0863e76f165067b26
- B ZIP SHA-256：574f82b577690427095bafb5a2fdd5fbf0303a064559e8f08208cdcdfb71e000
- 实际交付 W1.0 ZIP SHA-256：bfe78e4bcc617483c9e3136023aeefa40e2a6d6812ac43dcba2a3fafaecb87dc

这些哈希用于确定审计对象和恢复旧版本，不用于艺术一致性评分。
