---
name: project-infra
description: 接手或维护由 Project Infra 管理的项目，定位 Plan、Experiment 和交接记录，使用 project-infra CLI 查询、更新和验证项目。适用于有 .project/config.toml 的项目。
---

# Project Infra

1. 从用户指定目录或当前工作目录定位含 `.project/config.toml` 的项目根，读取项目的 `AGENTS.md`。从其他目录调用时，在子命令前加 `--root <项目根>`。
2. 优先采用 `.work/infra-runtime.md` 记录的 CLI 入口，否则使用 PATH 上的 `project-infra`。按需查子命令的 `--help`。接手时用 `status` 看全局，再对相关 ID 用 `context <ID>`，读所属 Plan 的执行计划和对象的 Continuation。
3. 开始执行前用 `reviewer status` 检查审查能力。若不可用，按项目的 `docs/reviewer-integration.md` 检查已有接入方式；无法接入时记录原因并告知用户。正式独立审查只在显式交付点通过 `deliver <ID>` 发起。
4. 用 `new` 创建对象，用 `edit` 或直接编辑对应项目文件更新记录。记下实际证据、结论和未完成工作的继续条件，修改后运行 `validate`。Plan 交付或结束前检查执行计划里的共享实现整理步骤及实际结果。
