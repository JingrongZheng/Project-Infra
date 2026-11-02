# 开发者 Agent 入口

这是 Project Infra 应用源码仓库；用户项目由程序初始化，模板在 project_infra/bootstrap.py。源码仓库与被管理项目的文件不要混淆。

| 需要什么 | 去哪里 |
|---|---|
| 产品目标、当前功能与使用流程 | README.md |
| 模块结构、验证和构建 | docs/development.md |
| 设计、知识、共享实现与质疑者的关系 | README.md 的设计章节；代码在 bootstrap.py、service.py、review.py |
| 版本与升级边界 | project_infra.__version__、CHANGELOG.md |
| 安装版及便携版操作 | docs/install-wizard.md、docs/portable-use.md |
| 明确标注的演示项目 | examples/document-qa/ |
| 许可与第三方资源 | LICENSE、THIRD_PARTY_NOTICES.md、licenses/ |
| 文件规则与状态 | project_infra/documents.py、validation.py |
| 可复用服务与事务 | project_infra/service.py、store.py |
| 图布局和路由 | project_infra/static/graph-layout.js |

若本地另有 PROJECT.md、TOOLKIT.md 和 .project，它们是维护此应用时的私有开发现场，可按需阅读；不会随公开源码默认上传。

开始前检查 Git 工作区，保护已有改动。浏览器与 CLI 复用同一套校验/存储规则，不另写业务副本。图关系从文件读取，不依赖编号顺序，不为演示数据硬编码坐标。
功能图必须从真实运行页面截取；演示项目和虚构指标要显式标注，不能冒充实际测量、用户验收或独立审查。
修改后运行与改动有关的检查，必要时更新文档与接续说明。构建产物和 .work 现场不提交，Release 附件与源码分别管理。
