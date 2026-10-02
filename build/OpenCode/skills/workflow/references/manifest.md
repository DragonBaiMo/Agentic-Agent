# 配置与命令

这些命令是Skill的文件组装接口，不能独自证明图像生成能力。使用workflow前仍须满足[全局图像工具前置](dependencies-and-start.md#必需的图像工具)；纯技术回归无图片调用的事实，不是无生图工具启动Skill的例外。

## 一次安装，直接重用

运行目录为本 Skill 根目录。`npm ci` 使用锁文件安装 ag-psd 31.0.0 和 @napi-rs/canvas 0.1.100。独立验证使用 `requirements.lock` 的 psd-tools 1.21.0 及其合成依赖；锁定的 NumPy/SciPy 等要求 Python 3.12+，本次验证 3.12.14。并非免安装软件，不包含 Photoshop 或字体授权。

若当前环境的默认 npm 缓存目录不可写，可以用 `npm ci --cache ./tmp/npm-cache` 指定本项目临时缓存；不要用管理员权限覆盖系统权限。离线环境需要预先准备已许可的依赖，不能假称零依赖。

```bash
npm ci
python -m venv .venv
.venv/bin/pip install -r requirements.lock
node scripts/assemble.cjs --config examples/future-lab.json --out output/demo
.venv/bin/python scripts/verify_psd.py --psd output/demo/future-laboratory.psd --config examples/future-lab.json --out output/demo/qa --preview output/demo/future-laboratory-preview.png --review --master assets/future-lab/reference-preview.png --toggle "装置 / 钴蓝陶瓷与拉丝金属"
```

Windows 中把 `.venv/bin/python` 改为 `.venv\Scripts\python.exe`，pip 同理。示例默认使用 Linux 的 Noto Sans CJK SC Bold 和 Liberation Sans Regular。其他环境设置 `POSTER_FONT_CN`、`POSTER_FONT_LATIN` 指向合法字体文件，或修改 JSON 的路径、family、postscript，使三者与实际字体相符。若换字体导致外观变化，需要重新看图；不要只改字体文件而仍声称旧字体。

安装前后可运行 `python scripts/project.py doctor`；给 `--project "$PROJECT"` 或 `--plan /actual/plan.json` 时同时检查选定字体路径。输出 Python/Node 版本、锁定包实际版本、Node 模块真实加载结果和字体文件是否存在。此命令只读、不安装，诊断缺项不自动处理权限；图片工具仍在宿主发现。字体路径存在不是 family/PostScript 已核实，见 [字体校准](font-calibration.md)。doctor 输出诊断事实，不以退出 0 代表所有条件满足。

## 一个简单 JSON，不需要工作流数据库

新项目优先编辑 plan.json，按 SKILL 的 init/record/compile 流程得到本节 manifest。这里是打包后端契约，不要求新接手 AI 直接凭空造好所有真实素材路径。旧工程已有 manifest 则可以直接回放。

`examples/future-lab.json` 是完整可运行示例。各相对路径相对于该 JSON。

| 字段 | 含义 |
|---|---|
| name | 输出基本文件名；小写字母/数字/连字符，最多 64 字符 |
| width / height | 画布像素，16–8192；画布最多 3200 万像素 |
| groups | 底到顶的文件夹名列表；仅一层文件夹 |
| asset_dir | 素材根目录，显式本地目录 |
| art | 图片层数组；至少一层 |
| text | 原生文字数组；可以为空 |
| fonts | 原生字体声明；没有原生文字时可以为 [] |
| notes | 可选任意项目说明；代码不会把它当生图或审批指令 |

所有叶层合计 2–128；画布像素 ×（叶层数 + 1）最多 2 亿，限制解码内存。更大项目需要经过测试的其他后端，不靠关闭边界检查硬撑。输入 JSON 是本地可信项目配置，不应直接把外部网页当配置执行。

### 图片层

```json
{
  "name": "主物体", "group": "主体", "kind": "object",
  "file": "subject.png", "source_size": [1024,1536],
  "crop": [58,339,932,858], "destination": [141,394,800,740],
  "expect_alpha": true, "z": 10, "blend": "normal", "opacity": 1
}
```

- source_size 是真实源文件尺寸；不一致表示取错素材或配置过期
- crop / destination 都为 `[x,y,width,height]`，不是 xyxy；原点左上角
- crop 只选择已生成独立素材中的区域，不用于把整张母图切成假图层
- destination 可以平移、缩放；可有负起点，但画布内完全不可见会报错
- expect_alpha 要求源图具有真实非完全不透明像素，不接受仅靠目标画布空白伪装透明；透明边缘是否好看仍靠看图
- kind 可为 background/object/effects/glass/shadow/typography/decoration；图片文字可带 copy_ids 字符串数组，供执行者核对归属，代码不识别图片中的字
- blend 支持 normal/multiply/screen/overlay；opacity 0–1；hidden 可为 true

### 原生文字层

```json
{
  "name": "说明文字", "group": "信息", "copy_id": "subtitle",
  "value": "让想象发生", "x": 64, "baseline": 1300,
  "size": 28, "font": 0, "color": "#132343", "tracking": 0, "z": 20
}
```

字体记录含 `path`、`family`、`postscript`，可选 `env` 环境变量覆盖字体路径、`weight`。size 为画布渲染字号；tracking 为千分之一 em。每条记录是简单横向单行，多行可按行建多个文字层。支持同样的 blend / opacity / hidden。复杂书写方向、组合字符和部分需塑形的文字会明确报错，不能默默输出错误排版。

### 层序

groups 控制跨文件夹顺序；同组内 z 较小的在下，无 z 时保持旧包的 art 再 text 顺序。z 相同按输入稳定排序。需要文字被物体遮挡时把两者放同一组并设 z，或用不同组的前后关系。文件夹采用 pass-through，让阴影可以混合下方背景；不支持文件夹本身的蒙版/效果/透明度。

未知字段会报错，避免写了 mask、smartObject、vertical 等参数却被静默忽略。已存在的 PSD/PNG 默认不覆盖；只有确实允许重建该产物时才加 `--overwrite`。

## 每个命令输出什么

- `assemble.cjs --config JSON --out DIR [--overwrite]`：PSD、独立 PNG、ag-psd 回读 JSON、logs/assembly.jsonl
- `probe_assets.py IMAGE [IMAGE...]`：只读图片尺寸、Alpha 极值、分布及不同阈值包围框的 JSON；不判断物理透射
- `measure_text.cjs --config JSON --layer 原生文字层名 [--target-width 像素]`：真实字体逐字符 advance 与可选字距建议，不修改布局；不代表墨迹边界或 Photoshop 重排
- `verify_psd.py --psd PSD --config JSON --out DIR [--preview PNG]`：独立结构报告；失败非零退出
- 添加 `--review`：从真实图层重建 reconstructed.png
- 添加 `--master IMAGE`（需 --review）：左基准、右重建的对照图，绝不自动给相似分数
- 添加 `--toggle "图层或组名"`（需 --review，可多次，最多 8 项）：隐藏视图，不修改原 PSD

显隐诊断通过当前psd-tools公开的 `layer_filter` 排除目标，不切换文档的visible标志或updated状态。真实回归发现：先改visible再改回，虽然可见性恢复，updated仍为真；该状态会影响库后续选择保存/重绘路径，因此只读诊断不应改变它。本次旧、新诊断图像素相同，不将这项隔离修正描述为PSD丢层修复。当前输入已经处于updated状态时保留其状态；不改PSD文件、依赖或Photoshop行为。

基础验证检查维度、每组的图层名和顺序、实际像素、native type 及准确文字、混合/透明度/显隐。它不是 OCR，不自动判断主体是否画对，也不保证字体在 Photoshop 重排后一致。无需在正常产图时反复跑代码单测。

## 面向维护者的测试

```bash
npm test
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

单测验证组装程序是否正确，与作品艺术验收分开。示例 smoke build 才会覆盖真实 1024×1536 素材。`validation.json` 记录本版本已运行范围；其他操作系统、其他字体、复杂文字和实际 Photoshop 不因这些测试而自动通过。

## 项目工具参数索引

- project.py：`doctor [--project DIR | --plan JSON]`；`init --project DIR --plan JSON`；`status/snapshot/compile --project DIR`；`restore --project DIR --snapshot 项目revisions内目录`
- visual_job.py：`--project DIR --task master或图像层id --out 新任务目录`；不接受 native_text 任务，不实际调用模型
- record_asset.py：`--project DIR --task ID --source 实际图片 --origin generated|user_supplied|conversation_history --tool 实际来源`；generated 另需 `--job 任务目录`；可选 `--call-id`、`--status usable|rejected`、`--reason`；generated 可加 `--execution 公开实际参数JSON`，格式见 tools-and-prompts.md
- review_assets.py：`gallery --images 图片... --out PNG`；`viewer --psd PSD --master 图像 --out 目录`；`move --psd PSD --layer 唯一叶层名 --out PNG`
- deliver_project.py：`--project DIR --handover MD --mode final|review|diagnostic --out ZIP`；非 diagnostic 另需 `--build 构建目录`

usable/final 是执行者已看图后的选择，不是脚本自动判断艺术合格。路径、引用或字段错误会非零退出；每次新生成请求用新 job 目录，旧文件保留。生成失败或工具权限不足时按 recovery-and-handoff 处理，不用改字段谎称成功。
