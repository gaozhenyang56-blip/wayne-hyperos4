# pm660.dtsi 与真实 wayne 板级包含链关联核验

时间：2026-10-13T04:56:24.559470-07:00；基线1296e39。国行wayne/SDM660、静态分区、独立Linux 6.6实验，与Miku UI无关。

做了什么：检查status/diff、最近提交、上轮实际测试和分流断点。没有已跟踪修改，原空白未跟踪MD保留。只处理候选0509c0e69da28fa0693258ddc6bf249e349ba3da，不处理其余七个blob，不恢复首blob父历史追踪。

复用选定对象校验，验证独立four-blob隔离库槽2只有该blob，无alternates；类型blob、5410字节、重算Git OID及规范内容SHA256与原分流事实一致。主库和原fork库仍missing该blob。对原分流中的pm660.dtsi精确快照见证逐级重算commit/tree OID和SHA256并核对entry/type/父树关系。它是6.6候选历史快照中的文件，不等于真实wayne板级基线，也不证明固定6.6当前提交仍使用同一字节。

发生了什么：现有记录确实固定了一个wayne名称源码参考——jakecommon/linux-sdm660-xiaomi-wayne，声明提交eefc44180fdfc30cdc760109c8acf189482c238d。已保存入口arch/arm64/boot/dts/qcom/sdm660-xiaomi-wayne.dts为426字节，SHA256与原source-evidence.json一致；其直接include是sdm660-xiaomi-jasmine.dts，并有共享板级设计的声明。

这只是第三方jasmine继承参考，不是经独立材料证明的真实国行wayne基线。原下载记录固定URL/声明commit/文件SHA256，未提供该入口的Git commit/tree成员关系证明；计算出的blob OID仅是本地文件字节OID，不冒称已验证其远端树成员关系。路径名、model/compatible或作者共享设计声明均不能单独证明适用性。历史sources.lock中的Miku相关仓库同样仅是第三方研究记录，不替代用户当前系统或板级基线。

本轮没有远端请求：并非没有已记录仓库，而是它不能满足所要求的真实wayne来源条件；继续取该参考的jasmine包含文件也不能把clone-only前提变成独立板级事实。不得把7.x参考入口与保存的6.6 jasmine文件跨仓库/提交拼接为闭合链，也不回退其他设备或猜新仓库。

精确断点：third_party_entry_includes_jasmine_without_independent_actual_wayne_board_evidence。只记录参考入口的直接include边，verified_real_wayne_edges为空、include_chain.status=not_closed、target_association=unresolved。未证明或否定真实wayne是否使用PM660；只是当前材料不能完成关联证明。

最小新增wayne.pm660-board-association.v1及只读检查器，绑定原分流、来源记录、source lock SHA256，并将这些字节与1296e39本地Git基线比对。保留候选快照树链、第三方入口来源/哈希/原始include行、成员关系未证状态和零请求决定。规范JSON无当前时间/绝对路径；未知字段、重复/非法OID、类型/树关系/证据漂移、主库污染、来源认证误报或资格误报拒绝；原子不覆盖输出，异常不发布部分合格结果。所有history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/build_gate_authorization/source_lock_input/hardware_tested继续false。

三项真实选定对象/来源不升级/确定性、明确synthetic树/链/资格篡改拒绝、原子输出冲突测试通过；三项既有门禁测试通过，共六项。两个实际6.6入口退出2。保留清单全部SHA256核对一致；来源记录、源码锁、4.19/6.6成果、provenance及既有包未改，未迁对象、未修改DTS/defconfig/boot/vendor/固件/init/fstab，无编译或打包。

[规范关联证据](../research/pm660-wayne-association-stage/association.json) · [测试及断点](../research/pm660-wayne-association-stage/checkpoint.json) · [带时区记录](operations/pm660-wayne-association-2026-10-13.md)

仅离线复核：

```sh
python3 tools/check_pm660_wayne_association.py --check research/pm660-wayne-association-stage/association.json
python3 tools/test_pm660_wayne_association.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：需要独立真实国行wayne板级材料或明确可采信的原始板级源码及其不可变commit/tree/include链，才能评估到PM660的关联。缺少这些材料就暂停，不继续补第三方jasmine链，不自动下载或扩展到其他blob/父历史。后续完整include证明必须逐文件绑定同一源码上下文，任何缺文件、条件分支不明确或跨版本拼接均不放行。

无网络请求、clone/fetch/rebase/merge/cherry-pick、对象迁移或新构建输入。无真机测试，不宣称可启动、可刷或硬件兼容。97%/90%仅用户额度快照，无法读取实时额度，不声称精确控制或保留。同步GitHub后立即暂停。
