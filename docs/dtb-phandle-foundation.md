# DTB phandle唯一索引基础层

时间：2026-10-11T13:49:43.669754-07:00；基线50b5bc6。目标国行wayne/SDM660原始静态分区，独立6.6实验；fixture不是设备事实，与Miku UI无关。

做了什么：新增tools/dtb_phandle_index.py，build_phandle_index(bytes)复用read_tree在同一不可变快照上完整校验结构后，扫描全树phandle和linux,phandle声明。严格要求一个四字节大端单元，拒绝0/0xffffffff、任何非四字节长度、同节点双属性冲突和跨节点重复。先完整建表，验证失败只抛异常，不返回部分合格索引。返回冻结对象及只读映射，保留来源SHA256；继承8MiB、16384节点等原树边界，无新的无界遍历。

受限查询API resolve(int)只做一次字典查找，拒绝bool、非int、保留值、越uint32范围或缺失目标；目标可在DTB中晚于其他节点出现。本轮不解析所谓引用节点的属性；测试的opaque-cell只是原始字节，前向测试验证全树完成后的查询，不宣称已解析引用。

发生了什么：五项新二进制测试和十三项既有回归，共十八项通过。仓库小fixture phandle-positive.dtb及phandle-conflict.dtb可用测试中的positive()/binary()/node()重现。覆盖phandle、仅linux,phandle、同值双属性、双属性冲突、跨节点重复、0/全1、0/1/3/5/8字节长度、每个截断位置、大端解码、前向目标与非法查询；没有mock解析结果或字符串替换。空索引合法但查询缺目标拒绝；同值双属性只计一个节点声明。

大小端测试核对0x01020304与0x04030201：DTB规范固定大端，小端编码的字节会按大端得到另一个合法值，不能推断作者意图或声称自动识别错误字节序。根read_identity与既有导入代码未修改，jasmine根伪装仍由既有二进制导入回归拒绝。通用索引本身不认证wayne身份，必须与来源/身份门禁分开理解；未接入构建放行。

两个真实6.6 preflight均退出2；五项既有材料哈希未变。原树semantic_extraction_implemented仍为false；新模块仅解释声明，不解析memory-region、reg、reserved-memory或GLINK/RPMSG/SMEM关系，也不分类remoteproc。65536引用边上限仍仅预留，没有已解析引用，不输出合格语义提取结果。

直接运行：

```sh
python3 tools/test_dtb_phandle.py
python3 tools/test_dtb_tree.py
python3 tools/test_dtb_identity.py
python3 tools/test_wayne_board_evidence.py
python3 tools/test_6_6_gate_integration.py
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

API示例（导入路径需含tools；文件应为本地实际证据或明确合成fixture）：

```python
from dtb_phandle_index import build_phandle_index
with open("local-reference.dtb", "rb") as stream:
    index = build_phandle_index(stream.read(8 * 1024 * 1024 + 1))
# index.targets是只读phandle -> 规范路径映射；index.resolve(value)拒绝无效/缺失目标。
```

[断点与实际结果](../research/dtb-phandle-stage/checkpoint.json)，[带时区记录](operations/dtb-phandle-2026-10-11.md)。下一步仅审阅有类型引用的支持范围和错误约定，再独立实现受限引用解码；其余内容继续按[设计](dtb-remoteproc-extraction-design.md)保持未实现。真实wayne DTB/采集链、boot/ABI/固件证据仍缺，不因索引通过而放行。

4.19、6.6成果与实验包保留；没有修改固件、DTS、内核配置、init、fstab，没有写sysfs、触发remoteproc、下载、编译或打包。无真机测试，不宣称启动或硬件可用。实时额度不可读取，93%/75%仅用户快照；同步后立即暂停。
