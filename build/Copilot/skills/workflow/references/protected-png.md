# 指定PNG原件与精确槽位的只读核验

这个检查器读取现有PPTX和工程声明，核对指定PNG的原字节、所在页、图片对象及居中contain几何。它不修改PPTX、原图或组装器，也不制作新素材。图面遮挡、背景衔接和实际应用中的显示仍须看图确认。

先按当前Presentations完成作者编辑和严格finalizer，再对实际准备交付的文件运行本检查。已有文件也能检查，但须先取得真实页顺序、唯一图片名称和原件；不能用随意填入的声明替代来源、使用权限或完整PPTX有效性验证。金额和标题不在此检查器的职责内。

## 声明与调用

在已有deck.json中添加protected_media。每项对应slides中一个普通image元素，slide_id和object_id使用实际项目ID，file必须与该元素的file相同，sha256来自此前保留的指定原件。准确槽位沿用元素的box（CSS像素，xywh），不复制另一套坐标。原件变化时先核业务授权，不自动重算哈希来消除错误。

```json
{
  "protected_media": [{
    "slide_id": "S01",
    "object_id": "product-photo",
    "file": "input/product-original.png",
    "sha256": "此前登记的原件SHA-256"
  }]
}
```

此片段补入现有pptx-1工程；它不是完整deck。源对象须为image，使用contain且不提升到固定版式。调用位置是workflow根目录，PROJECT为实际工程目录，文件参数为工程内相对路径：

```bash
"$RUNTIME_PYTHON" scripts/verify_protected_media.py --project "$PROJECT" \
  --plan deck.json --pptx builds/B01/final.pptx --out evidence/B01/protected-png.json
```

RUNTIME_PYTHON需具备本包已锁定的Pillow；先用现有doctor核对环境，不另装替代后端。命令只读源文件，成功时以新文件保存完整回执，已存在的回执不会被覆盖。退出0表示所声明PNG的检查通过，退出2表示输入、支持范围或回执写入失败。失败不生成成功回执，不为通过检查重画原图或改写媒体关系。

回执包含实际PPTX SHA、每张原图SHA、页/对象/media部件、声明槽位，以及期望与实际EMU框。几何允许2 EMU以内的序列化取整差异，实际图片仍须完整在画布内。回执只对应被读取的文件字节；随后文件变化要重新核验。这个命令尚未自动接入assemble_pptx或发布包装器，仅增加声明不会自动触发检查。

## 精确支持与拒绝范围

- 原件为可完整解码的静态PNG，最大32 MiB、5000万像素；既校验PNG块CRC，也实际解码像素。JPEG改扩展名、APNG和损坏数据不进入此路线
- 每个声明在指定页对应唯一普通图片，原件路径/字节与嵌入媒体一致，实际MIME为image/png；支持非同名slide文件，通过presentation关系确定页序
- 画布两边为有限正数且各不超过100万像素，槽位为有限正宽高并完整在页内；居中contain保留原图比例
- 受保护图不支持分组、裁剪、蒙版、旋转/翻转、图片效果、隐藏、版式提升，以及媒体/占位元数据、点击动作或未知扩展。带视频元数据的poster不能算普通静态图通过。所在页也不支持隐藏、动画时序或非空页根变换；显式单位矩阵也未在此路线放行
- 复用有界OPC读取器，拒绝外部关系、签名/活动二进制部件、重复ZIP成员、越界路径、缺失关系目标和超过容量/XML边界的包。即使外链与指定PNG无关，这条保守检查路线也会拒绝

拒绝的是这项自动证明，不意味着整份演示不可制作。定位报错涉及的页/对象后，按当前Presentations可执行方式保留原生对象并核实实际结构；需要更复杂裁剪或分组时采用与请求相符的受支持路线，不能删除检查条件假装通过。不会自动扁平化、拆组或修复文件。

这不是通用media-slot框架。独立视频原件、外链、poster和真实嵌入视频是不同交付；本工具不插入视频，也不能证明播放。PNG回执不能标成视频通过。

## 维护者复验

```bash
"$RUNTIME_PYTHON" -m unittest discover -s tests -p 'test_protected*.py' -v
```

包内测试使用小型解析器夹具验证正反边界，不是用低级XML制作可交付PPTX。另以既有Artifact Tool B08真实PPTX及两原图跑过CLI，原字节与实际contain框一致；旧实验的画布、页根变换、页外框和不可解码PNG四个误通过均已复现并拒绝。0次生图，未验证PowerPoint/Slides桌面或视频播放。检查器通过仍不替代逐页视觉复核。
