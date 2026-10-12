# 后续四个缺失blob有界批次探针

时间：2026-10-12T07:10:19.549409-07:00；基线b299a3c。仅国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：绑定原acquisition manifest与单对象探针规范SHA256，先实际复核前次blob类型/OID/内容哈希，从原162个missing blob按规范OID排序排除001fb2723fbb7c6dd6a2f19ef00bdfb862a17bf4，仅取后续四个。来源只读已有fork-fetch/probe固定https://github.com/sdm660-mainline/linux.git，禁止新增远端。

新增four_blob_batch_probe.py版本wayne.four-blob-batch.v1，复用原单对象attempt，顺序执行每OID独立downloads/four-blob-probe-b299a3c/0..3裸库最多一次精确请求，每次60秒期限、16MiB对象/包上限；无重试、历史加深、完整克隆、递归历史、其他对象补取或fallback。达到2MiB累计已验证payload时，下一项标not_attempted不启动；保守累计含上一探针17271字节。阈值限制下一请求，当前成功对象可能使累计越过阈值，不宣称整个批次payload永远≤2MiB；单对象原上限继续有效。检测轮询有调度延迟，不宣称绝对零超调。

遇任一server_rejected/timeout/auth_required/filter_unsupported/bot_challenge/response_anomaly/volume_limit/type_error/oid_mismatch/local_tool_error结果，立即stop_reason=object_failure，剩余项request_count=0、object/probe=null；无失败伪元数据。本次stop_reason=completed，四次均成功，未尝试项0。

| 选择顺序OID | payload字节 | 结果 |
| --- | --- | --- |
| 00753f0f73f819a743ea64ae08c3e64b661e1005 | 10431 | success |
| 04296a4abe8e87ac41873d4451abc8e3c00d02a5 | 4419 | success |
| 0509c0e69da28fa0693258ddc6bf249e349ba3da | 5410 | success |
| 055ca80c007578eed43c9e07576c2d5466a9600a | 147478 | success |

本批已验证payload167738字节，加上一探针共185009字节，未达2097152字节阈值。每项cat-file验证blob类型并按Git对象格式重算OID，内容SHA256见规范证据；隔离库只含所请求对象。全部对象留各自探针库，不导入原fork/主Git对象库、源码锁或构建；不上传blob内容。网络响应原字节仅留隔离库，公开只存命令/exit/严格结果/大小/OID/内容与响应SHA256等非敏感证据。

规范数据固定版本、输入哈希、选择顺序、逐项请求次数、停止原因/未尝试项、初始/批次/累计payload与false状态；无当前时间/临时目录。查询时间另存run.json。离线validate重新核对规范选择、绑定、对象类型/OID/hash、响应字节哈希、计数及停止模拟，严格拒绝未知/重复字段/OID、非法hash、来源/请求参数/嵌套字段/顺序漂移、成功对象不符、失败或未尝试元数据、停止后请求和payload矛盾。JSON规范序列化、原子不覆盖发布及异常清理复用原工具。旧单对象工具/证据和manifest未改。

发生了什么：四项明确synthetic本地Git服务测试与三项构建门禁测试共七项通过，覆盖全成功、第二项拒绝后剩余未尝试、本地ext sleep服务短超时后停止、真实1MiB初始+1MiB首项达到阈值后不启动下一项、tree类型拒绝/成功元数据类型篡改、输入哈希/计数/顺序/字段篡改、规范字节与重复离线验证一致、已有输出冲突及IO失败清理。synthetic超时使用缩短期限，实际远端固定60秒；测试不是实际fork历史或wayne事实。

两个实际6.6入口仍退出2，所有结果history_complete=false、upstream_membership_verified=false、carry_strategy_reviewed=false、eligible=false、hardware_tested=false。旧4.19/6.6锁、候选锁、provenance与既有实验包/证据哈希保留。成功仅验证这些对象传输与OID，不证明上游归属、补丁可携带或硬件可用。

[规范批次证据](../research/four-blob-stage/batch.json)，[测试与断点](../research/four-blob-stage/checkpoint.json)，[带时区记录](operations/four-blob-2026-10-12.md)。离线测试：

```sh
python3 tools/test_four_blob_batch.py
```

离线API validate(raw,manifest,manifest_sha,previous_probe,previous_sha,isolated_root)不请求远端。不得重跑run；它要求新批次目录不存在。下一步只审阅隔离对象的利用/更大范围预算，本轮不继续抓剩余对象，不迁入主库、不做指纹/更新资格放行。

无rebase/merge/cherry-pick、DTS/defconfig/boot/vendor/固件/init/fstab改动、编译/打包或真机验证，不宣称可刷、启动或硬件兼容。实时额度不可读取，95%/43%仅用户快照；保存同步后立即暂停。
