# 依赖与冷启动

## 先读什么

1. 读取 workflow/SKILL.md，确认用户要 PSD、PPTX，或两者
2. 找到并完整读取 consumer-first-writing/SKILL.md，再读其路由命中的参考。写新的演示文稿时至少按实际内容读取 writing-modes；改已有稿读 editing-existing；正文、讲者注释、工程交付分层时读 layered-instructions。编写图片提示词或修改本 Skill 时另读 ai-instructions。不要给普通幻灯片正文附上作者的制作与验收汇报
3. 读取 frontend-development 及视觉设计、内容与文案参考；导航涉及组件关系时读界面设计。写代码前读取 coding-rule
4. PPTX 读当前可用的 Presentations 及它要求的 implementation、API quick start、finalization；用图表/表格时读 native_evidence。PSD 读本包 psd-production 与 project-contract

文件存在不等于已读取。当前任务中记录实际读取来源即可，不要求把加载过程写进作品。

## 配套包怎样用

```text
解压目录/
  workflow/SKILL.md
  workflow/使用说明.md
  workflow/references/...
  consumer-first-writing/SKILL.md
  consumer-first-writing/references/...
```

这两个目录是独立标准 Skill。保留同级结构时，可以从 workflow 根目录读取 `../consumer-first-writing/SKILL.md`，再以该目录为基准读 references。安装时分别放到宿主支持的技能目录，通过名称发现；不要将 consumer 主文摘录成几个口号代替完整前置。

配套 consumer 来自用户原包，内容不作修改。原 ZIP 的 SHA-256 为 `f8e48c5bdcf2f7c9a749b0af2605605687d11f2c0e1cbcedc812f6d2a3d21727`。本包不自动安装，不包含其他技能的私有副本、图片模型、账号权限或 API Key。

frontend-development、coding-rule及当前Presentations不在此配套包中。先通过宿主提供的技能发现/读取入口按名称查找，再完整读取所需主文与参考；宿主没有技能目录入口时，使用用户已提供且有权读取的完整原包或明确路径。确认不可读或未安装后再请求对应技能，不猜测别的机器或私有路径，不将一次缺项解释为宿主永远不支持。

优先读已安装的所需技能；找不到 consumer 时检查同级配套目录。路径存在但子参考读取失败，报告具体文件、失败和影响，可读取用户提供且已验证的同一配套文件。两处都缺失时，明确“缺少 consumer-first-writing，内容与文案定稿暂不能按所需前置进行，请提供完整包或可读目录”；可以继续源资料整理和运行时检查，不伪称已加载，不静默用自己的概括顶替。frontend/coding-rule/Presentations 缺失时同样准确说明，不凭私有绝对路径猜测安装。

## 运行时

PSD：沿用锁定的 package-lock.json、requirements.lock 和 `project.py doctor`。已有可用依赖优先复用，安装遵守当前环境授权。

Node诊断分别读加载与版本结果：loadable只表示公开包名的真实require是否成功，遵守当前Node解析和NODE_PATH；metadata_verified表示已从同一resolved入口最多12层祖先路径找到名称匹配的包元数据，遇node_modules边界停止；version_matches再与package.json中的精确期望版本比较，安装仍按现有lock。不要因没有workflow/node_modules副本就判断外部已加载依赖不可用。

- loadable=false：未加载，按error_code核对实际加载错误
- loadable=true且metadata_verified=false：已加载但版本未核，按metadata_error_code核实该安装位置；不能当作完整就绪，也不自动重装或改变解析优先级
- loadable=true、metadata_verified=true且version_matches=true：已加载且与本包锁定的精确期望版本匹配

元数据已核实但version_matches=false时，则是已加载的版本不符，installed保留实际版本；同样不能当作满足锁版本要求。加载失败、版本未知和版本不符不相互替代。

PPTX：本次参考实现使用 Presentations 的 `@oai/artifact-tool` JavaScript API，及 Python 标准库、Pillow。运行前按 **当前** Presentations 设置实际 RUNTIME_NODE、RUNTIME_NODE_MODULES、RUNTIME_BIN_DIR、RUNTIME_PYTHON；`--presentations-skill` 指向本次实际读取的 Skill 根目录。构建器调用其正式 finalizer 与 authoring marker。不把这个环境的绝对路径写进新工程。

### 区分找到工具与实际验证

声明某个应用或渲染器缺失前，检查当前获授权环境的宿主说明、公开工具入口、已声明的运行时目录和 PATH。只在系统 PATH 中未找到名字，不能排除宿主 bundle 已提供它。发现明确入口后，用该程序支持的版本/帮助命令核实能否启动；不要猜私有安装路径或扫描未授权环境。

能力记录分清：入口未找到、可启动、已对本文件导入/导出、已在目标应用实际编辑保存。它们不相互替代。比如可运行的 LibreOffice CLI 可以用于实际 PDF 导出检查，不能写成已做 PowerPoint 桌面编辑；没有做某项操作也不能写成该软件不存在。

字体显示不同先分别核实文件中的声明、实际字体可用性和各渲染器的输出。可用且适合本任务的第二渲染器能帮助判断差异，但不因此悄悄改变已承诺的原生文字能力或强制增加所有目标应用验收。

配套代码没有打包运行时与字体，因此是可携带 Skill/源工程，不是无需依赖的一键安装程序。缺少指定运行时，停在准确的能力缺口；不要另装一个未经验证的库后声称等价。宿主使用其他合法后端时，可以按用户目标适配，但需公开差异、实际回读和编辑测试，不能把参考实现验证扩张成所有后端都通过。

## 新 AI 从哪里开始

没有历史聊天时，向自己收齐用途、受众、格式、准确内容、页数/尺寸与可编辑目标。能合理推断的自行决定，关键缺口一次问清。建立独立PROJECT，先内容和视觉系统；PPTX按原生达标优先构建完整代表页，需要复杂图片时再做母图/语义分层，PSD继续完整母图流程。

已有 PSD 项目：运行 status，读 plan.json、receipts.json、resume_note，沿旧入口继续，不转成 PPTX 协议。

已有 PPTX 项目：读 brief/content/design-system、deck.json、jobs.json、receipts.json、resume.json 和最近 builds 下的实际文件。查可用素材和未完成页，沿最后选定母图继续。没有调用证据就只称“已有素材回放”。从旧 G05 工程迁移时按 deck-contract 映射，无须再次生图。
