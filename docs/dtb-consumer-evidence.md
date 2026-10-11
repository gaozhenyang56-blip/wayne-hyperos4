# memory-region消费者只读证据组合层

时间：2026-10-11T16:46:44.004077-07:00；基线3e3e71f。国行wayne/SDM660静态分区6.6实验，与Miku UI无关；合成fixture不是实际板级事实。

做了什么：新增tools/dtb_consumer_evidence.py的collect_consumer_evidence(bytes)。一次不可变快照读取完整树并构建唯一phandle索引，只枚举显式存在memory-region的节点，按DTB结构出现顺序返回冻结ConsumerEvidence组成的tuple。复用既有列表/直接reserved-memory/reg逻辑，共享同一索引和目标缓存，避免逐消费者重复读文件/全树建表；旧公开API行为不变。

每个记录保留输入SHA256、来源规范路径、memory-region token与值绝对偏移、原始bytes、有序冻结ReservedTarget及其ReferenceEdge、目标规范路径、reg元组和地址/size原始偏移、no_map/reusable显式存在性。可选compatible/status/firmware-name固定按此顺序记录：缺失为presence=absent、raw/offset=None、strings=()；存在保留原始bytes/token/value偏移，要求末尾NUL、无空元素并严格ASCII解码。compatible与firmware-name为非空字符串tuple；status恰为一个非空字符串，不转为启用状态，不填默认值。非ASCII显式拒绝，不替换或忽略解码错误。

任何显式消费者属性畸形、引用或目标资格/reg错误、全树phandle冲突均异常退出，只在所有消费者成功后返回，不提供部分合格结果。输出对象、嵌套tuple、冻结目标/边及bytes均不可变。空消费者集合返回()，不代表不存在remoteproc或硬件。

上限：消费者≤65536，累计引用边≤65536（包括重复引用，跨消费者累计），预检列表长度及总数后才构造结果。既有16384全树节点上限更紧，所以65536消费者分支实际不可达；本轮不伪称已触达它。二进制测试在本fixture构成下16380消费者通过，增加至16384消费者因总节点越界拒绝；实际累计65536边通过、65537边拒绝。共享目标缓存不丢失引用顺序或重复项。

发生了什么：五项新二进制测试与原三十二项回归共三十七项通过。覆盖单/多消费者、多目标与顺序、可选属性全缺失、合法多字符串/status单字符串、缺末尾NUL、空元素/status多字符串、合法消费者后畸形失败无返回、悬空引用、非法reserved-memory、冻结属性/结果及实际边界。仓库consumer-positive.dtb由测试fixture()重现；没有mock解析结果或用字符串替换绕过身份。

根身份/导入未修改，jasmine拒绝回归仍通过；两个真实6.6 preflight均退出2，五项保留材料哈希未变。消费者不分类为remoteproc，不根据节点名、属性字符串或缺status推断功能/状态/固件可用性；不推断GLINK/RPMSG/SMEM、不解析其他provider参数、不判断地址范围/对齐/重叠、不接入构建或导入新选项。

直接复核：

```sh
python3 tools/test_dtb_consumer_evidence.py
python3 -m unittest discover -s tools -p 'test_dtb_*.py'
python3 tools/test_wayne_board_evidence.py
python3 tools/test_6_6_gate_integration.py
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

API示例（导入路径需包含tools）：

```python
from dtb_consumer_evidence import collect_consumer_evidence
with open("local-reference.dtb", "rb") as stream:
    evidence = collect_consumer_evidence(stream.read(8 * 1024 * 1024 + 1))
```

[结果和下一断点](../research/dtb-consumer-stage/checkpoint.json)，[带时区记录](operations/dtb-consumer-2026-10-11.md)。下一步仅审阅只读证据导出与真实来源/身份集成，不扩大到硬件分类或构建放行；实际国行wayne DTB/来源链及boot/ABI/固件仍待核实。4.19、6.6成果及实验包保留，不改固件、DTS、内核配置、init/fstab，不写sysfs或触发remoteproc，无下载、长编译/打包或真机测试，不宣称启动或硬件验证。实时额度不可读，62%/70%仅用户快照；同步后立即暂停。
