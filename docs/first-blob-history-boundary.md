# 首个隔离 blob 引入提交与可见历史边界核验

时间：2026-10-12T23:53:59.665317-07:00；基线492912f。国行wayne/SDM660、静态分区、独立Linux 6.6实验，与Miku UI无关。

做了什么：先检查status、diff、最近提交与上轮实际测试。没有已跟踪改动，原有空白未跟踪MD保留。仅处理首个001fb2723fbb7c6dd6a2f19ef00bdfb862a17bf4；复用上轮快照归属校验和八对象隔离链校验，绑定原归属/inventory/review/manifest规范SHA256。类型blob、17271字节、内容SHA256为958dd0d910f9cfed3914fa628e12a4ff2e3bfa7fcb6342accfa8a543abdff495。内容字节未作相似性或用途推断。

本轮只在现有64条inventory边界内，从acquisition上下文c9cb50b2d371824ce711f172430cbd6ed83ca1e9沿明确单父链向前核对；硬上限64个已有提交，不运行无界log、自动lazy fetch或网络请求。每次重算commit/tree Git OID及原始SHA256，核对库存父OID、逐级树entry与精确路径arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi，并记录父子路径对象差异。

发生了什么：共核对13个提交快照/12条父子边。上下文c9cb50b…路径已变为另一blob，其父b633be8…及再往前共12个连续祖先快照均引用所选OID。最近可证明的祖先边界为71c631a9fb211df4ea5a59ac68a310c5854f07f1（现有shallow边界）；其commit记录的父6fbaeffc3a92b4a32b8e320e486cf644ff30d240不在已有可见库存且对象缺失。可见11条更早父子边的精确路径blob不变，未观察到引入转换。

结论：只能证明所选blob在浅边界快照中已经存在。不能区分它在边界提交引入还是更早已经存在，更无法枚举全fork历史中的删除/重新引入或其他分支/路径出现；不是唯一来源或wayne适用性证明。introduction_candidates=null，unknown原因明确为更早浅历史不可枚举，不伪造候选列表。唯一引入提交仍null、relationship_status=unresolved。官方候选历史尚缺，本轮也未核对上游成员或携带策略。既然边界内无法唯一证明，就在此停止，没有发起远端请求，没有加深历史，也未处理第二blob。

最小新增schema=wayne.isolated-blob-history-boundary.v1及只读校验器。规范负载不含当前时间/绝对目录，保留来源锁URL、固定fork提交、精确路径、13份快照树链、12条父子对象差异、shallow文件哈希和可复现禁网络命令。校验先实时重新审计原证据/隔离边界和本地对象，再严格比较规范字节；未知字段、重复OID/快照、排序漂移、输入绑定/树/父子关系漂移、主库污染和资格误报均拒绝。原子发布复用不覆盖工具，冲突不产生部分文件。

实际本地链/确定性测试、明确synthetic篡改拒绝测试、原子冲突测试三项通过，既有门禁测试三项通过，共六项。两个真实6.6 preflight仍退出2。checkpoint JSON另验证可解析；上轮检查点全部保留文件SHA256核对一致。history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/source_lock_input/build_gate_authorization/hardware_tested全部false，隔离对象不迁入主库或构建输入。

[规范证据](../research/isolated-blob-history-boundary-stage/boundary.json) · [测试及断点](../research/isolated-blob-history-boundary-stage/checkpoint.json) · [带时区操作记录](operations/first-blob-history-boundary-2026-10-12.md)

可执行离线复核：

```sh
python3 tools/isolated_blob_history_boundary.py --check research/isolated-blob-history-boundary-stage/boundary.json
python3 tools/test_isolated_blob_history_boundary.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：唯一引入证明仍阻断。已知缺口是边界71c631a…父6fbaeff…及更早精确路径树关系；一个父对象成功取得也未必足以证明全历史唯一，不自动获取、不重试或扩展。后续若单独授权，需要先限定更早关系证据范围和停止条件。本轮同步GitHub后暂停，不进入第二对象、全历史或实际源更新。

无rebase/merge/cherry-pick、对象迁移、来源/候选锁、DTS/defconfig/boot/vendor/固件/init/fstab/4.19/provenance/实验包修改，无编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。额度84%/98%为用户快照，无法读取实时用量，不声称精确控制或保留。
