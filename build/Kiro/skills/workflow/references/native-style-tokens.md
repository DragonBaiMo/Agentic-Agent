# 原生样式源、单位与实测边界

为当前作品定义标题、正文、注释、数据、正常/活动导航等实际角色。角色名、字体、颜色、字号和状态数量来自主题与内容；不要把研究样例的75/40pt、两字标签预算或纸纹装饰变成所有项目的默认模板。

## 可执行入口

`deck.json`可选`text_styles`保存当前JS后端完整样式；text对象以`style_role`引用，编译输出仍是既有`style`。示例字段如下，数值只展示契约，不是一套通用视觉设计：

```json
{
  "text_styles": {
    "section.normal": {
      "typeface": "Noto Sans CJK SC", "fontSize": 32,
      "bold": true, "italic": false, "color": "#244B58",
      "alignment": "left", "verticalAlignment": "middle",
      "autoFit": "none", "wrap": "none",
      "insets": {"left": 0, "right": 0, "top": 0, "bottom": 0}
    }
  },
  "slides": [{
    "id": "S01", "elements": [{
      "id": "section-label", "kind": "text", "text": "项目范围",
      "box": [80, 620, 360, 60], "style_role": "section.normal",
      "style": {"fontSize": 36}
    }]
  }]
}
```

这段是deck片段。可运行的完整合成样例见`examples/pptx-native-roles.json`，按[pptx-tools](pptx-tools.md)用现有`assemble_pptx.mjs`构建；无需生图。项目仍须验证实际字体与视觉，示例不提供字体文件。

合成顺序为角色完整style，再以对象style覆盖同名顶级字段。嵌套对象如insets整体替换，不能只提供一个方向又期待隐式保留其他方向。编译在副本中执行，保留原输入；未知角色、非对象角色/覆盖值报告页ID、对象ID与角色。未使用style_role的旧对象保持原协议。角色引用不自动改变文字内容、框或字号，不会启用隐藏缩字。

## 单位与后端适配

本入口的box和数字fontSize是96DPI的CSS px：`px = pt × 96 / 72`，PPTX几何`EMU = px × 9525`。不要把研究Python bridge的font_size、vertical_alignment等字段直接放进JS style。中英混排、基线、字距、段距、渐变等必须先查当前API；有格式节点不等于当前API能写或往返能保留。

样式源与能力记录分开：`text_styles`可复用参数，能力证据另按`backend/version或指纹 + renderer/version + font文件hash + recipe版本 + role`登记。改变这些条件后重新验证相关能力。style引用不会使未经实测的属性自动成为已支持属性，也不是PowerPoint主题的双向绑定。

## 固定槽位与完整状态

用稳定section_id决定本页当前章，为每个标签保留固定ID和框。每次状态改变从唯一源重建所有正常/活动样式，只移动需要移动的活动装饰；不沿上次状态只改一个color。重建器新建原生对象，因此不会继承旧活动对象的残留效果。

编辑导入对象时则必须额外检查：整体style赋值不应被假定能清除所有未提及属性。原对象带渐变、描边、阴影或run格式时，按当前API明确重设/清除并实测；不能把纯色研究例的通过扩展成高级效果清除保证。内容、整体样式、分段样式按固定顺序设置，整体样式之后的run样式必须重新应用。需要清除而当前接口无可靠路径时，从原样式源重建该组件或报告该效果的阻断，不擅自改全部页面。

切换后再切回，保存重开，逐一核对标签文本、字体/颜色/字号、四周净空、旧活动态残影与活动装饰坐标。清空可编辑文字后看装饰是否仍带旧字。视觉导航不自动包含点击跳转；链接需独立实现并在实际放映模式点击验证。

## 长文与字体

预检实际字体文件的家族/字重、字符覆盖和许可，再用代表角色真实导出验证。cmap和advance测量只能排除明显缺字或超宽，不等同PPT排版引擎；设置了字体名字也不等于实际渲染采用该文件。

用本项目实际可能出现的长标题、混排、数字与字号变化测试。先守住准确字面、固定邻居和已批准设计；在允许范围内换行、调宽或调字号，超出范围再问必要决定。每个角色的最小字号和长度预算来自当前设计，不采用统一二字上限。不要把缺字体或溢出直接转成图片来掩盖。

## 证据状态

分别保存written、imported、rendered、edited、saved_reopened、visual_pass、target_app_tested与实际文件/日志；未知为NOT_RUN，已观察失真为FAIL。测试多个属性不等于完成多轮验收。每轮复查须绑定精确源码版本、风险范围、实际输入/输出、观察与修复，新改动后重测受影响范围。

基础文字通过不意味着高级属性全部通过。渐变、描边、阴影、WordArt、字距、基线、中英文混排与目标应用各有自己的证据。研究包的Python bridge/LibreOffice记录是相关先验；当前JS和最终PowerPoint/WPS仍须分别实测。目标软件不可达时保留NOT_RUN/BLOCKED，不能把工具渲染成功改称跨软件通过。
