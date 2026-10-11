# DTB完整子树结构基础层

时间：2026-10-11T11:17:57.488431-07:00；基线8ef2641。仅国行wayne/SDM660静态分区实验；合成fixture不代表真实设备，与Miku UI无关。

做了什么：将read_dtb_identity.py的v17 walker拆为read_tree(bytes)通用索引，read_identity继续从同一验证后的树取得根model/compatible，保持原输出字段。索引记录规范节点路径、节点/属性token的DTB绝对偏移、属性值绝对偏移、长度、原始hex和快照SHA256；只接受不可变bytes，不重读路径，不修改原件。保留magic、偏移、块重叠/对齐、reservation终止、token、NUL、填充与嵌套检查，拒绝重复节点/属性、非法路径组件和属性名。整个结构成功才返回，异常不返回部分索引。

边界：8MiB输入、16384节点（含根）、65536属性、128层（含根）、单属性1MiB；65536引用边仅预留常量与输出说明，reference_edges=null，不解析也不计数引用，不声称已实现引用上限检查。语义输出semantic_extraction_implemented=false、build_gate_authorization=false；通用结构解析本身不执行wayne认证，既有导入入口继续拒绝jasmine根身份。

发生了什么：新增四项实际二进制测试，覆盖嵌套树、绝对偏移回读、重复/非法路径/属性、未知token、每个截断长度、缺节点/属性名NUL、可变输入拒绝。节点/属性/深度/单属性尺寸均测试生产上限接受与超限拒绝，输入8MiB超限拒绝；数量/大载荷向量在测试时生成真实二进制，不mock限额或解析结果。仓库小fixture tree-nested.dtb由测试中的nested()重现，不含真实板级事实。

首次直接运行发现未知token fixture编码错误；记录执行后又发现边界fixture无属性时生成空字符串块，触发现有拒绝规则。两处均修正生成器，未放宽解析器。失败和成功日志保留；最终四项新测试加九项既有根身份/导入/门禁回归共十三项通过。jasmine伪装使用既有二进制fixture，导入仍拒绝。两个真实6.6 preflight均返回2，五项保留材料哈希未变。

可直接执行：

```sh
python3 tools/test_dtb_tree.py
python3 tools/test_dtb_identity.py
python3 tools/test_wayne_board_evidence.py
python3 tools/test_6_6_gate_integration.py
```

API用法（只读本地小文件；实际入口仍需先做8MiB有界读取）：

```python
from read_dtb_identity import read_tree
with open("local-reference.dtb", "rb") as stream:
    tree = read_tree(stream.read(8 * 1024 * 1024 + 1))
```

下一断点：树结构层已实现；下一阶段先审阅phandle/linux,phandle唯一索引和有类型引用规则，之后才考虑memory-region/reg/reserved-memory及GLINK/RPMSG/SMEM。remoteproc候选分类、任何引用或数值解码仍为[设计状态](dtb-remoteproc-extraction-design.md)，未输出合格语义提取结果，未接入导入入口的新选项或构建放行。现有工具优先的根身份导入行为不变，外部工具快照一致性扩展仍待后续处理。

[断点与结果](../research/dtb-tree-stage/checkpoint.json)，[带时区记录](operations/dtb-tree-2026-10-11.md)。4.19/6.6实验及实验包未替换，未改固件、DTS、内核配置、init或fstab，未写sysfs/触发SSR、下载、编译或打包。boot/ABI/固件证据缺口与DTB阻断保留；无真机测试，不宣称任何remoteproc或硬件可用。实时额度不可读取，48%/79%仅用户快照；同步后立即暂停。
