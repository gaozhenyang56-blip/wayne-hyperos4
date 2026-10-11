# reserved-memory引用目标与reg只读数值基础层

时间：2026-10-11T15:21:46.667070-07:00；基线33102f7。目标仅国行wayne/SDM660静态分区6.6实验，与Miku UI无关；合成数据不代表实际设备地址或布局。

做了什么：新增tools/dtb_reserved_memory.py的decode_reserved_memory(bytes, source_path)，同一不可变快照只读取一次树，再复用唯一phandle索引与memory-region内部解码。两个旧公开API行为不变。要求/reserved-memory显式存在，所有引用目标均在其直接子层；父节点#address-cells与#size-cells必须显式存在且恰为一个BE32单元，本轮仅接受1或2。ranges必须存在且为空。

每个目标reg须非空且为(address-cells+size-cells)*4的整数倍；按大端无符号解码最多64位的(address,size)，按原顺序保存冻结tuple及地址/size原始DTB绝对偏移。返回冻结ReservedTarget成员组成的tuple，每项保留原ReferenceEdge与来源哈希、宽度、reg元组/偏移、no_map/reusable布尔存在性。两布尔属性若存在必须为零长度，不允许同时存在。缺失/畸形/截断/声明冲突等均异常退出，不返回部分结果；同一重复目标缓存已解码元组，保持原引用顺序。

数值范围只由1/2个cell的编码宽度限定，无法从合法两cell产生超过uint64的值；非法宽度或不完整元组拒绝。不做address+size运算或范围、对齐、重叠/真实可映射资格检查。size=0原样保留，本轮没有引入规范禁止证据，不自行拒绝或改写。不会将原始数值称为已验证wayne物理内存。

发生了什么：六项新增二进制测试与原二十六项回归，共三十二项通过。覆盖1/1、2/2、多个reg元组、多memory-region目标、no-map/reusable、二者冲突与带值、缺父节点、外部目标/非直接子层、缺失/0/3/全1/错误长度cell计数、缺/非空ranges、缺/空/畸形reg及2/2不完整元组、每个截断位置、继承phandle冲突、失败无部分返回、size=0及uint64最大值。仓库reserved-positive-11.dtb与reserved-positive-22.dtb由测试fixture()重现；没有mock输出、字符串替换或真实板级推断。

原根身份/导入未修改，jasmine伪装仍由既有二进制回归拒绝；两个真实6.6 preflight均退出2，五项保留材料哈希不变。通用基础API不认证wayne来源，不接入导入新选项或构建放行。boot/ABI/固件证据缺口与DTB阻断保留。

直接运行：

```sh
python3 tools/test_dtb_reserved_memory.py
python3 tools/test_dtb_memory_region.py
python3 tools/test_dtb_phandle.py
python3 tools/test_dtb_tree.py
python3 tools/test_dtb_identity.py
python3 tools/test_wayne_board_evidence.py
python3 tools/test_6_6_gate_integration.py
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

API示例（导入路径需包含tools，来源节点须由实际树提供）：

```python
from dtb_reserved_memory import decode_reserved_memory
with open("local-reference.dtb", "rb") as stream:
    snapshot = stream.read(8 * 1024 * 1024 + 1)
# targets = decode_reserved_memory(snapshot, actual_source_path)
```

[实际结果与断点](../research/dtb-reserved-memory-stage/checkpoint.json)，[带时区记录](operations/dtb-reserved-memory-2026-10-11.md)。下一步先明确下一独立小阶段范围；remoteproc分类、compatible/status/firmware-name字段解码、GLINK/RPMSG/SMEM关系、provider参数引用与地址资格检查均未实现，原完整语义提取仍未完成，不能输出合格remoteproc结论。

保留4.19、6.6成果及实验包；不改固件、DTS、内核配置、init/fstab，不写sysfs或触发remoteproc，不下载、长编译或打包。没有真机测试，不宣称任何硬件或整机启动可用。实时额度不可读取，76%/72%仅用户快照；同步后立即暂停。
