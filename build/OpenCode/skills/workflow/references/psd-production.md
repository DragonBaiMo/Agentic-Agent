
# PSD 制作全流程

先完成主 Skill 的前置加载、文案与编辑职责约定。本文件是 PSD 分支的完整执行流程；按阶段完成输入、动作、输出，遇到指定分支再读参考。不要只跑历史例图重建，就声称完成用户的新项目。

目标：先做有辨识度、敢于取舍的完整设计，再保持母版的整体构图和重要内容，生成真正可独立操作的图片/背景/文字层，交付 PSD 与单独预览。大胆集中在主题签名元素，其他信息保持清楚。位置、大小、纹理和反光允许合理误差；不设 100% 像素复刻门禁，不编造相似分数。准确文案、数字、主体身份和数量不能借容错随意改变。代码保证文件事实，视觉判断决定作品是否够好。

## 0．入口、工具和目录

| 输入 | 入口 | 开始位置 |
|---|---|---|
| 只有需求，做一版 | single_design | 建计划，然后生成完整设计 |
| 用户要多方向比较 | candidate_gallery | 建计划，生成编号完整候选并选稿 |
| 用户给完整图/所谓模板图 | existing_design | 导入原图，识别全部文字，再拆层；不自动套商业模板 |
| 已有计划与素材 | resume | 先 status，读 plan/receipts/resume_note，继续缺项，不重新 init |
| 只重建已有配方 | replay | 用已有 manifest 与素材组装；不声称本次重新生图 |

需要：文件读写、真实看图能力、Node/Python，以及能生成/编辑并返回可保存图像的实际图片工具。已有全部合格素材时可不生图。先确认当前工具如何传参考图、是否支持透明、如何保存返回；文件名/哈希不等于图像已传入。终端可写 PSD 不代表图片工具可原位提层。

依赖、字体和后端字段见 [manifest](manifest.md)。`python scripts/project.py doctor` 检查本地基础条件；图片工具仍须在宿主真实发现。本包不含模型、API Key、Photoshop 权限，不自动安装到用户环境。

下文从 Skill 根目录执行；`PROJECT` 为独立任务目录，python 指已安装依赖的 Python 3.12+，Node 20+。已有依赖直接复用。

```text
PROJECT/
  plan.json                完整需求/文案、母图指针、语义层、定位、文字样式
  receipts.json            实际来源和调用/导入记录
  inputs/ design/          用户原文件、完整候选与选稿说明
  assets/ rejected/        不覆盖的可用原料；隔离的失败图
  jobs/J01/DRAW.txt        当前一张图像的纯视觉正文
  jobs/J01/reference.*     实际母图文件，扩展名以导出为准
  jobs/J01/request.json    准备信息，不作为图片模型的视觉正文
  manifest.json            由计划编译的组装配置
  builds/B01/              该版 PSD、PNG、基础报告
  review/ revisions/ logs/ 审阅材料、可恢复快照、事件记录
```

plan 是可编辑工作计划，不是审批状态机。用户控制保留在两个有价值的节点：完整母版/方向、图层架构，可合并一次沟通。明确全自动授权时由执行者记录方案继续，不伪造用户批准。各独立图片任务可并行；同项目的登记、编译、回退由一个执行者顺序做。

## 1．用户输入 → 可执行计划

**输入**：用途、受众、尺寸、完整文案、参考/品牌素材、需要怎样编辑。

**动作**：读 [项目契约](project-contract.md)，复制并改写 `examples/new-poster.plan.json`：填 canvas、direction、完整 copy、入口、groups、layers、字体及 interaction。不要把示例主题套进用户项目。初始层只需有清楚的编辑用途；精确位置在母图后补。

先读 [关键确认与分层架构](interaction-and-layers.md)。默认 staged，stop_at 为 master/layer_architecture：先给推荐方案，不把“要几层”空丢给用户。可以把完整母图与建议分层一起展示，一次答复满足两个节点。用户明确“全自动、你决定、直接做完”则 autonomous，记录授权与推荐分层后继续；沉默不等于同意。用户明确只在母图阶段停则 master_only，之后按其授权自定分层；若交付范围只有母图，则止于母图，不擅自扩展。已有项目保留真实的既有约定；缺少不能猜的品牌/法律文案才另问。

