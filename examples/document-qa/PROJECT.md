+++
[[mainline]]
id = "goal"
section = "goal"
after = []
sources = []
[[mainline]]
id = "retrieval"
section = "retrieval"
after = ["goal"]
sources = []
[[mainline]]
id = "verification"
section = "verification"
after = ["retrieval"]
sources = []
+++

# 示例项目 · 文档问答探索

此项目用于功能展示，记录与数字均为构造的演示内容，不代表真实研究结论。

<a id="goal"></a>
## 回答必须有可核查的出处

让用户能够沿引用检查回答依据。

<a id="retrieval"></a>
## 先限定文档范围，再检查相关性

围绕检索和引用展开探索。本图中的设计与实验均是演示。

<a id="verification"></a>
## 保留可重跑的问答验证入口

让后续接手者找到验证命令、结果和未完成停点。
