# 首个隔离 blob 第三层父提交补证

时间：2026-10-13T02:45:55.854193-07:00；基线f530131。目标为国行wayne/SDM660静态分区独立Linux 6.6实验，与Miku UI无关。

做了什么：检查status/diff、上一轮实际测试与断点。无已跟踪修改，原空白未跟踪MD保留。重新验证所有前序规范证据与隔离对象，从实际50ae1c470491481328363639c227020691469f29原始commit读取唯一直接父9a6ed4ea985ac4b7a566faddeb16271b8ea54d36，同时核对commit Git OID/原始SHA256及前序树关系。该父在主库、原fork库及前两轮隔离库均missing，未猜测OID。

仅对原固定https://github.com/sdm660-mainline/linux.git做一次精确父OID请求；复用已有引擎，不修改旧工具或报告。新独立bare库downloads/third-parent-probe-f530131，depth=1/blob:none、60秒截止杀进程组、8MiB对象存储停止阈值，禁认证交互/重定向，无tag/子模块/FETCH_HEAD写入。遇拒绝/异常/认证/人机验证停止，无重试、换源、递归祖先获取或批量加深。只获取该commit及tree闭包，无blob源码。

发生了什么：请求退出0，隔离对象存储2808314字节，仅一个指定commit及tree，无其他commit/blob，shallow仅该父。9a6ed4e…类型commit、1725字节，重算Git OID一致，原始SHA256及逐级树链/OID/类型证据见规范清单。其精确路径arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi仍引用001fb2723fbb7c6dd6a2f19ef00bdfb862a17bf4，与50ae1c…相同。首blob的type/17271字节/内容SHA256及八对象隔离链再次核对，未按内容相似性推断用途。

因此排除50ae1c…相对该直接父的该路径引入转换；最近的“已存在”祖先见证推进到9a6ed4e…。仍不能证明全历史唯一引入、wayne适用性、上游成员关系或携带策略。局部引入边界/唯一引入提交均null，relationship_status=unresolved。

最小新增v3增量适配器，沿用原v1受限请求/树校验引擎的独立模块实例。previous_evidence_sha256绑定前轮v2规范字节，engine_source_sha256绑定旧引擎，原v1/v2报告及工具字节不变、仍可验证。嵌套request_engine_evidence保留旧结构，旧boundary_sha256字段在本适配上下文中指前轮v2证据哈希；须由v3适配器校验，不能作为最初v1入口的boundary输入。版本化原因是来源链新增一层且本轮新增明确的信息增益评估。

规范JSON无当前时间或绝对目录，记录父OID解析命令、单次请求命令/响应哈希/对象文件哈希、父子树链与比较。检查器实时重读全部本地证据，严格拒绝未知字段、重复/非法OID、类型/树关系/证据链漂移、主库污染、资格误报及擅自开启第四层。失败不发布部分合格结果；原子不覆盖输出，默认audit/check无网络，已有请求目录拒绝再次--attempt。

三项本地父关系与确定性、明确synthetic篡改拒绝、原子冲突测试通过；三项既有门禁测试通过，共六项。两个实际6.6入口退出2。旧引擎、前轮规范证据/请求及保留清单的锁、4.19/6.6成果、provenance与包均未变；新对象未迁入主库、原fork库、旧隔离库或任何构建输入。内外层history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/source_lock_input/build_gate_authorization/hardware_tested全部false。

信息增益评估：连续三层成功请求只新增三条直接祖先路径见证，都未观察到blob变化或引入转换，也没有缩小到唯一来源或提供wayne关联。新增边是有效事实，但相对于更新资格阻塞，继续逐层获取的收益有限。建议停止这一逐层路线，不自动进入第四层；这不是“更早历史没有引入”或“永远无法找到”的判断，也不替代完整历史/上游成员/携带策略审查。机器可读评估明确continued_layer_requests_recommended=false、unique_origin_resolved=false、fourth_layer_authorized=false。

[规范证据](../research/isolated-third-parent-stage/evidence.json) · [实际请求](../research/isolated-third-parent-stage/request.json) · [测试及断点](../research/isolated-third-parent-stage/checkpoint.json) · [带时区记录](operations/isolated-third-parent-2026-10-13.md)

仅离线复核，不再次--attempt：

```sh
python3 tools/isolated_third_parent_probe.py --check research/isolated-third-parent-stage/evidence.json
python3 tools/test_isolated_third_parent_probe.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：保持unresolved并停止逐层请求。新commit记录的父add8973e3de6a3557ef5fd0ecc317b24fc6efe6e只是已解析parent声明，本轮未取得或核验其树，不猜测内容，不发起第四层。后续若另定阶段，应先论证与源更新阻塞的关联及有界证据方案，不自动延长此路线，不处理第二blob或旁支。

无rebase/merge/cherry-pick、对象迁入主库、锁/DTS/defconfig/boot/vendor/固件/init/fstab/4.19/provenance/既有包修改，无编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。57%/93%为用户额度快照，无法读取实时额度，不声称精确控制或保留。同步GitHub后立即暂停。
