# memory-region纯phandle列表只读基础层

时间：2026-10-11T14:13:34.048416-07:00；基线e6ffcac。仅国行wayne/SDM660静态分区6.6实验，与Miku UI无关；合成fixture不代表实际wayne布局。

做了什么：新增tools/dtb_memory_region.py的decode_memory_region(bytes, source_path, property_name="memory-region")。从同一不可变快照只读树，再复用完整唯一索引的内部构建函数；旧build_phandle_index公开API保持行为不变。仅允许memory-region，其他属性名称明确拒绝，绝不把带provider参数的字段当纯列表。

属性必须存在、非空且长度为4的整数倍，每个单元按大端uint32解析，拒绝0/0xffffffff及完整唯一索引中缺失目标。来源节点须以真实规范路径存在。全部校验成功才返回tuple，成员为冻结ReferenceEdge：来源SHA256、来源规范路径、属性名、cell序号、DTB绝对值偏移、phandle值和目标规范路径。失败抛ValueError并附相关位置，不返回部分边；先完整索引所以支持前向目标，重复引用保持原顺序和独立cell位置。

65536边上限落实于每次明确请求的一个列表结果，超限在解码前拒绝；本轮没有全树引用图API，也不宣称多个列表合并后的全图边数已受检。继承结构与声明的全部边界/冲突拒绝；不验证目标是否reserved-memory、不解码reg、cell宽度或数值，不分类remoteproc，不推断运行关系、循环或启动时序。

发生了什么：八项新二进制测试与原十八项回归，共二十六项通过。覆盖单/多目标、前向目标、重复顺序、偏移回读、冻结结果、缺目标（含有效前缀后失败无返回）、0/全1、1/3/5字节与空值、缺来源/属性、未支持字段、每个截断位置、继承的声明冲突/重复拒绝。生产上限实际生成65536/65537单元DTB，前者通过后者拒绝，不mock解析器或限额。仓库小fixture memory-region-positive.dtb、memory-region-dangling.dtb由测试fixture()可复现，不提供任何设备板级事实。

根身份API/导入未改，既有jasmine伪装二进制拒绝回归通过。两个真实6.6 preflight均退出2，五项保留材料哈希不变；不接入导入新选项、构建放行或打包链。原树完整语义标志仍为false，本轮只实现一种声明引用列表，不输出合格remoteproc提取结果。

直接运行：

```sh
python3 tools/test_dtb_memory_region.py
python3 tools/test_dtb_phandle.py
python3 tools/test_dtb_tree.py
python3 tools/test_dtb_identity.py
python3 tools/test_wayne_board_evidence.py
python3 tools/test_6_6_gate_integration.py
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

API示例（导入路径包含tools；实际source_path须来自所读树，示例不指定设备节点）：

```python
from dtb_memory_region import decode_memory_region
with open("local-reference.dtb", "rb") as stream:
    snapshot = stream.read(8 * 1024 * 1024 + 1)
# edges = decode_memory_region(snapshot, actual_source_path)
```

[结果与断点](../research/dtb-memory-region-stage/checkpoint.json)，[带时区记录](operations/dtb-memory-region-2026-10-11.md)。下一步先明确下一受限证据层的支持规则及测试范围，再独立推进；provider参数、reg/reserved-memory、GLINK/RPMSG/SMEM及remoteproc分类仍未实现，沿用原设计，不自动扩大本轮范围。

实际国行DTB及来源链、boot/ABI/固件证据仍缺；DTB阻断与其余证据缺口保留。4.19、6.6成果和实验包不覆盖，不改固件、DTS、内核配置、init/fstab，不写sysfs、不触发remoteproc，不下载、编译或打包。没有真机测试，不宣称启动或硬件验证。实时额度不可读，85%/74%仅用户快照；同步后立即暂停。
