# 浅历史补丁复核队列

时间：2026-10-12T01:31:12.602623-07:00；基线12c94df。目标国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：只对已保存inventory规范字节离线整理，新增tools/shallow_review_queue.py版本wayne.shallow-review-queue.v1。先绑定checkpoint中inventory SHA256，再严格检查schema、字段/OID、record哈希、父可见性与边界/path状态；不调用Git或访问远端，不扩大来源认证。输入哈希是已保存证据绑定，不证明上游成员或真实硬件来源。

每项保存inventory_sha256、commit_oid、父对象/图内可见性、paths_known、全部机械分类与原始信号来源。subject信号保留原主题；path信号保留原路径及命中组件，只在paths_known=true时产生。规则literal-signal-strength-v1按非字母数字边界匹配wayne/sdm660/qualcomm/qcom/android/jasmine，qcom只映射qualcomm_generic。分类固定顺序wayne_explicit、sdm660_explicit、qualcomm_generic、android_generic；全部多重命中均保留。无这些分类但有jasmine信号时为jasmine_only；完全无信号时为no_target_signal。jasmine与其他词同时命中时仍保留原jasmine信号，不把它升级成wayne类别。

证据强度只是来源覆盖机械顺序：path_and_subject、path_only、subject_only、none；其后按分类优先顺序元组、OID排序。信号内部按token/source/text/component排序，不因主题显得重要而改变顺序。通用Qualcomm/Android信号不是设备专用证据，wayne_explicit也仅表示显式词命中，不证明适配目标或补丁必要性。

所有条目review_status=unreviewed、carry_decision=undetermined、upstream_membership_verified=false；队列history_complete=false、carry_strategy_reviewed=false、eligible=false、hardware_tested=false。不存在keep/drop推断、硬件分类或携带决定。

类别计数（多重命中可计入多个类别，总和不一定等于64）：

| 机械类别 | 数量 |
| --- | --- |
| wayne_explicit | 0 |
| sdm660_explicit | 14 |
| qualcomm_generic | 40 |
| android_generic | 0 |
| jasmine_only | 1 |
| no_target_signal | 22 |

实际队列64项均未复核，见[完整规范队列](../research/shallow-review-stage/queue.json)。validator严格解析未知/重复键及非有限值，依据原清单重新生成所有预期信号与固定状态，拒绝非法枚举、重复OID、伪造来源、哈希/顺序漂移及未知嵌套字段；不会接受“自报已审”字段。生成全部完成才使用同目录临时文件/fsync及原子不覆盖发布，既有不同字节拒绝，失败清理。

发生了什么：四项明确synthetic测试与三项既有门禁测试共七项通过，覆盖多重信号与排序、确定性、浅边界无路径、jasmine-only隔离、generic不升级、哈希/来源/枚举/排序篡改、重复项/非法OID/未知字段、已有输出冲突和注入IO失败无部分文件。合成inventory在测试函数内构造，不当作真实fork历史。实际64项另做生成/重新校验字节一致；两个6.6入口仍退出2，源码锁/candidate锁/provenance、原inventory及既有成果未改动。

可直接离线复核：

```sh
python3 tools/test_shallow_review_queue.py
python3 tools/shallow_review_queue.py research/shallow-inventory-stage/inventory.json --sha256 4be982d379dc87a1b87cf64a15a49dbc2bed7c989789fe6891f87f0ca2042ff7 --validate research/shallow-review-stage/queue.json
```

第二条成功也退出2，不提供更新资格。--output只发布完全验证后的队列，已有不匹配内容拒绝。

[断点/哈希](../research/shallow-review-stage/checkpoint.json)，[带时区记录](operations/shallow-review-2026-10-12.md)。下一步仅基于清单证据逐项独立人工审阅；浅图不等于完整非上游补丁集，完整上游归属及携带策略仍未建立。本轮无联网/加深/下载、rebase/merge/cherry-pick、固件/DTS/config/boot/vendor/init/fstab改动、编译或打包；保留4.19、DTB provenance及所有旧实验包和门禁。无真机测试，不宣称可刷、启动或硬件兼容。本轮实现验证与保存超过约3分钟目标，同步后立即暂停；实时额度不可读取，85%/53%仅用户快照。
