# 可见提交离线补丁指纹

时间：2026-10-12T02:51:59.382411-07:00；基线4186999，国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：新增shallow_patch_fingerprints.py，先绑定inventory与review-queue原始规范SHA256并重验队列，只用现有本地对象，为恰一个父且paths_known、父可见可读的记录尝试规范diff及git patch-id --stable。GIT_NO_LAZY_FETCH=1、protocol.allow=never禁止网络/自动补取；没有加深/下载。

补丁参数固定--no-ext-diff --no-textconv --no-renames --diff-algorithm=myers --no-indent-heuristic --no-color --no-relative --src-prefix=a/ --dst-prefix=b/ --unified=3 --submodule=short --binary --full-index，core.quotePath=true、LC_ALL=C。保存原diff字节SHA256与stable patch-id，不加入作者、时间、提交消息；相同内容仅更改作者等元数据时patch-id与diff哈希均不变，内容改变则按真实diff改变。numstat使用同参数但移除unified=3及binary/full-index，追加--numstat -z；关闭外部转换和rename，不混入patch输出。

成功记录保存父OID/提交OID、两个输入哈希、文件数、文本增删量和binary_files（不把二进制增删伪记为已知）。diff/统计输出各限4MiB，命令5秒。无指纹严格原因为shallow_boundary/paths_unknown/zero_parents/merge_commit/parent_unavailable/objects_unavailable/empty_patch/evidence_limit；patch_id、diff_sha256和statistics均null。不用整棵树、第一父或合并展开代替普通补丁。

规范schema=wayne.shallow-patch-fingerprints.v1，OID字典序、UTF-8固定顺序/末尾换行，无当前时间或绝对路径。validator严格解析重复键、非有限值，重新从固定输入与当前本地对象计算预期内容，拒绝未知字段、非法OID/hash/patch-id、绑定/内容/枚举/null原因/排序漂移。原子不覆盖发布，既有不同字节拒绝、失败清理。

发生了什么：首次测试发现unified=3隐式启用patch导致numstat输出混杂，已分开统计参数后复测。四项合成实际Git对象测试与三项门禁共七项通过，覆盖稳定指纹、作者元数据改变/内容改变、浅边界/真实零父根/合并不生成普通指纹、实际移除对象、绑定与指纹/null篡改、确定性和输出冲突/IO失败清理。合成仓库明确不是实际SDM660证据。

实际结果：0条成功，原因计数{"shallow_boundary": 1, "paths_unknown": 0, "zero_parents": 0, "merge_commit": 0, "parent_unavailable": 0, "objects_unavailable": 63, "empty_patch": 0, "evidence_limit": 0}。现有fork是blob:none浅获取，内容diff所需blob缺失，未下载补齐；64条记录都未复核，carry_decision=undetermined、upstream_membership_verified=false，整体history_complete=false、eligible=false。patch-id相同最多表示规范补丁内容候选相等，不证明上游成员、来源、适用性或携带决定。

[指纹/缺失原因清单](../research/shallow-fingerprint-stage/fingerprints.json)，[断点/哈希](../research/shallow-fingerprint-stage/checkpoint.json)。两个实际6.6入口仍退出2，旧inventory/queue、源码锁/候选锁/provenance与既有成果哈希未改。

离线测试：

```sh
python3 tools/test_patch_fingerprints.py
```

CLI读取repo、inventory、queue以及明确--inventory-sha/--queue-sha；--validate重新计算核对已有报告，--output只在全部完成后原子不覆盖发布。无对象时输出明确null，不伪造内容指纹；成功执行仍退出2。

下一断点：本地缺blob，无法形成实际内容补丁清单；后续若要取得必要内容必须单独定义有界范围和证据要求，本轮不获取。完整历史、上游归属和携带策略仍未审，不因指纹/线索放行。无rebase/merge/cherry-pick、DTS/defconfig/boot/vendor/固件/init/fstab改动、编译或打包；保留4.19/所有发布包与门禁。无真机验证，不宣称可刷、启动或硬件兼容。

[带时区记录](operations/shallow-fingerprint-2026-10-12.md)。本轮因参数修正与对象重算明显超过约3分钟目标，保存同步后立即停止；实时额度不可读取，73%/51%仅用户快照。
