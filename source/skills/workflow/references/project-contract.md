# 项目计划与数据流

这是把需求接到工具的契约，不是审批表。`examples/new-poster.plan.json` 是完整结构示例，没有假造图片返回；须改成当前项目。

## 输入如何流动

| 输入 | 写入 | 消费者 |
|---|---|---|
| 用途、方向、尺寸 | brief/direction/canvas | 完整图提示词、最终 PSD 画布 |
| 全部准确文案 | copy: id/value | 图片只取所属 copy_ids；原生文字用 copy_id |
| 确认偏好与实际决定 | interaction.mode/stop_at/decisions | 两个关键节点可合并；明确全自动可自主；不需要票据签名 |
| 实际母图 | master.file + receipts | visual_job 复制真实附件，不能只传哈希 |
| 语义拆分 | layers 的 owns/excludes/kind/occlusion | 单素材视觉提示词 |
| 视觉目标位置 | target_box/effect_box | 模型和看图定位参考，不是自动评分门槛 |
| 真实返回 | record_asset → assets、file/source_size | compile → manifest.art |
| 最终放置 | crop/destination | 轻量裁剪、平移、缩放 |
| 准确字与字体样式 | copy_id、fonts、style | manifest.text → native type + 缓存像素 |

## 顶层字段

entry 是 single_design/candidate_gallery/existing_design；resume/replay 是接续方式。output_name 是安全文件名，canvas 是像素宽高。brief 和 direction 写当前项目而非套例图。copy 必须包含必要文案，即使它在产品标签上也明确归属。interaction.mode 为 autonomous/master_only/staged；新项目默认 staged 的 master/layer_architecture 两个关键节点，可合并。明确全自动授权则 autonomous；既有项目沿用实际约定。user_visual_approval 仅真实批准后为 true，可选 notes/decisions 记录依据和编辑取舍，不作为机器签票。完整沟通方法见 [关键确认与分层架构](interaction-and-layers.md)。

master 初始可为 {}，登记后有 file/origin/receipt_id。fonts 与 manifest 契约相同；全图片模式可为 []。groups 底到顶。resume_note 写已完成、缺什么、下一动作、等谁。

## 两类层

image：id/name/type/kind/group/z，owns/excludes/copy_ids，alpha，target_box/effect_box，occlusion，blend/opacity。kind 支持 background/object/effects/glass/shadow/typography/decoration；不要求七类齐全。目标位置通常先看母图后填写。file/source_size 由真实图片登记，不提前填虚构文件。

native_text：id/name/type/group/z、copy_id、style。style 必需 x/baseline/size/font/color，可有 tracking。它没有图片源文件，不走 visual_job。简单多行按行分层；复杂脚本/艺术效果与真实文本框能力见 limitations。

每个文字片段由一个明确层或明确分行组拥有。实物表面的瓶标签可和瓶体同层，但应说明它是图片文字，不能称为可改字；单独排版的普通标签按native_text能力处理。特殊艺术造型超出当前Type能力时使用image/typography，不因它叫标题就自动出图，也不因原生排版方便而改掉所需风格。

向用户展示的是叶层数量、分组与每层能编辑的内容；数量按 layer 项统计，不能把文件夹数或整张母图缓存算成真实编辑层。全自动默认按最小充分编辑动作拆分，没有固定层数要求。

## 坐标规则与变换

所有 plan 的 box、crop、destination 均为 `[x,y,width,height]`。LayerForge 原包的 xyxy 应转换为 `[x1,y1,x2-x1,y2-y1]`。target_box 是期望位置；crop 是实际独立素材上的取用区域，destination 才是最终放置，两者不可混为一谈。

例：实际对象包围盒为 `(100,300,700,800)`（xyxy），则 crop=[100,300,600,500]。目标宽 540，等比高 450，destination 可为 [150,420,540,450]。视觉检查中心、轮廓、遮挡；不是凑框就算对。

默认编译将完整源画布缩放到目标全画布。源/目标长宽比不同或物体明显漂移时，先明确 crop/destination，别盲目拉伸。不会自动切掉弱 Alpha；玻璃、柔光和投影要在浅/深背景上看。

## 编译与回放

compile：canvas→width/height，output_name→name，groups/fonts 原样；image→art，native_text→text，value 从 copy_id 取。生成用 owns/目标框不塞入 PSD 后端冒充高级属性。缺真实文件会报 missing_asset，不能拿母图副本填空。

旧 build-layered-poster 的 manifest 仍可直接用 assemble；不强制迁移。要获得新项目工具，再将其 art/text 映射成 plan 层。LayerForge 的旧 state/project.json 不直接兼容：抽取 brief/copy、实际母图/来源、已采用图层、坐标和混合关系，转换 xyxy；源文件复制到新工程后按历史来源登记。

## 候选、并行与接续

不同方向 C01/C02；微调 C01-v2。完整候选可经 gallery 展示；自主选稿留一句视觉依据，不能冒称用户批准。重选 master 后重新看已有层是否还适用，程序不作艺术失效门禁。

母图与计划稳定后，背景/独立对象/字体检查可并行；图片工作者只收到 DRAW + reference。登记/改计划/恢复由单一执行者串行，脚本没有并发锁。结果先保存、再登记；PSD 先写出、再解析。状态不确定时 status 和 receipts 查实际文件，旧素材标 conversation_history，后台 Prompt 不可见就记 not_exposed。
