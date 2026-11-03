# 质疑者接入与启动自检（v0.4.0）

Project Infra 不包含 Agent。它管理能力握手、交付检查点、项目写保护、异常与多轮意见；实际会话由你已有的工具提供，不限定模型、厂商、subagent 或独立进程。

审查是串行交接：执行者结束本轮写入 → 程序保存原权限并冻结项目 → 独立会话审查 → 程序恢复原权限 → 写回意见 → 执行者继续。审查阶段不允许项目修改。Windows 文件权限提供实际写保护，不使用密码或另建用户。

## 启动时：能力自检

执行者读 AGENTS.md 后先运行 `project-infra reviewer status`。便携/安装版的命令路径见项目 `.work/infra-runtime.md`；Python 安装版可使用 `python -m project_infra` 替代 `project-infra`。外部项目统一加 `--root 项目路径`。

未自检时默认关闭质疑功能，看板持续提示。不要因此自行安装另一个 Agent。可接入时选择下列任意一种方式；不能接入则运行 `project-infra reviewer disable --reason "当前工具无法创建独立会话"` 并告诉用户。

能力记录在 `.work/reviewer/runtime.json`，不作为可迁移的项目事实。工作台服务重新打开会重置能力；机器、用户、项目路径或程序入口变化时不复用旧结果。成功结果有效 8 小时，过期后重检。命令行操作自身不创建新工作台会话；请先启动工作台，再让执行者自检。

### 方式一：宿主 subagent / 自己管理的独立会话

```sh
project-infra reviewer probe --label "当前执行环境" --timeout 600
```

返回 `.work/reviewer/probes/<编号>/request.json` 以及建议的 response 路径。执行者使用宿主自身的能力，把 request 交给一个未参与本次方案和实现的独立会话。该会话只确认可接收上下文和返回意见，此时不要展开正式方案审查。响应为 UTF-8 JSON：

```json
{"nonce":"request 中的 nonce", "independent":true, "session":"新建会话的标识"}
```

将响应保存到 response.json 后执行：

```sh
project-infra reviewer accept --response .work/reviewer/probes/<编号>/response.json
```

程序检查请求对应关系、独立能力声明与超时，成功后开启质疑功能。这是接入能力握手，不是身份认证，也不证明审查质量或声明真实性。宿主应使用自己的工具实际创建独立会话，不应由执行者代替它返回响应。

### 方式二：独立进程适配器

在本机准备 JSON 文件，内容是适配器的参数数组，不能是 shell 命令字符串。例如：

```json
["D:/已有工具/reviewer-adapter.exe", "--profile", "review-only"]
```

然后运行：

```sh
project-infra reviewer check --label "本机审查工具" --command-file D:/本机配置/reviewer-command.json --timeout 600
```

程序实际启动适配器并进行能力握手。适配器负责调用你已有的 Agent 工具；它可以直接是支持协议的可执行文件，也可以是现有语言环境运行的包装脚本。不要求额外安装特定工具。HTTP 界面不能设置命令，只有本机命令行能配置。配置仅保留在当前项目的 .work 运行现场，不提交机器路径。

适配器协议：每次调用创建独立进程，工作目录为项目根目录；stdin 是一个 UTF-8 JSON 对象，stdout 只返回一个 JSON 对象，诊断写 stderr。程序保留 stdout.log / stderr.log。

自检输入：`{"action":"probe","nonce":"…","project":"项目绝对路径","instruction":"…"}`。输出与宿主模式相同：nonce、independent=true、session。

正式审查输入：`{"action":"review","id":"PLAN-0001","project":"…","context":"完整交接上下文","handoff":"本轮临时目录"}`。输出：`{"note":"Reviewer: …\n\n## 已核查\n…\n\n## 主要疑点\n…\n\n## 未覆盖与下一步\n…"}`。

每次正式审查必须新建一个未参与方案制定与实现的会话，不能恢复执行者的对话。适配器可复用登录状态和模型。原进程只输出意见，由 Project Infra 保存；不要让模型直接修改项目记录。项目写权限由 Project Infra 在启动前冻结；适配器只读取项目、输出意见，临时测试产物写本轮 checks/。托管进程的 TEMP/TMP 指向 checks/，Git 可选写锁关闭。

