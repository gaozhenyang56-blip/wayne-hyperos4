# 隔离 blob 来源证据分流与下一目标选择

时间：2026-10-13T03:24:55.849805-07:00；基线a5a84d5。国行wayne/SDM660静态分区、独立Linux 6.6实验，与Miku UI无关。

做了什么：检查工作区status/diff、三层补证断点和上轮实际测试；没有已跟踪修改，原空白未跟踪MD保留。明确停止首blob父提交追踪，只读取八对象、单对象/两批链、inventory/acquisition manifest、前序规范补证及已有本地commit/tree。本轮零网络请求、零新对象、零第四层请求，未扩展原可见历史。

在manifest既有上下文的当前/直接父提交及其已记录变更路径内，逐级核验commit/tree Git OID与原始SHA256，补齐八个blob的精确快照路径见证。每项绑定类型blob、OID、字节大小、规范内容SHA256、隔离边界与证据链。见证只证明该路径在指定快照引用该OID，不证明全局来源、唯一引入或当前固定fork版本仍使用该内容。未按内容相似性或文件名猜用途。

发生了什么：目标相关性有真实材料支持0项、其他SoC/设备路径5项、目标关联证据不足3项。下表按下一步复核优先级排列，OID为唯一规范完整OID的显示前缀：

|优先级|OID前缀|字节|已证快照路径|分流与后续信息增益|
|---|---|---:|---|---|
|1|0509c0e6|5410|arch/arm64/boot/dts/qcom/pm660.dtsi|目标关联不足；存在未验证实验include依赖，可优先核对独立板级关联|
|2|04296a4a|4419|drivers/input/misc/Makefile|通用内核路径，设备关联未知|
|3|0ab09b0d|12232|arch/arm64/kvm/vgic/vgic.h|通用内核路径，设备关联未知|
|4|00753f0f|10431|arch/arm64/boot/dts/qcom/sdm636-xiaomi-tulip.dts|其他SoC/设备路径，延后|
|5|06f8ff62|16144|arch/arm64/boot/dts/qcom/msm8996-xiaomi-common.dtsi|其他SoC路径，延后|
|6|09a0c35d|137687|arch/arm64/boot/dts/qcom/sm8450.dtsi|其他SoC路径，延后|
|7|055ca80c|147478|arch/arm64/boot/dts/qcom/sdm845.dtsi|其他SoC路径，延后|
|8|001fb272|17271|arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi|其他SoC/Sony路径，首blob追踪已停止|

排序规则明确且机械：已有实验依赖待核实项 → 通用路径证据缺口 → 其他SoC/设备路径 → 已停止的首blob；同组按已有blob字节数、完整OID排序。大小仅为本地读取成本的可复核量，不是未来耗时/网络流量；未知信息增益数值、未来耗时均null。此排序是条件式离线补证优先级，材料不足以可靠判定实际硬件收益或补丁重要性，不生成这种排名。

为何pm660排第一：现有实验config实际include sdm660-xiaomi-jasmine.dts，该已保存历史源又实际include pm660.dtsi；清单保留两文件哈希、行号及原文。这仅支持“现有实验有待审include依赖”，且明确标为unverified_jasmine_inherited_experiment_only。不是wayne板级事实，也不是允许继续继承jasmine的理由。pm660仍归入证据不足，不升级成目标已验证。其他SoC/设备路径分类也仅指已证快照路径，不伪造全局排他来源结论或上游成员关系。

唯一下一目标：0509c0e69da28fa0693258ddc6bf249e349ba3da在pm660.dtsi路径上的独立wayne PMIC关联证据审阅，不是父历史追踪或适配修改。最小材料为现有blob/快照树链，以及用户实际wayne DTB或有可信来源链的板级材料中明确PMIC关系，保持既有身份与来源门禁。真实板级材料当前缺失，因此selected_next_target为conditional_evidence_review_only_not_device_adaptation，blocked_reason=actual_wayne_board_evidence_missing；本轮未执行下一目标、未计划网络请求。停止条件：缺真实wayne材料、仅有jasmine/其他设备参考、关系有歧义都保持unresolved，不猜硬件或节点。不得凭include文本证明已适配。

最小新增wayne.isolated-eight-blob-triage.v1清单及只读校验器，规范JSON绑定原review/第三层/manifest/inventory SHA256，无当前时间或绝对路径，保留各条精确路径树链、分类、缺口、成本依据和排序键。校验实时重读既有对象/证据，拒绝未知字段、重复/非法OID、类型/哈希/树链/排序漂移、主库污染、第四层误报和资格误报；原子不覆盖输出。history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/build_gate_authorization/source_lock_input/hardware_tested全部false。

三项真实路径/稳定排序/jasmine不升级、明确synthetic篡改拒绝、原子输出冲突测试通过；三项既有门禁测试通过，共六项。两个实际6.6入口仍退出2。旧第三层工具/规范证据/请求、八对象review与保留清单的锁、4.19/6.6成果、provenance及包均未变；没有对象迁移或构建输入变化。

[规范分流清单](../research/isolated-blob-triage-stage/triage.json) · [实际测试及断点](../research/isolated-blob-triage-stage/checkpoint.json) · [带时区记录](operations/isolated-triage-2026-10-13.md)

仅离线复核：

```sh
python3 tools/isolated_blob_triage.py --check research/isolated-blob-triage-stage/triage.json
python3 tools/test_isolated_blob_triage.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：停止首blob逐层路线，不请求第四层。仅保留上述pm660条件式下一证据目标；独立真实wayne板级关联材料缺失时暂停，不执行目标、不自动获取新材料。现有八个对象不能给出已适配补丁集合、上游归属或携带策略。

无fetch/clone/rebase/merge/cherry-pick、对象迁移、sources.lock/候选锁/DTS/defconfig/boot/vendor/固件/init/fstab/4.19/provenance/既有包修改，无编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。47%/92%仅为用户额度快照，无法读取实时用量，不声称精确控制或保留。同步GitHub后立即暂停。
