# 文档范围检查的适用边界（演示知识）

在本例中，项目范围由文档的 project_id 决定。共享代码先筛选范围，再拒绝不在允许集合中的引用，包括根本不存在的编号。
这能检查引用是否属于给定范围，不能证明回答内容正确，也不能证明文档元数据本身正确。不能用范围检查通过代替语义正确性验证。

来源：[EXP-0002](../.project/experiments/EXP-0002.md)、[EXP-0004](../.project/experiments/EXP-0004.md)。实际共享实现位于 [shared/documents.py](../shared/documents.py)，不依赖实验目录。

在本示例项目根目录可重跑：

```sh
python -m experiments.exp_0002
python -m experiments.exp_0004
```

这里没有把演示表格中的百分比当作知识依据；规则只对应构造输入和可执行代码。
