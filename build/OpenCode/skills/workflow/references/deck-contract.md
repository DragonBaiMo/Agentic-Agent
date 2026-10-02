# deck.json 与共用资源

本版 PPTX 协议为 `schema_version: "pptx-1"`。PSD 的 plan/manifest 仍用原协议，不要拿 deck.json 调 project.py compile。

```text
PROJECT/
  brief.json / content.json       用途、逐页叙事、准确文案、来源
  design-system.json             画布、颜色、字体角色、网格、版式族、导航
  deck.json                      实际页对象与坐标，引用所选语义资产
  data.json                      唯一数值来源，可选
  jobs.json / receipts.json       待生图任务 / 实际调用及导入结果
  masters/                       完整页面母图，不作为整页可编辑成品
  assets/ / cropped/ / rejected/  原始语义素材 / 紧裁成品 / 不采用素材
  jobs/J01/                      DRAW、真实参考文件与不变的准备快照
  crop-ledger/                   原画布、裁剪框、补偿后目标框
  builds/B01/                    compiled.json、final.pptx、实际渲染；验证报告在 evidence/B01/
  review/B01/                    母图对照、实际编辑副本证据
  resume.json / logs/ / tmp/      续做记录、关键事件、可清理临时产物
```

content 的最小有效内容是每页的 purpose、可见文字角色与准确字面、source_ids、必要限制、是否经常编辑。design-system 的 navigation 应包括 section_id/顺序、共用位置、各状态素材、激活区分方式和 links（默认 false）。这些供主模型执行设计判断，不是后端自动设计的参数。

标题在同一内容资源中以title_contracts记录slide_id、text、origin（user_specified或lead_model）、source、change_frequency（fixed或frequent）、representation（native或semantic_art_image）及object_id。用户指定标题的text保留原话；主模型拟题记录事实或页面职责依据。艺术图另写editing说明，不能把“整体可移动”称为“可逐字输入”。标题来源、编辑频率与对象形式是独立字段，不互相推导。后端保留这些说明字段，但不声称自动识别图片里的汉字；艺术字准确性仍需看实际输出。

例如固定“四周试用”采用艺术图时，试用周数仍是业务事实。如果它会受data.json变化影响，按下文art_bindings绑定对应周数或标题字段，修改事实后走局部艺术层替换，不能沿用过期图片标题。

## 组装字段

| 字段 | 用途 |
|---|---|
| schema_version, name, canvas | 协议、作品名、[宽,高]，单位 CSS px/96 DPI |
| background, background_alt | 可选，真实干净共用PNG的项目相对路径与说明；显式提供时图片优先，缺文件不回退 |
| theme.background | 有PNG时为原有备用纯色；省略background时必须为#RRGGBB，由公开母版fill直接实现，不需要制造背景图片 |
| text_styles | 可选，项目自己的角色名到当前JS完整文字style；不固定字体、字号或主题 |
| font_policy | `{basis:"design",families:[实际字体族]}`，按当前 Presentations 规则使用 |
| slides | 有顺序的真实页；含唯一 id、section_id、master_reference、elements、notes |
| data_file, data_bindings, art_bindings | 可选；单源数值与艺术标签一致性契约 |

elements 数组是普通页的绘制顺序，每个元素有本页唯一 id 和 kind。跨页共用艺术导航可引用同一 file，目标框来自同一 design-system 状态表。不要给同一状态生成六套不一致的导航。

- image：file（项目内 PNG）、box=[x,y,w,h]、alt、可选 fixed_layout。图片字的准确文案及编辑职责可放 copy/role 注释字段。fixed_layout=true 表示版式图片，始终在普通页对象后面，需版式视图编辑
- text：text、box、style，或以style_role引用text_styles，再用可选style覆盖顶级字段。嵌套对象整体替换，未知角色或无效样式拒绝并定位页/对象。style是当前Artifact Tool的完整文字样式，如typeface、fontSize、color、bold、italic、autoFit、wrap、insets、lineSpacing；字段须查API并实测。单位、状态复位与长文验证见[原生样式源](native-style-tokens.md)
- chart：chart_type、options、font_family。options 是已读公开 chart API 对象，包括 position、categories、series、axis、format 等；用原生数据绘制，艺术外置标签不自动绑定
- table：options（rows、columns、left/top/width/height、columnWidths、values）、ranges。每项 range={block:{row,column,rowCount,columnCount},style:{...}}，复用当前公开 table API
- rule：box、fill。只用于母图中实际存在的信息分隔/结构线；不能用它编程绘制装饰插图代替生图

