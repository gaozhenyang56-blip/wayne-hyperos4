# 现有fork浅历史内提交/路径线索清单

时间：2026-10-12T00:49:04.921076-07:00；基线e8f02e9。仅国行wayne/SDM660静态分区6.6实验，与Miku UI无关。

做了什么：只读现有downloads/history-probe-73e35d6/fork对象，校验上一轮对象文件SHA256后枚举固定6a4e475000ecc7e864911959a1984a0664088464可达提交。所有Git命令设置GIT_NO_LAZY_FETCH=1与protocol.allow=never，禁止自动补取或其他远端操作；没有重试kernel.org、加深/克隆或源码下载。

新增tools/shallow_patch_inventory.py：版本wayne.shallow-patch-inventory.v1，按OID字典序确定记录顺序。每个记录保存OID、父OID/可见图内状态/本地对象可读状态、作者原始unix_seconds及原始时区、UTF-8主题、可验证变更路径排序集合、原始commit对象SHA256和不含自身record_sha256字段的规范UTF-8字节SHA256。commit对象还实际计算Git SHA1与OID一致。每个可见父的差分路径取并集；关闭rename/ext-diff/textconv以免访问blob或执行外部diff。边界提交不越过浅历史边界，即使父对象恰存在也不解其差分；changed_paths=null、path_evidence_complete=false，绝不把整个根树冒充补丁路径。

线索规则literal-subject-path-component-v1：主题与路径组件仅作明确非字母数字边界的wayne/sdm660/qualcomm/android关键词匹配，路径qcom组件追加qualcomm线索；jasmine独立记jasmine_reference。路径/主题命中不证明上游归属、硬件功能、补丁必要性或可移植性，wayne_target_verified恒false。jasmine-only测试不产生wayne线索或目标证据。

清单显式shallow_boundary=true、history_complete=false、upstream_membership_verified=false、carry_strategy_reviewed=false、eligible=false、hardware_tested=false。因浅边界无法给完整非上游补丁集合，更不能据清单更新源码或放行。

离线validate(raw,repo,current)严格解析重复JSON键/NaN，拒绝未知顶层字段，重新从同一已有对象图生成期望规范记录后逐字节规范比对，故记录重复、非法OID、路径遍历、父子/路径/哈希篡改和嵌套未知字段均拒绝；不接受声称自洽但与对象不符的记录。限制4096可见提交、每次Git输出4MiB、验证输入16MiB、命令5秒。规范负载不含当前时间或目录；文件输出复用已有原子不覆盖发布，既有不匹配拒绝，失败清理。

发生了什么：四项合成清单测试和三项既有门禁集成测试共七项最终通过；覆盖确定性、浅边界、实际移除父对象、分支/合并、多父、路径/哈希/OID/父列表篡改、未知/重复字段、jasmine-only线索及不匹配文件/IO失败无部分文件。首次直接测试选中了原本无父的记录，空列表修改不构成篡改；随后改为选择确有父的记录，重新通过。合成小Git仓库不是实际fork证据。

实际可见提交数量64，无法取得完整父差分的记录1；详见[规范清单](../research/shallow-inventory-stage/inventory.json)及[断点/清单哈希](../research/shallow-inventory-stage/checkpoint.json)。实际对象元数据已核对，两个真实6.6入口仍退出2，原源码锁/candidate锁/provenance及旧成果哈希保持。

可直接离线复核：

```sh
python3 tools/test_shallow_inventory.py
python3 tools/shallow_patch_inventory.py downloads/history-probe-73e35d6/fork --validate research/shallow-inventory-stage/inventory.json
```

第二条成功核验也始终退出2、eligible=false；--output只在完整生成/验证成功后原子发布不匹配拒绝。缺对象/树直接失败，不以题目或路径猜测填补。

下一断点：仅有浅图内线索与边界未知差分；官方候选图仍缺、完整上游成员与补丁携带政策仍未审。本轮不扩大为完整历史获取或移植。4.19、6.6与既有发布包不替换，不修改sources.lock/源码锁/候选锁/DTS/defconfig/boot/vendor/固件/init/fstab，无rebase/merge/cherry-pick、编译或打包。全部门禁保留，无真机测试，不宣称可刷、启动或硬件兼容。

[带时区记录](operations/shallow-inventory-2026-10-12.md)。本轮因测试修正与保存超过约3分钟目标，保存同步后立即暂停。实时额度无法读取，97%/55%仅用户快照，不声称精确保留。
