# 恢复原图表工作簿依赖

这个入口用于一个已验证的窄情形：Artifact Tool 完成文字编辑并导出后，保留了原生图表及其缓存，却丢失了原工作簿、图表关系和 externalData。工具自动证明原依赖与作者输出仍然对应，只恢复原字节，再运行当前 Presentations 的严格 finalizer。

它不编辑标题、正文、价格或备注，不创建替代工作簿，也不修复任意 PPTX。先按当前 Presentations 用 Artifact Tool 完成内容作者步骤。不能为了使用本工具把其他文稿改造成以下结构。

## 当前接受的结构

- 整个文稿只有一个原生 barChart（横条或柱状图），由一张幻灯片唯一持有
- 原稿和作者导出的 chart part 路径相同；移除原 chart 的唯一 externalData 后，整个 XML 语义树与作者输出一致，包括类别、数值、轴和样式
- 原 chart 只有一条内部 package 关系，指向原稿中唯一的 xlsx；作者输出恰好丢失该关系 part、xlsx 和 xlsx content type
- 原工作簿恰好是五个部件：Content_Types、根关系、xl/workbook.xml、其关系、xl/worksheets/sheet1.xml；使用 inlineStr 和数值单元格
- 工作簿只有一张表，无 styles、sharedStrings、公式、宏、外链、命名区域或额外元数据。一般 Excel 保存的单表文件常带其他部件，不能据“单表”判断其受支持
- 每个系列都有 strRef 类别和 numRef 数值，引用同一张表内的单列绝对连续范围；工具逐点核对全部缓存和原单元格，保留系列与点位顺序
- 全包无外部关系、宏或签名。ZIP 不得含重复成员、目录项、非规范路径、越界目标或缺失关系目标
- 文件与单层解压总量各不超过128 MiB，成员不超过2000；XML不超过8 MiB、深度不超过64；单条引用不超过10000个点、系列不超过16个。数值文本最多128字符、34位有效数字，十进制数量级限于-308到308

不满足任一条件就返回稳定错误码；原文件继续保留。不要删除检查或自填“已证明”来放行。其他商业材料仍按完整工作流处理，必要时保留原件并报告不支持的具体结构。

## 调用

Python运行部分仅使用标准库。最终验证依赖当前宿主的 Presentations 和它提供的运行时；先依其 implementation.md 设置环境。RUNTIME_PYTHON、RUNTIME_NODE_MODULES、PRESENTATIONS_SKILL_DIR必须为当次实际绝对路径。

```sh
"$CODEX_PRIMARY_RUNTIME_NODE" finalize_restoration.mjs \
  --source /path/original.pptx \
  --authored /path/artifact-authored.pptx \
  --out-dir /path/new-output-directory \
  --requirements /path/requirements.json
```

requirements.json只描述本次请求的页数、画布和原字体，例如本仓库的 resources/requirements.json。工作簿和图表身份不由调用者提供，工具在同次调用内从实际输入计算。输出目录必须不存在且其父目录已存在；工具不会复用或覆盖旧输出。

成功文件是新目录中的 output/final.pptx。candidate.pptx以及verified目录中的文件属于诊断材料，不能交付。proof.json记录实际输入/依赖哈希与自动验证结果，validation.json记录实际 finalizer 验证。只有严格验证及输入身份复查全部通过，才通过同文件系统的排他硬链接原子发布output/final.pptx。finalizer失败或输入在验证期间变化时，交付路径不会出现final文件；诊断材料保留，原文件不覆盖、不回滚。文件系统若不支持硬链接，发布会明确失败，不能静默降级为非原子写入。

单独诊断可调用 restore_chart_dependencies.py，参数为 --source、--authored、--out-dir。退出0仅表示依赖候选已写出，2表示输入不受支持，3表示文件访问或写入失败。生产交付始终使用上面的严格入口。

## 已验证范围

真实回杯站案例的原图表4个引用、2个系列、12个数值均自动核对；只恢复原chart、关系及xlsx三个部件，并补回原xlsx声明。原生图表与原工作簿强制检查通过，未生成快照。作者输出的所有slide和notes字节不变。

85项Python测试覆盖正例、第二套一致数值、歧义/不支持输入、ZIP/XML边界、文件写入失败、输入变化及真实CLI退出码。Node包装层用明确的finalizer测试替身检验拒绝、部分写入和输入变化时无final残留；这些替身不作为实际PPTX验证。真实集成另使用当前Presentations finalizer并回读五页PNG。

未宣称在PowerPoint或Google Slides桌面实测，也未宣称支持复杂Excel工作簿、多图表、其他图表类型或任意外来PPTX无损编辑。

```sh
python -m unittest discover -s tests -p 'test_*.py'
```
