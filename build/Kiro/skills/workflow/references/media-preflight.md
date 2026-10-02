# 现有PPTX的音视频预检与已知往返边界

需要保留现有PPTX内容时，在当前JS导入/编辑/导出路线之前检查原包。视频可能只显示为一张poster，不能凭渲染图或普通image对象清单判断原文件没有视频。

## 执行入口

从workflow根目录运行，原文件只读，JSON回执可以保存在本次工程的evidence目录：

```bash
python scripts/inspect_pptx_media.py /actual/source.pptx
```

| 状态与退出码 | 含义与下一步 |
|---|---|
| CLEAR，0 | 未检出本检查器覆盖的音视频标记，可继续既有对象/内容/编辑校验；不是完整保真批准 |
| BLOCKED，2 | 发现音视频关系、播放对象或实际媒体部件；保留原件，停止当前JS往返，选择当前宿主允许且已验证对应保媒体能力的后端 |
| UNKNOWN，2 | ZIP/XML损坏、声明冲突、超过检查边界或无法可靠判定；先解决具体读取问题，不把未知当无媒体 |

`verify_pptx_edits.mjs`已在加载作者库、创建输出目录和导入原PPTX之前调用同一检查器。阻断时不产生候选PPTX。其他自定义导入脚本也要先使用此入口；它不是为任意外部脚本提供全局拦截。本流程新建deck只接受既有对象kind，尚无video/audio作者对象，不可把媒体文件谎报为PNG。

有合适后端时，单独验证原媒体字节、嵌入/外链方式、关系、框和播放行为，确认后再用于任务。没有合适后端时，暂停保媒体分支并继续独立工作。用户明确接受改交付形式后，才可另交poster加原视频；不能默认为用户接受，也不能用删除媒体标记的办法让预检放行。

## 检查什么

- 按关系类型识别embedded与external的video/audio/media，不依赖文件扩展名；从不访问外部目标，也不把可能带凭据的完整URL写入回执
- 扫描包内XML与关系，包括隐藏页、备注、母版和版式；识别DrawingML视频/音频、p14媒体及播放对象
- 按实际部件的ContentType或音视频文件名发现媒体，区分referenced_media_part和orphan_media_part；回执注明按MIME还是文件名识别。只是存在未使用的video/mp4默认声明，不会误报为实际视频
- 普通image关系、ppt/media里的PNG、普通外部超链接，以及正文出现“video/audio”等词不会因此阻断
- 保留原包SHA-256及具体部件/关系ID。源文件读取前后大小或修改时间变化，返回UNKNOWN

此检查不解码图片/视频、不检验全部二进制CRC，也不证明播放或所有OOXML语义。每个XML最多8MiB、XML合计64MiB、文件部件最多10,000个；加密、DTD/实体、当前不接受的XML编码或超限包返回UNKNOWN。发现损坏不会尝试修复原文件。音频属于当前路线未验证的保留能力，不能声称已有音频丢失实测。

源文件变化检测比较读取前后大小和mtime，不防御恶意保持两者不变的并发改写；继续使用独立源副本与工程单写者。SHA用于辨认本次读取的原包，不把轻量预检描述为文件系统沙箱。

## 已观察的失败样例

2026-10-01的JS样例使用`@oai/artifact-tool 2.8.59`、供应运行时包`26.903.11726`。源包只读，往返结果是研究副本，不作成品交付。

| 原样例 | 实际媒体 | 当前JS导入再导出 |
|---|---|---|
| [LibreOffice tdf106867.pptx](https://github.com/LibreOffice/core/blob/master/sd/qa/unit/data/pptx/tdf106867.pptx) | 内嵌AVI，media/video双关系 | 视频、对应关系和videoFile丢失，只剩poster，FAIL |
| [python-pptx固定提交的shp-movie-props.pptx](https://github.com/scanny/python-pptx/blob/278b47b1dedd5b46ee84c286e77cdfb0bf4594be/features/steps/test_files/shp-movie-props.pptx) | 7.16秒、312×450 H.264 MP4，470,987B，无音轨 | MP4、对应关系和videoFile丢失，只剩166,499B poster，FAIL |

AVI源SHA-256：`d46a098caa019a2219ac91592c6e1e444cc9cafb207895208390092ef70c28ed`，Git blob：`5bf16d690ef21e2bb3c9f12f5437cae248b3d245`。

H.264源PPTX SHA-256：`aadd42367aff257e8e6aefc8d22b28351982c481464a616d588d4ffe2bbf5f83`，Git blob：`cc135e8a9e968faa4a4ea6c2360a1cc5296ee1b1`。原MP4 SHA-256：`6c3f6ef92428ede25a6fe8becdf3997e4d7630c08a3646461c81e89eae0799d1`。JS输出SHA-256：`21120815878785663ffac7f702ce88277e2824c4f71daf8d12a80cc2687bee21`。

同一H.264源经本次供应`soffice`入口重保存，输出7,144B，视频与poster部件、media/video关系、videoFile和p14:media均丢失，仅残留timing中的video节点。输出SHA-256：`28d547c37a108eca2b37d61bf80351140162f386d236cc90a8b69c6f4ca4889b`，所以这条入口也不是已验证的保媒体替代路径。入口报告`LibreOfficeDev 26.8.0.0.alpha0 2c87e51eeaa2b413ff4ae097b2705eea1995d8e5`；启动链和本地oosplash进程已观察，最终soffice.bin未直接采样，不据此推断其他LibreOffice发行版的结果。

H.264+AAC组合、实际播放、Windows/macOS PowerPoint、WPS均为NOT_RUN。上述失败只界定所测文件及后端，不能推导PPTX格式本身不支持视频，也不能泛化到所有MP4编码或库。
