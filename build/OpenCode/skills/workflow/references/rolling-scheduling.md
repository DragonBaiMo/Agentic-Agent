# 滚动调度与实际计时

多页、多个语义层或需要恢复时使用。单幅简单任务可以沿用 image_job.py；不要为了启用调度重写已有 deck、素材或批准记录。

## 一条执行路径

1. 内容定稿时就确定每页文字、数字、编辑对象和共享视觉令牌。复用现有 content.json；只在需要独立失效时拆成 pages/S01.json 等文件，不增加一份内容副本
2. 代表封面和信息内页确定方向后，立即让其他母图与代表页提层/真实重组交错。代表页证明拆层方法，不能无故阻塞独立母图
3. 每页母图返回，马上持久化与登记；看实际图，核对全部文字、数字、主体后采用，释放该页提层。不要等全部母图
4. 每个语义层返回立即登记。裁边、坐标资源和轻量页预览按页推进，共享 JSON 由单写者提交；不要一层一次完整 finalizer
5. 全部页面资源与代表页方法就绪后，才汇合成一次正式组装、实际回读、全套视觉审阅和关键编辑验证。局部错位先改坐标预览，艺术或语义问题只重做责任层

调度不减少艺术设计、真实分层、必要原生内容或验证。采用表示执行者已经完成原有质检，不增加逐页用户审批，也不替用户作出新的方向决定。

## 可执行边界

`scripts/schedule.py` 是持久状态/收据协调器，不调用图片模型。它用 Python 标准库 SQLite 序列化短写事务，不增加第三方依赖。当前宿主仍通过真实图片工具调用模型，工具参数、权限与返回文件以当次发现的 schema 为准。

有 Python 异步适配器的宿主可直接调用 `scheduling.run(coordinator, invoke, inspect)`。它每项返回就落盘并登记，视觉检查串行但不拖住其他结果登记。适配器契约：

- `invoke(claim)`：真正执行 claim 指定的一项已授权任务；返回 `{"source": 实际本地文件}`，图片可另附下述 image_record 和实际 timing
- `inspect(claim, state)`：使用已登记文件完成该项需要的真实检查；通过返回 True；需要局部修复返回 False，原结果保留，只有其下游等待
- 确认无结果的临时失败可以抛 `ServiceFailure("transient")`；明确限流用 `ServiceFailure("rate_limit", retry_after_seconds)`；其他异常/超时默认 unknown
- `timeout` 默认600秒，`deadline_seconds` 默认3600秒，是可配置的调用/本次运行保护，不是图片服务 SLA。超时不会自动补发；实际任务需要更长时在调用前设置合理值

原生工具只存在于宿主 JavaScript 执行单元、无法从 Python 调用时，使用下面的 CLI 事件接口。不要假装 Python 可以调用未暴露的模型 SDK，也不要为了接入去安装用户 Codex、另建未获授权任务或绕过工具权限。

## 最小计划和 CLI

所有命令从 workflow 目录执行；PROJECT 为本次独立生产工程。例子 `examples/rolling-deck.schedule.json` 展示真实依赖，但 pages 文件须替换为本次内容。每任务只必需 id，depends_on 默认为空；仅在确有依赖时填写。

- `input_files`：项目内已存在的直接输入，按真实文件字节哈希；不同页应引用自己的内容，避免改一个时间牵连整套
- `input_version`：无法用文件表达的既有视觉决定版本，改变时明确更新；不是自动生成的批准记录
- `depends_on`：必须已经采用的父任务；哈希包含父任务版本，领取时还记录实际父结果哈希
- `priority`：可选整数；同等就绪条件下优先已完成页的后续工序，默认0
- 其他 spec 字段交给当前适配器，不会当 shell、表达式或模板执行

准备 init.json：

```json
{"plan":{"schema":"schedule-1","tasks":[
  {"id":"S02-master","input_files":["pages/S02.json"]},
  {"id":"S03-master","input_files":["pages/S03.json"]},
  {"id":"S02-title","depends_on":["S02-master"]}
]},"window":2,"max_attempts":3}
```

```bash
python scripts/schedule.py --project "$PROJECT" init --payload "$PROJECT/init.json"
python scripts/schedule.py --project "$PROJECT" next
```

next 原子领取 ready 项，返回 id、attempt_id、spec、input_hash；领取不是模型已提交。窗口从2开始可作未知环境的保守试验，宿主公开上限优先。2/4/32都不是供应商承诺：32只是本地误配保护，不建议默认提高。只在真实吞吐与延迟/错误支持时试4；没有数据不自动升窗。

每个独立调用使用自己的返回回调。宿主的推荐循环是：

```text
next → 对领取的每项立即提交真实工具调用
某项返回 → 保存原始文件/公开参数 → return → register → 立即 next 补空位
对已登记图做实际检查 → adopt → 立即 next 释放本页下游
明确失败 → fail → 根据 retry_at 和仍在途任务等待，局部补位
无在途、无可到期重试 → 查看是否完成，或报告 unknown/缺输入/未通过检查
```

使用 Promise.all 时，必须在各个 Promise 的回调里消费结果，不能把最终 Promise.all resolve 当唯一消费点。保持本次宿主执行单元存活直到所有已提交 Promise 都已记录结果；禁止发出工具调用后丢弃未等待的 Promise。共享 deck/data/bindings 更新排在单写者队列；其他独立调用继续在途。不要让长分析、下一批提示词或用户进度汇报插到“已返回→登记”之间。

原生桥接必须实测：先在回调记录返回时间、真实路径和最小状态，再请求落盘登记，最后才展示图片。2026-09-30 的三次真实小链路中，两项同刻提交，较快项52.884秒返回，但实际登记滞后44.848秒；另两项登记约0.28秒。该回调把 generatedImage 展示放在登记之前，展示/跨工具派发哪一层等待尚未隔离。不能把“回调里调用了登记工具”写成“实际已即时消费”。

