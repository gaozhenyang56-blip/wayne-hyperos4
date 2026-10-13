# 单个隔离 blob 精确快照路径核验

时间：2026-10-13T05:40:07.959766+00:00；基线84180b3。国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：检查status/diff和上一断点；没有已跟踪修改，原有空白未跟踪MD保留。复用八对象校验器核对隔离边界与链绑定，只选全局序号0的001fb2723fbb7c6dd6a2f19ef00bdfb862a17bf4。依据acquisition manifest的唯一审计上下文，只检查c9cb50b2d371824ce711f172430cbd6ed83ca1e9与父b633be8ec977605e7d47c2b9a778ad8298a7dd0a的19个已记录变更路径。

发生了什么：精确树关系证明该blob位于父提交的arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi；当前提交在这19个路径内没有该OID。提交原始字节重算Git OID、逐级根树到blob的entry/type/mode/OID及树原始SHA256均核对，隔离blob类型blob、17271字节、内容SHA256仍为958dd0d910f9cfed3914fa628e12a4ff2e3bfa7fcb6342accfa8a543abdff495。此为父快照引用，不是唯一引入提交、全树无其他路径证明或wayne适用性。文件路径里的其他设备名称不构成本项目目标证据。

现有裸库无命名ref，但FETCH_HEAD精确指向固定6a4e475000ecc7e864911959a1984a0664088464；origin与原锁URL一致。初次实现假设show-ref存在及误用manifest字段名，均触发拒绝、无规范输出；已按实际FETCH_HEAD和commit_oid修正后测试。没有远端请求：浅历史无法证明唯一来源，候选对象历史仍缺失，本轮不扩展消除该歧义。

新增最小wayne.isolated-blob-snapshot-attribution.v1确定性证据与只读校验器，命令相对隔离库执行、禁协议与lazy fetch，输入绑定原review/manifest/inventory规范哈希；校验重新读取真实本地对象后逐字节比较规范报告。拒绝未知字段、重复/漂移见证、树/提交/hash/顺序矛盾、隔离污染和资格误报；复用原子不覆盖发布。规范负载无当前时间/绝对路径。relationship_status仍unresolved，unique_introducing_commit/candidate_history为null，history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/source_lock_input/build_gate_authorization/hardware_tested全部false。

三项实际本地快照/确定性、明确synthetic报告篡改拒绝、原子输出冲突测试与三项既有门禁测试共六项通过；两个实际6.6入口均退出2。运行测试采用unittest discovery，既有门禁测试文件没有直接执行入口。旧检查点列出的锁、provenance、4.19/6.6成果及包保留哈希全部一致，八个blob仍仅在隔离库。

[规范证据](../research/isolated-blob-attribution-stage/attribution.json) · [测试及下一断点](../research/isolated-blob-attribution-stage/checkpoint.json) · [操作记录](operations/single-blob-attribution-2026-10-13.md)

复核：`python3 tools/isolated_blob_attribution.py --check research/isolated-blob-attribution-stage/attribution.json`。测试：`python3 tools/test_isolated_blob_attribution.py`及`python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v`。

下一断点：首对象已获得精确父快照路径见证；未解决唯一引入提交和官方候选历史关系。只排除当前提交19个指定变更路径中包含该OID，未扫描其他路径、全部历史或官方候选，不声称全局唯一。本轮到此暂停，不自动选择第二对象或获取更多证据。后续需单独限定历史证据范围，完整源及补丁携带策略仍未审。

无fetch/clone/rebase/merge/cherry-pick、对象迁移、源码/设备配置修改、编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。额度97%/100%仅用户快照，无法读取实时额度，不声称精确控制或保留。
