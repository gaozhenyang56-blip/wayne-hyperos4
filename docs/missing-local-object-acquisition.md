# 缺失本地对象获取需求清单

时间：2026-10-12T03:47:09.606868-07:00；基线f76306d。国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：新增missing_object_manifest.py，完全离线读取原inventory/review queue/fingerprint规范字节并绑定三个SHA256；校验队列、指纹字段/父OID/原因/计数一致性。在已有父/提交树中，只针对原已知变更路径运行ls-tree，再用cat-file --batch-check确认精确blob是否本地缺失。GIT_NO_LAZY_FETCH=1、protocol.allow=never与字面路径模式禁止自动补取和远端访问；不调用fetch/clone。

规范schema=wayne.missing-object-acquisition.v1。每项保存三个输入哈希、提交OID、父OID/原图内可见性/实际本地存在复核、paths_known、对应指纹条目及其null原因。objects_unavailable仅在实际存在缺失blob证据时机械归为missing_local_object；blob类型依据现有commit树条目，不从错误文字猜类型。精确OID/类型/presence逐项记录，若全都存在却旧指纹标缺失则拒绝，而不是继续申请获取。

浅边界单独归shallow_boundary，missing_objects=null、unknown_reason=shallow_completeness_depth_unknown；仅给separate_completeness_review，不申请某个猜测深度。后续内容需求列出已证实精确blob OID，建议上限4096对象/16MiB/20秒，来源URL和depth=null，不伪造取回来源，network_authorized=false。这是待独立审阅的最小范围建议，不授权本轮或自动后续下载；浅边界需求与blob内容需求不可混用。

所有输出history_complete=false、upstream_membership_verified=false、carry_strategy_reviewed=false、eligible=false、hardware_tested=false，条目保持unreviewed/undetermined。数据稳定按原OID顺序，UTF-8规范JSON，不含当前时间或工作区路径；未知信息明确null及原因。validator严格拒绝未知/重复字段、非法绑定/OID、重复条目、父/原因/排序矛盾、manifest内容漂移；每次复核实际本地缺失状态，不能信任旧presence声明。完整成功后才原子不覆盖发布，既有不同字节拒绝，IO失败清理。

发生了什么：四项synthetic Git测试与三项既有门禁测试共七项通过。覆盖字节稳定、浅边界隔离、精确缺失blob、恢复对象后存在/缺失矛盾拒绝、输入哈希篡改、重复项/未知字段/原因/排序漂移、重复键及输出冲突/失败无部分文件。首次fixture只删除了未影响第二差分的blob，随后真实删除其Makefile内容对象再复测；未mock对象或解析结果。

实际清单63条missing_local_object、1条shallow_boundary，去重缺失blob数162；三份原证据SHA已绑定，生成后再离线校验字节一致。两个实际6.6入口仍退出2，原源码锁、候选锁、DTB provenance、指纹/队列/清单和旧成果哈希未变。

[完整需求manifest](../research/missing-object-stage/manifest.json)，[绑定哈希](../research/missing-object-stage/input-hashes.json)，[断点/统计](../research/missing-object-stage/checkpoint.json)。离线复核：

```sh
python3 tools/test_missing_object_manifest.py
python3 tools/missing_object_manifest.py downloads/history-probe-73e35d6/fork research/shallow-inventory-stage/inventory.json research/shallow-review-stage/queue.json research/shallow-fingerprint-stage/fingerprints.json --hashes research/missing-object-stage/input-hashes.json --validate research/missing-object-stage/manifest.json
```

成功验证也退出2。清单没有接入自动获取或更新门禁放行；只能用于解释阻塞。对象已补齐时旧需求不再有效，应由独立阶段复核新状态，不隐式覆盖旧manifest。

下一断点：先独立审阅精确blob来源与有界获取能力，以及浅边界完整性路线；本轮不访问远端、不下载/补齐，不声称上游关系或携带策略已审。没有rebase/merge/cherry-pick、DTS/defconfig/boot/vendor/固件/init/fstab改动、编译/打包，保留4.19及全部旧实验包/门禁。无真机验证，不宣称可刷、启动或硬件兼容。

[带时区记录](operations/missing-object-2026-10-12.md)。实时额度无法读取，54%/48%仅用户快照；保存同步后立即暂停。