```bash
python scripts/project.py init --project "$PROJECT" --plan /path/your-plan.json
```

**输出**：新项目和 plan。**前进条件**：成品目标、准确文字、尺寸与编辑要求清楚；不要求此时所有坐标都钉死。

## 2．完整设计 → 实际母图

**已有图**：先实际看图，转录并核对所有文字，再导入：

```bash
python scripts/record_asset.py --project "$PROJECT" --task master --source /path/user-design.png --origin user_supplied --tool user_upload --call-id ACTUAL_UPLOAD_ID
```

**从零设计**：按完整文案和方向准备任务：

```bash
python scripts/visual_job.py --project "$PROJECT" --task master --out "$PROJECT/jobs/design-01"
```

该命令读取 `prompts/design.txt`，只准备 DRAW 和可选 reference。你必须实际调用宿主图片工具，把 DRAW 正文和真正的参考附件传进去。调用路由见 [工具与提示词](tools-and-prompts.md)。保存真实返回、看图后登记：

```bash
python scripts/record_asset.py --project "$PROJECT" --task master --source /actual/result.png --origin generated --tool ACTUAL_TOOL --job "$PROJECT/jobs/design-01" --call-id ACTUAL_CALL_ID
```

ID 未暴露就省略，不编造。完整母图应包含最终文字方案：采用原生文字时，可以先生成无字艺术中间图，再用真实字体排出完整候选；不能最后临时塞字。多方向各生成完整图，命名 C01/C02；C01-v2 是同方向版本。需要画廊时：

```bash
python scripts/review_assets.py gallery --images C01.png C02.png --out "$PROJECT/review/candidates.png"
```

按 interaction 选稿。普通模式展示实际完整母图、一个推荐方向及其设计理由，询问是否按此方向拆层；此时可合并下一阶段的分层方案。已批准的用户输入图无须再问同一视觉方向。全自动时执行者看图选稿，留选择依据，不能写成用户已批准。重选已有候选用 conversation_history 导入，保留原实际调用记录，不算新生图。

**输出**：master 指向真实完整图，receipts 可追到来源，design 中有选稿说明。**前进条件**：构图和准确文案可用，用户指定的停点已满足。