若宿主不能在另一图片调用在途时执行本地工具，保留内存/store中的返回证据，采用小窗口（必要时1）并尽快完成单写者登记，明确报告剩余消费滞后。首项可见即 yield 给主层、或从返回通道直接触发下游，只有该宿主实际支持并经过验证时才采用；需要视觉判断的下游仍先看图，不为填满窗口盲目采用素材。不要再造后台服务、绕过访问权限或无限增加调用试验。

return 的 payload 例子：

```json
{"identifier":"S02-master","attempt_id":"next返回的原值",
 "source":"真实工具返回的文件路径",
 "timing":{"clock_id":"本次调用计时器身份","basis":"actual_tool_boundary",
   "submit":{"utc":"2026-09-30T14:00:00+00:00","monotonic_ns":1000000000},
   "return":{"utc":"2026-09-30T14:00:42+00:00","monotonic_ns":43000000000}},
 "image_record":{"origin":"generated","tool":"本次真实工具名",
   "call_id":"真实调用ID，未暴露可省略","execution":"calls/S02-public.json"}}
```

例中时间和ID只说明 schema，严禁复制为生产证据。执行文件仍使用 image_job 的三字段白名单，真实附件在项目内保留副本。source 可以是宿主给出的获准原始文件；协调器复制到任务专属不可变目录，不把整份工具响应或凭证写入收据。

```bash
python scripts/schedule.py --project "$PROJECT" return --payload "$PROJECT/events/return-S02.json"
python scripts/schedule.py --project "$PROJECT" register --payload "$PROJECT/events/id-S02.json"
python scripts/schedule.py --project "$PROJECT" adopt --payload "$PROJECT/events/id-S02.json"
python scripts/schedule.py --project "$PROJECT" report
```

register/adopt 的 id payload：`{"identifier":"S02-master","attempt_id":"实际attempt_id"}`。return 先原子保存返回字节；register 才更新共享收据。采用不自动改 deck.json。图片登记复用 image_job.py，record_id 防止“收据已写但状态未提交”崩溃后的重复条目。调度运行时不要另起直接 image_job record 写同一个 receipts.json。

## 限流、未知结果与恢复

fail 的 payload 包含 identifier、attempt_id、kind，以及可选 retry_after（秒）、timing。HTTP Retry-After 日期必须由当前适配器按实际响应换算成非负秒，不猜隐藏限流。

- transient / rate_limit 只用于**确认没有可采用输出**的失败；指数等待2、4秒加抖动，默认最多3次总尝试，含首次。Retry-After 是最低等待，不提前补发。限流把未来窗口减半；不强行取消已在途调用
- unknown 用于结果不明的超时、断连或宿主中断。占用一个可能仍在途的窗口，不自动补发。先查原调用和实际返回文件；找回结果用原 attempt_id 执行 return。只有核实该次确无结果后，才能把同一尝试 fail 为 transient/permanent
- permanent 保留失败分支，独立页照常。达到尝试上限转 failed；需要新方案时改责任任务版本，不能无界重置上限
- 收据/登记错误发生在模型返回之后，重做 register，不能重做模型调用。质检未通过的图片保留 registered，修改责任任务 spec/version 后局部恢复

旧宿主调用循环**已经停止**后运行 recover：running 转 unknown，returned/registered/adopted 保留。仍在调用时不要执行 recover。接着核对原任务；重新进入 Python run 会消费 returned/registered 素材，不重新生成。CLI 路径手动继续 register/检查/adopt。

变更内容或参考后用 reconcile，payload 是 `{"plan": 完整的新计划}`。它重算直接输入和依赖版本，仅失效变化任务与下游，归档旧状态和输出。仍 running/unknown 时拒绝换计划，先核实在途结果。采用的已有文件丢失或变字节时拒绝静默复用；先恢复正确文件或明确建立新版本。不能原地替换素材后仍沿用旧输入版本。

## 看什么指标

每调用在真实工具边界记录 UTC、单调时钟 submit/return，包含成功与失败。只有调用两端使用同一时钟时才算持续时间。CLI 自己的领取/落盘时刻不能冒充工具 submit/return；缺失填 null。Python runner 默认记录适配器入口/返回边界，适配器内部若还有准备必须单独注明，或传真实工具边界 timing。

report 输出调用 P50/P90、ready→claim、return→register P90、已测客户端在途峰值和每分钟完成数。登记滞后跨宿主用 UTC 对齐，时钟偏差可能影响结果；负值保持未知。重启后不直接相减跨时钟的单调值。数据库保存逐尝试而非只保存批次总时间。

宿主没有单调时钟时，submit/return 中的 monotonic_ns 都为 null，保留真实 UTC。报告明确标记 UTC_wall_clock_only；不能伪造单调值。UTC差值可能受时钟调整影响，不和单调测量混称同一种精度。

成功结果到登记 P90<10秒是下一次真实生产的待检验目标，不是艺术质量门禁。分别记录内容/提示准备、实际看图、坐标、组装回读、交付的主动耗时；模型等待可能重叠，不能直接相加。预算超出先消除重复准备/全套重建，不删信息或关验证。

运行 `python scripts/benchmark_schedule.py --out /new/local-benchmark.json` 可比较串行、窗口2的整批屏障、滚动窗口2/4。它的 asyncio.sleep 模拟延迟，实际测的是本地调度墙钟和登记开销；结果不是图片服务吞吐、不是新的六页生产时长。真实改善幅度仍需同类型完整任务和相同质量要求下复测。客户端 Promise 数量、文件 mtime、窗口配置均不能证明服务端排队或 GPU 并行度。
