# 没有历史聊天的 AI：完整新任务演练

任务：用户上传 1080×1350 香水海报，要把背景、玻璃瓶及固定标签、前景丝带、薄雾、金属艺术标题“夜航”拆开，底部“EAU DE PARFUM · 50 mL”可改字。允许近似定位，自主完成。

这是操作演练，不是本次已经生成了这张香水图。示例中只有计划，图片文件必须来自实际用户/工具，绝不能用不存在的路径假装完成。

## 1．准备工程

先按[工具前置](dependencies-and-start.md#必需的图像工具)确认主模型可调用图片生成/参考图编辑工具并保存返回；没有该能力时本演练停止，不能把不存在的图片换成模板或代码图后继续。

从 `examples/new-poster.plan.json` 复制一份到自己的任务目录外作为初始化输入。看用户图片后核对其中的 NIGHT VOYAGE 标签是否真的存在，修改实际文案、方向、目标框与字体；不要盲抄示例坐标。本演练明确已获“自主完成”授权，因此把示例的 staged 改 autonomous、stop_at 改 []，记录本任务的真实授权与 5 张图片层 + 1 层可改说明的方案。普通未授权任务保持 staged，推荐分层与母版一起给用户选择。设置 PROJECT=/absolute/work/night-voyage。按 manifest.md 一次安装依赖，然后：

```bash
python scripts/project.py init --project "$PROJECT" --plan /path/revised-plan.json
python scripts/record_asset.py --project "$PROJECT" --task master --source /actual/user-poster.png --origin user_supplied --tool user_upload
python scripts/project.py status --project "$PROJECT"
```

此时 master_exists=true、pending_images 包含 background/haze/bottle/ribbon/headline；caption 是 native_text，不应要求图片模型生成。记录用户输入来源；不是新的模型调用。

## 2．试玻璃瓶这一难层

```bash
python scripts/visual_job.py --project "$PROJECT" --task bottle --out "$PROJECT/jobs/bottle-01"
```

打开 DRAW：只应要求瓶体、瓶盖和固定标签，允许文字仅 NIGHT VOYAGE；不应要求夜航或底部说明。reference 必须是真正完整用户图。把这两项交给实际参考图编辑工具；透明参数按真实 schema 开启。不要把 request.json、包目录或 PSD 验收描述传给图像模型。

模型返回后保存为真实路径，看玻璃、标签、补全和位置；运行 probe，包括非零 Alpha 内近不透明比例。这只是数据，外侧透明不证明瓶内会跟随新背景透射。若实际是黑底 RGB，登记为 rejected，保留原因。先检查工具是否真的收到了透明参数与参考图；修正后用 bottle-02 新任务重试。不要同样提示词空转，也不要为了“通过”把黑色当透明。

```bash
python scripts/probe_assets.py /actual/bottle-01.png
python scripts/record_asset.py --project "$PROJECT" --task bottle --source /actual/bottle-01.png --origin generated --tool ACTUAL_TOOL --job "$PROJECT/jobs/bottle-01" --status rejected --reason "真实文件没有透明通道"
```

若结果本身可用，则不加 rejected，登记后 plan.layers[bottle] 自动写入 assets 中的新文件名和 source_size。玻璃轻微偏位不必重生，留到定位。

## 3．其余四张图片与一层原生字

background 用背景模板：去除产品、文字、丝带、雾并补全；haze 保留柔 Alpha；ribbon 只含丝带；headline 只含“夜航”金属字。分别执行 visual_job、实际模型调用、看图/probe、record。独立请求可并行，但登记顺序执行。

caption 不生成图片。核实字体路径、family、PostScript 名，设 style 的基线/字号/颜色，必要时按 font-calibration.md 测行宽。headline 由独立艺术字模板处理，不带瓶体玻璃描述。若所有文字必须图片，按已确认架构改 caption 为 image/typography 并加入 copy_ids；若用户要金属字也原生可改，需要支持该效果的实际后端或明确取舍，不自动把金属字降成普通字体。

## 4．位置校正与首版

status 显示必需 image 都可用后，看源对象与母图位置。保持整画布基本原位的素材无需 crop；某个对象偏大则测其实际包围框，用等比 crop/destination 调整。不要用所有层一起硬拉伸的办法掩盖单层问题。

```bash
python scripts/project.py compile --project "$PROJECT"
node scripts/assemble.cjs --config "$PROJECT/manifest.json" --out "$PROJECT/builds/B01"
python scripts/verify_psd.py --psd "$PROJECT/builds/B01/night-voyage.psd" --config "$PROJECT/manifest.json" --preview "$PROJECT/builds/B01/night-voyage-preview.png" --out "$PROJECT/review/B01" --review --master /actual/master-file.png --toggle "玻璃瓶与固定标签"
```

master-file 取 plan.master.file 在 PROJECT 下的实际位置。正常计划有 5 个图片层和 1 个 native type，6 个语义组；数量是这个示例的结果，不是所有作品门槛。查看 reconstructed 和母图，不把技术 passed 当成看图批准。

## 5．修一处而不重来

若隐藏瓶体仍有瓶残影，只重做 background。先 snapshot，用 background-02 生图并登记，新构建 B02。若只是瓶偏右，改它的 destination，再编译；不消耗图片调用。若 B02 反而破坏标题，restore 回 B01 前保存的计划快照，原素材全部保留。被遮挡区域露洞，针对责任主体补全，不拿整张母图覆盖顶层。

中断前在 resume_note 写“瓶/标题已可用；背景残影待修；下一任务 background-02；最新可看版本 B01”。下一位 AI 先 status/receipts，就能继续，不重画所有层。

## 6．检查与交付

必要时用 move 检查瓶是否带走其他文字，用 viewer 让用户切换真实图层。填 START_HERE：标题和标签是图片文字，底部是原生文字；对应字体、轻量位置校正、还存在的细微玻璃差异；写清实际是否做了 Photoshop 实机测试。

执行 deliver_project 的 final/review 模式生成完整源包，同时单独交付 PSD 与 PNG。用户未要求最终确认且自主完成时可写“执行者视觉检查通过”，不要写“用户已批准”。

## 从零设计分支如何起步

若用户没有图，把 entry 改 single_design，先用 master 任务生成含全部文案的完整作品；其他步骤相同。大胆选择一个主题签名，其余信息有纪律。普通字需要精确 native 预排时，可把无字艺术中间图与 native_text 放入临时候选 manifest，先构成完整候选并选稿；这个临时整图底层不能冒充最终分层背景。多方向 entry=candidate_gallery，生成 C01/C02 后做编号画廊，按用户确认偏好选定再拆层。两个节点可一次问“推荐 C01，按这 6 层方案制作可以吗？”；明确全自动则记录执行者选定和分层依据继续。