背景PNG自动提升到真实共享slideMaster；省略PNG时保留该母版的原生纯色。本页fixed_layout图片置于单独slideLayout。普通页对象保持独立。text_styles是源工程复用入口，不是完整PowerPoint主题字体/配色引擎；改PowerPoint主题不保证自动替换图片字或所有直接格式。

## 单源数值与艺术图片

data.json 可以是任意普通 JSON 层级，例如 `scores.current=72.6`。data_bindings 的 key 使用点路径，path 使用从 deck 根开始的键/数组索引路径；编译时把值填入原生对象。例如：

```json
{
  "data_file":"data.json",
  "data_bindings":[{
    "key":"scores.current",
    "path":["slides",0,"elements",2,"options","series",0,"values",0]
  }],
  "art_bindings":[{
    "key":"scores.current","approved_value":72.6,
    "object_id":"score-art","file":"cropped/score-art.png",
    "sha256":"该已核对图像的真实SHA256"
  }]
}
```

同一个艺术图包含多个数值时，每个值各有绑定，共享 file/object_id。 `_derived` 可定义 reduction_percent，给 baseline/current 的数据 key、输出 key 和 decimals。只支持这项明确计算；其他指标在可靠数据整理阶段算好，不执行表达式或任意代码。

每项艺术绑定必须指向实际使用的图片对象，不能只登记一份未上页的旧素材。默认object_id在全套中须唯一；跨页复用同一对象ID时，加`slide_id`指定页，例如`"slide_id":"S02"`。同页对象ID仍须唯一。编译器在data_bindings解析后核对该目标是image，且对象file与绑定file解析到同一项目内文件；相对路径的`./`别名不构成差异。对象缺失、非图片、跨页歧义或引用错文件会报具体错误并停止，不自动改绑定来放行。只验证绑定本身的值与哈希不足以证明页面正在用它。

绑定在编译时覆盖目标path的原字面值；被覆盖的字面不是另一份报价决定。已有工程接手时查明真正的key和data_file，再改其权威来源并核compiled.json。需要货币格式、日期文案或双格式内容副本时，沿项目已有准备脚本生成对应显示字段和内容资源，明确该项目的格式合同；本编译器不自动格式化任意金额，也不自动同步PSD文案。不要仅改一个最终配置后声称所有来源都已更新。

数值或绑定资产字节改变后，编译输出 pending-art-replacements.json 并以退出码 2 停止；显式slide_id会保留在待替换项中。按新值局部编辑该图片，实际看图、紧裁和补偿，再更新 approved_value 与 sha256；仅改绑定来消除报错不能证明标签正确。未发生数据变化无需重做图片。

这是重建工程的同步约束。PowerPoint中改chart的数据不会自动修改艺术图片，编辑说明必须点明该关联。承诺可改数据的图表必须保留能读取/修改的原生数值，不能只剩一张数字图；按已定视觉取舍采用图片图表时，准确源数据仍保留，并明确不能在PPTX中直接改数据。

## jobs 与接手

jobs.json 的 tasks 以稳定 ID 索引，每项含当前纯视觉 prompt、references（项目相对路径）和真实 transparent_background 布尔值。提示词由 content/design-system 与该页任务写出，不把整个 deck JSON 原封不动塞进图片模型。

receipts 区分 prepared_not_executed 与真实 result_recorded；来源为 generated/user_supplied/conversation_history，记录工具、公开调用 ID（未暴露则 not_exposed）、结果哈希、公开参数。不能从已保存文件倒推出某个模型版本。

从 G05 旧工程迁移时，把原 images/texts/chart/table 依原绘制顺序转成 elements，数据与艺术绑定显式转入上述字段，保留来源和母图。迁移只改变协议，不改变艺术素材；旧工程仍可使用原构建器。普通旧 PSD 项目无需迁移。
