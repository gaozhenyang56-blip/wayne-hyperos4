# 单对象有界获取探针

时间：2026-10-12T04:47:46.520400-07:00；基线20c9575。国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：检查工作区/status/diff与获取manifest，实际绑定manifest SHA256=009b810703be74bb37a1f12ce29f489898c0463c2ff7f05a5ced3eeef8094379；从已保存fork-fetch.json读取固定https://github.com/sdm660-mainline/linux.git，核对固定URL。对162个缺失blob按OID排序，只选择首个001fb2723fbb7c6dd6a2f19ef00bdfb862a17bf4。

仅在新downloads/single-blob-probe-20c9575隔离裸库进行一次git fetch --no-tags --no-recurse-submodules --no-write-fetch-head URL OID，精确单OID，无filter/depth/完整克隆/递归补取/回退或重试；未改主工作树或主对象库。禁Git交互/重定向/LFS smudge；60秒期限后终止整个进程组，16MiB对象/包与1MiB诊断上限，循环及最终复核越界后失败。检测轮询存在调度延迟，不宣称零超调；本次远端实际迅速完成，未接近期限。认证/人机挑战/过滤不支持等严格枚举并停止，不交互。

真实结果：success，blob大小17271字节。git cat-file确认type=blob，按Git blob头部与内容重新计算OID完全匹配；内容SHA256=958dd0d910f9cfed3914fa628e12a4ff2e3bfa7fcb6342accfa8a543abdff495。隔离库枚举到的对象仅为该OID，无额外对象；对象没有转入原fork库、源码锁或构建输入，也未上传blob内容。公开证据只含请求参数、exit/result、类型/大小/OID/哈希与false状态；原始网络诊断仅留隔离库，不上传可能敏感响应。

新增single_object_probe.py，版本wayne.single-blob-probe.v1。实际查询时间仅在非规范run.json/操作记录，规范负载无当前时间或临时目录。validator拒绝未知/重复字段、非法OID/hash、manifest/选择排序/URL/命令/timeout漂移，重新核对成功对象type/OID/content hash，失败object必须null；本地响应原字节可用时核对stdout/stderr哈希。原子不覆盖发布，既有不同字节拒绝，异常清理；main远端执行只有本轮单次调用，不提供自动批量路线。

发生了什么：四项synthetic本地Git服务/对象测试和三项门禁测试共七项最终通过：实际本地服务精确blob成功/拒绝、合成ext本地sleep服务超时并杀进程组、tree类型拒绝、实际篡改loose blob后Git OID拒绝、manifest/字段/失败元数据/排序/响应绑定校验及输出冲突/IO失败清理。synthetic超时测试使用缩短期限，真实请求固定60秒；没有把本地测试当真实远端证据。首次篡改测试遇Git对象只读权限，已仅对合成临时对象chmod后重跑；没有重复实际远端请求。失败与复测日志保留。

所有结果history_complete=false、upstream_membership_verified=false、carry_strategy_reviewed=false、eligible=false、hardware_tested=false；单blob取回只证明一次对象传输与内容OID校验，不证明上游成员、补丁可移植、来源认证、硬件或启动可用。两个实际6.6入口仍退出2，原manifest、源码/候选锁、provenance及旧成果哈希保持。

[规范探针证据](../research/single-object-stage/probe.json)，[测试/保留哈希/断点](../research/single-object-stage/checkpoint.json)。离线测试：

```sh
python3 tools/test_single_object_probe.py
```

离线API validate(raw_probe, original_manifest, manifest_sha, isolated_repo)只读取已有结果/对象；复核不得再次调用attempt。attempt创建隔离目录要求不存在，不可复用已存在库悄悄重试。输出使用已有_write_payload原子发布，未接入获取manifest授权或构建门禁。

下一断点：这一对象仅在探针库，原162对象清单仍描述原fork库状态。若未来要处理更多对象或迁入审计库，必须独立定义精确范围/大小/时间与完整性要求，本轮不继续。没有fetch以外的远端操作、rebase/merge/cherry-pick、DTS/defconfig/boot/vendor/固件/init/fstab改动、编译/打包；保留4.19与发布包/全部门禁，无真机测试。

[带时区记录](operations/single-object-2026-10-12.md)。实时额度不可读取，44%/46%仅用户快照；保存同步后立即暂停。
