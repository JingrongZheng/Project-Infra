# 项目共享代码与工具索引

真实代码在项目级 shared/documents.py，不属于任何实验；实验通过正常模块导入，不修改 sys.path。

| 能力 | 实际入口 | 使用者 |
|---|---|---|
| 读取示例文档 | shared.documents.load_documents | 两个实验入口 |
| 按项目限制范围 | shared.documents.within_project | EXP-0002 与引用核查 |
| 拒绝越界或不存在的引用 | shared.documents.invalid_citations | EXP-0004 |

从本例根目录运行 python -m experiments.exp_0002 或 python -m experiments.exp_0004。
实验只组织本次输入、调用与结果断言，共享代码可以在移除某次实验后继续复用。
