# 1.2.0 到 1.3.0：功能去向

1.3.0 以兼容新增为主。原 PSD 工具和数据协议保留，完整主流程移入 psd-production，主入口按格式路由。没有拿缩短篇幅当作删掉生产步骤的理由。

| 能力 | 1.3.0 可执行位置 |
|---|---|
| 内容、受众、叙事、准确完整文案 | SKILL 前置 consumer，dependencies-and-start，PPTX content 资源 |
| 单方案、多候选、已有图 | 主入口选择；PSD 原 init/record/gallery；PPTX jobs、实际完整候选 |
| 视觉方向与编辑架构确认、全自动 | interaction-and-layers 保留；PPTX 增加普通页/版式/母版和编辑频率 |
| 完整母图与艺术文字 | 共享流程；PSD design/typography；PPTX 全页含导航/固定文案设计 |
| 七类语义、所有权、遮挡、背景补全 | PSD 原 plan、visual-production；PPTX 语义职责和逐页提取 |
| 原位尺寸、合理注册、透明软边 | 原 crop/destination 保留；新增 crop_alpha 的裁框与坐标补偿 |
| 真实图片调用、准备与结果区分 | PSD visual_job/record_asset；PPTX image_job 复用 execution_record |
| 来源、历史复用、失败隔离 | 原 receipts 协议保留；PPTX 独立 receipts，不重写旧项目 |
| PSD 简单原生 Type、图片字、组和混合 | assemble.cjs、contract/render、manifest；功能不变 |
| PSD 双解析、隐藏/移动、HTML 诊断 | verify_psd/review_psd/review_assets 原工具；不新增伪造实机声明 |
| PSD 状态、快照、恢复、打包 | project.py 与 deliver_project.py 原命令不变 |
| PPTX 统一背景与章节 active | design-system 的共用状态 + deck 页状态；真实 slideMaster/slideLayout |
| PPTX 艺术导航与固定文案 | 完整页设计后语义提层；不退回默认小字和下划线 |
| PPTX 原生文字/图表/表格 | render_objects 与 assemble_pptx；保留真实数据工作簿快照 |
| 数值源与艺术标签同步 | pptx_project、pptx_backend/contract 的 data/art bindings，过期生成替换任务 |
| PPTX 实际编辑测试 | verify_pptx_edits，另存再开诊断副本；正式文件与诊断分开 |
| 局部修复与中断恢复 | PSD 原 snapshot/resume；PPTX 新版本目录、resume 和具体错误恢复 |
| 真实交付与源包 | 交付成品/预览/编辑说明；格式对应配置、素材、来源和依赖，不打包私有运行时 |
| 历史例图回放 | Future Lab 继续保留；G05 是本次验证资产，不成为所有新作品的模板 |

包内 source-capability-map 是 1.1 来源历史，release-validation 是 1.2 实测历史；不可把其测试数字当 1.3 结果。本次新增验证以外层“变更与验证”交付文件为准。

保留的边界：不新增 Photoshop 高级蒙版/智能对象、CMYK、复杂 Type 塑形；不承诺 PPTX 动画/内部链接/跨平台主题自动替换；不恢复 SSIM/像素百分比艺术门禁；不把旧的未复现显示异常当已证实程序 bug。
