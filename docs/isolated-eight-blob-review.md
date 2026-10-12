# 现有八个隔离blob可利用性与缺口审阅

时间：2026-10-12T12:29:09.193256-07:00；基线50bb7d7，国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：检查status/diff/断点，只读取原manifest、单对象/两批证据与现有隔离库。复用单对象和增量链完整离线校验器，核对四个规范输入SHA256、原manifest排序前八个OID、type/size/重算OID/content SHA256。另逐库检查bare=true且只含所指定OID；以禁网络/自动补取cat-file批查询工作区主Git库和原fork库，确认这八个OID均missing。没有远端请求、新对象获取或对象迁移。

最小新增isolated_blob_review.py，schema=wayne.isolated-eight-blob-review.v1，只将既有验证事实与未证关系组成确定性清单。规范负载固定顺序、UTF-8、输入哈希与隔离槽标识，不含当前时间或绝对目录。未知字段、重复OID、顺序/哈希/链/隔离范围漂移、主库存在或isolated被标成source lock、任何true资格声明均拒绝。validator将待验内容与重新audit得到的规范字节比对；生产使用时expected须来自实时只读audit，不是外部自报报告。发布复用原子不覆盖写入。

已证事实：八个隔离blob总payload351072字节，类型/OID/大小/内容SHA256/输入链和隔离边界复核一致；主Git库与原fork库均未污染。未证关系：现有acquisition manifest把blob列在提交审计上下文中，但不记录明确在哪个父/当前树的哪个精确路径；不能据此给blob唯一提交/用途。逐对象precise_path=null、precise_commit=null、candidate_history=null、relationship_status=unresolved。未读内容作相似性匹配，也不猜上游归属或板级功能。

对象内容可作为后续只读对象检查候选（read_only_audit_candidate=true），但不能直接作为已绑定历史审计输入（history_audit_ready=false、source_lock_input=false）。阻断为精确path/commit未绑定、候选历史缺失、浅历史不完整、上游成员与携带策略未审。history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/build_gate_authorization/hardware_tested均false；对象取回成功不解除任何门禁。

发生了什么：三项明确synthetic纯序列化/漂移/污染拒绝测试及三项既有门禁测试共六项通过。测试未启用Git网络服务，也无fetch/clone；合成事实只验证审阅格式，真实对象另用既有校验器反复本地核对。两个实际6.6入口仍退出2。旧源码锁、候选锁、manifest/provenance、两批证据及4.19/6.6成果/包保留哈希未变。

[审阅清单](../research/isolated-blob-review-stage/review.json)，[测试和断点](../research/isolated-blob-review-stage/checkpoint.json)，[带时区记录](operations/isolated-review-2026-10-12.md)。仅离线复核：

```sh
python3 tools/test_isolated_blob_review.py
python3 tools/test_6_6_gate_integration.py
```

API audit()只读本地证据/对象，validate(report,audit())重新核对；不调用run/attempt，不转移对象。

明确下一断点：八个对象仅具备内容证据，精确路径/提交/候选历史关系全未解决。下一独立阶段若授权，可先基于已存在树对象设计精确归属核对；当前不进行该扩展，不新增获取，不迁主库、不做来源认证或放行。本轮无rebase/merge/cherry-pick、固件/DTS/defconfig/boot/vendor/init/fstab改动、编译或打包，无真机验证，不宣称启动、可刷或硬件兼容。

周额度29%已接近用户预算保留区，本轮到此停止。无法读取实时额度，97%/29%仅用户快照，不声称精确保留约20%。