## 交付时：才启动正式审查

```sh
project-infra deliver PLAN-0001
```

也支持显式审查某个 Experiment。看板对象详情的“发起交付审查”调用同一个入口。兼容 `review <ID> --prepare`，该命令本身也表示显式交付审查请求；普通 context、run、verify、新建实验不会启动质疑者。

- 进程模式：程序启动已配置适配器，传入上下文，等待结果并导入。
- 宿主模式：返回 `.work/reviews/<ID>/<本轮>/`；项目已冻结；宿主新建独立审查会话阅读 context.md，填写 NOTE.md，结束本轮会话后执行 `review <ID> --record <NOTE相对项目路径>`。程序不直接控制宿主 subagent 的生命周期；宿主负责停止会话并交接，程序负责恢复权限及拒绝超时回传。
- 能力缺失：不调用审查者，Delivery 明确写“未执行独立审查：原因”；其他工作继续。界面仍显示功能关闭，不能将降级等同于通过。

同一对象不能重复并发发起待完成审查。需要取消时先 `reviewer disable --reason "取消本轮"`，重新接入后再发起。

## 异常与关闭

程序在项目外保存原权限备份（默认 %LOCALAPPDATA%/ProjectInfra/review-locks），再冻结项目所有普通写入；仅本轮 NOTE.md、stdout/stderr 日志与 checks/ 可写。context.md 和 manifest.json 同样只读。

收到本轮意见后，程序先恢复原权限，再校验和写回记录。异常退出、无效输出、空白意见不会记为完成；托管进程失败或超时会先停止进程再恢复。独立后台监护在主程序退出或截止时间到达时恢复权限，不依赖浏览器轮询；工作台重新打开项目也会先恢复遗留权限。

取消用 reviewer disable --reason "取消本轮审查"，程序先恢复写入，再关闭审查能力。宿主模式需先由宿主停止独立会话；程序不能替外部宿主终止 subagent，超时回传会被拒绝。

冻结前检查文件系统及原权限，不能建立保护就不启动审查。当前实现使用 Windows 持久文件权限；遇到不支持的文件系统、重解析点或硬链接会拒绝，避免改变项目外目标的权限。恢复失败保留备份并报告错误，不声称已恢复。

只有能力启用时，非放弃 Plan 的关闭才要求当前内容对应的本轮交接记录。先保存候选方案、发起审查，再按原有要求 verify、最后 close；关闭时不能同时修改候选内容。修改后需要重新审查。意见内容是否足够、方案是否采纳由用户/执行者判断，程序不评判思考质量，也不验证审查者诚实。

能力关闭时允许结束 Plan，但程序自动写入未执行独立审查的 Delivery。普通 Experiment 结束和放弃 Plan 不强制审查，避免每个实验都调用。已有关闭对象不会被升级自动重新审查；重新打开后按当前流程处理。

审查阶段不仅 CLI/Web 拒绝写入，直接覆盖、新建、删除、重命名项目文件也会被本机文件权限拒绝。恢复之后才允许继续编辑。validate 仍不证明审查内容真实。

## 往期意见

每轮成功意见追加到 Plan / Experiment 的 Review；原始 note 和时间、来源指纹、轮次元数据原子写入 `.project/reviews/<ID>/`，建议随项目 Git 提交。这是附属审查记录，不增加工作对象或状态。

reviewer 上下文包括相关对象的历轮意见与原始记录路径。新一轮注明复核哪条旧意见及结果，不自动让旧问题消失，不把多轮判断改写成一个“合并结论”。v0.2 的已有 Review 会保留，新轮次从其后追加。尚未导入的 .work note 只是现场，清理前先导入有效意见。

## 版本阶段

当前为 0.x 探索阶段，不承诺跨版本兼容；正式版从 1.0.0 起定义稳定格式与升级规则。

测试中的 tests/reviewer_fixture.py 只是协议夹具，不调用模型，不能用它代表真实质疑者或研究结论。