按 [主题与尺度判断](visual-production.md#从主题到可判断的完整页面) 检查主物体、文字和留白；指定原图先实际放入槽位再判断完整效果。标题来源与表现形式分别记录，用户锁定的字面不因艺术设计改写。艺术字、背景及主体可以是可移动像素层；只有当前 PSD 后端实际支持并验证过的 Type 层才承诺可逐字编辑，不照搬 PPTX 的图表、段落或主题能力。

## 3．母图 → 语义层计划

**动作**：实际看母图后完善每层 id/name/type/kind/group/z、owns/excludes、copy_ids、alpha、target_box/effect_box、occlusion、blend/opacity。

给用户一份可判断的推荐架构：预计叶层数量、分组、每层能做什么、哪些能改字、主体/背景/投影/效果的独立关系及限制。数量是结果，不是越多越好。等待尚未授权的架构选择；已全自动则按 [默认分层](interaction-and-layers.md) 自主记录并继续。用户批准“按推荐方案”即可，不要求会 PSD 或逐字段签字。

- 每层对应一个有用编辑动作：换背景、移动产品、关前景、调光、改文字。七类语义不要求每类都出现
- target_box/effect_box 用全画布 `[左,上,宽,高]`，仅作生成和视觉定位指导，不强行卡像素边界
- 背景必须补全被移除对象；物体按后续移动用途补全遮挡。前后交错可拆为前/后素材，不假称恢复原作者源文件
- 固定产品标签可随瓶体同层，明确其文字所有权；不要让文字同时残留背景又单独叠一遍
- 特殊字形/立体艺术标题用 image + typography；普通可改小字用 native_text；按角色混合。用户明确全图片/全原生时遵从，超出后端能力先说明必要取舍

详细材质/Alpha/布局判断见 [视觉生产](visual-production.md)，原生文字/蒙版限制见 [能力边界](limitations.md)。

**输出**：每层拥有的内容、文字和前后关系明确。**前进条件**：能写出“一次只生成这一份”的视觉任务，而不是裁母图凑层。

## 4．逐份生成/导入 → 可用素材

先试一个有代表性的难层确认调用可用，再扩大生产。对 type=image 的每个 id：

```bash
python scripts/visual_job.py --project "$PROJECT" --task bottle --out "$PROJECT/jobs/bottle-01"
```

按 kind 读取 background/typography/glass/layer 模板，只取所属 copy_ids，并复制真实母图作为 reference。艺术字只继承母图中该字自己的材质，不把其他对象的玻璃、波纹或光效带进字里。看过 DRAW/reference 后调用实际图片工具；优先同画布、原位置、原比例。背景完整不透明，其他素材按计划真实透明。玻璃外轮廓透明与玻璃内部能透出新背景是两件事，probe 分布和实际叠放一起判断。

返回必须落盘和看图；`python scripts/probe_assets.py /actual/result.png` 查尺寸/Alpha。可用才登记：

```bash
python scripts/record_asset.py --project "$PROJECT" --task bottle --source /actual/result.png --origin generated --tool ACTUAL_TOOL --job "$PROJECT/jobs/bottle-01"
```

失败则加 `--status rejected --reason "具体问题"`，不替换已用素材。已有独立素材用 user_supplied/conversation_history，避免重复生图。可用 `--execution 实际调用公开参数.json` 保存实际提交的正文、附件与透明参数；格式见 [工具与提示词](tools-and-prompts.md)。request 是不变的准备快照；execution 是本次实际结果/调用者可见参数，后台参考绑定仍不可见，不把准备成功冒充生成成功。

**输出**：真实 assets、receipts；plan 自动有 file/source_size。**前进条件**：必需内容齐全、能组合。轻微偏位留给定位；内容错了才修责任层。

## 5．定位/文字 → 首版真实 PSD

先全画布叠放。有偏移再填对应层 crop/destination：crop 是独立源素材的区域，destination 是目标位置与大小，都用 xywh。等比缩放优先，禁止为凑框明显拉伸，也不去掉弱 Alpha。不是从完整母图裁矩形冒充语义层。

native_text 不调用图片模型：copy_id 引用准确文字，style 写 font 索引、size、x、baseline、color、tracking。核对真实 family/PostScript 名；字体的字宽、字重和基线先接近，再调字距，不靠拉伸解决。只读行宽工具见 [字体校准](font-calibration.md)。多行可按行分层，复杂排版不能假装支持。字体替换后重新看整体。

```bash
python scripts/project.py compile --project "$PROJECT"
node scripts/assemble.cjs --config "$PROJECT/manifest.json" --out "$PROJECT/builds/B01"
```

编译器把 image/native_text 转成 art/text，把角色文案、素材文件和位置连起来。映射见 [项目契约](project-contract.md)，完整字段见 [manifest](manifest.md)。groups 决定组间顺序，z 决定组内图文前后；陌生字段不会自动成为蒙版/智能对象。

**输出**：PSD、独立 PNG、回读报告。**前进条件**：真正写出所需图层，不能只用缓存预览证明图层存在。

## 6．技术事实 + 实际视觉审阅

NAME 为 output_name；层名用真实唯一名称：

```bash
python scripts/verify_psd.py --psd "$PROJECT/builds/B01/NAME.psd" --config "$PROJECT/manifest.json" --out "$PROJECT/review/B01" --preview "$PROJECT/builds/B01/NAME-preview.png" --review --master /actual/master.png --toggle "主物体"
```

代码检查文件可读、层、顺序、准确原生文字、混合/透明度等事实。你打开重建图/母图对照，看整体关系、重要轮廓、遮挡、错字、背景残影和透明边缘。确认隐藏的是叶层还是整组，按报告中的名字与输出文件对应检查；复核用新目录，避免旧文件被覆盖造成版本混淆。无 SSIM/像素一致艺术门禁，不虚构测量分数。

按需选用，不强制全部跑：

```bash
python scripts/review_assets.py move --psd "$PROJECT/builds/B01/NAME.psd" --layer "主物体" --out "$PROJECT/review/moved.png"
python scripts/review_assets.py viewer --psd "$PROJECT/builds/B01/NAME.psd" --master /actual/master.png --out "$PROJECT/review/viewer"
```

移动只改内存中的诊断副本。HTML 使用真实解码图层，可切换；默认显示所有层，最终显隐以 PSD/成品预览为准。不是 Photoshop 截图。若要求实机验收，真实打开、修改、另存再开，单独记录；解析成功不能替代。

需要继续迭代时，用实际层名演示一项所承诺的改动，例如移动主体或修改受支持的 Type 层文字，再重建一个新版本并检查其他内容。只给可移动的艺术字就说明替换整层的入口，不能宣称它可逐字输入。恢复能力由 plan/manifest、选中素材和真实编辑证据共同证明，不能只交一张合成预览。

**输出**：技术报告、已看图结论与残留问题。**前进条件**：符合用途、重要内容正确、层独立；微小生成差异不拖延交付。

## 7．有问题就局部修；中断就从现状继续

先分清引用/工具、内容、定位、文字、字体或打包问题。定位改配置；内容修责任素材；引用错先修调用。不要每次重做全图。改动前 `project.py snapshot --project "$PROJECT"`，新输出用 B02；登记也保存快照。

新素材或母图登记后重新观察已有定位是否适用。改母版方向、减少承诺的编辑能力、合并用户要独立的主体/效果，或超出已批准预算时，按 [重新确认边界](interaction-and-layers.md) 询问；已授权范围内的定位、字距和微小纹理修复不反复打断。修坏了用 `project.py restore --project "$PROJECT" --snapshot /actual/snapshot-directory` 恢复指针，原料不删除。plan.resume_note 写已完成/缺项/下一步/等待谁；续做先 status，不重新 init，不暗示后台仍在运行。

同一问题默认最多两次有明确变化的尝试；之后换有根据且已授权的方法或报告关键缺口。详细故障分类、暂停/恢复、选择旧版见 [恢复与交付](recovery-and-handoff.md)。权限拒绝不能当成模型失败绕过。

## 8．真实工程交付

按 `resources/handover.md` 写本项目 START_HERE：PSD/PNG、层清单、图片文字与原生文字、字体、布局调整、残留问题、实际验证范围。正常交付 PSD + 单独 PNG；需要源包/AI 续做时：

```bash
python scripts/deliver_project.py --project "$PROJECT" --build "$PROJECT/builds/B01" --handover "$PROJECT/START_HERE.md" --mode final --out /path/project-source.zip
```

final=执行者已完成要求；review=待用户指定审阅；diagnostic=失败诊断，不能冒充 PSD 成品。选择模式不伪造用户批准。打包器检查 PSD 基础结构和 ZIP CRC/哈希，保留选中素材、计划、来源与可回放配置，不带字体/密钥/缓存。用宿主真实文件工具保存并确认附件可访问。

按 [双格式交接模板](../resources/handover.md) 填本项目的实际入口。解压到另一位置后，核对 plan/manifest、素材与字体准备方式，按记录命令重建；复用既有素材时不重复生图。PSD 与 PPTX 同时交付时，各自保留配置和验证结果，可共享素材，但不把一种格式的编辑证据算给另一种。

初次接手跟着 [全新任务演练](new-task-walkthrough.md)；历史 Future Lab 仅是现成素材 replay/smoke。原包每项职责的去向和 1.0 的具体缺失见 [来源映射](source-capability-map.md)。
