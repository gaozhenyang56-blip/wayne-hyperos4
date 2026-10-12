# 下一批三个缺失blob有界探针

时间：2026-10-12T07:45:28.883484-07:00；基线cee01fc。国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：检查工作区/断点和原manifest、单对象及四项批次；重新离线核验前五个对象及上一批字节哈希。按原162个OID规范排序排除已验证前五个，只取紧接三项，全局从0计数为5/6/7。远端只采用已有证据固定https://github.com/sdm660-mainline/linux.git。

复用旧four_blob_batch_probe.py的请求循环和完整逐项校验，最小抽取内部_run_selected/_validate_selected并参数化数量、阈值与计数基准；原run/validate签名、wayne.four-blob-batch.v1输出和旧证据保持兼容。新增next_three_blob_probe.py薄封装，用wayne.incremental-blob-batch.v1绑定manifest、单对象、上一批规范SHA256及全局序号，内部wayne.isolated-blob-batch.v2记录三项结果。版本扩展原因仅为增加上一批链绑定、3项数量和本轮新增payload阈值，不改写旧schema/证据，不重写请求/校验框架。

每OID独立downloads/next-three-blob-probe-cee01fc/0..2裸库各一次精确请求，60秒期限，原16MiB对象/包上限与禁交互/重定向/LFS smudge规则继承；无重试、加深、完整克隆、递归历史或补取其他OID。失败或认证/过滤不支持/响应异常/人机挑战即停止，后续not_attempted/object=null。达到512KiB本轮新增已验证payload后不再启动下一项；阈值作用于batch_verified_payload_bytes，而不是前批累计。当前请求成功可能越过阈值，故不宣称总payload硬性永不超过512KiB；轮询存在调度延迟，不声称零超调。

实际结果：三次均success，stop_reason=completed，未尝试项0。

| 全局序号（从0计） | OID | payload字节 | 结果 |
| --- | --- | --- | --- |
| 5 | 06f8ff624181fc1dde3fa825a86f15dee6249a9e | 16144 | success |
| 6 | 09a0c35dd514c927650cb9e23fbe893052f7adb5 | 137687 | success |
| 7 | 0ab09b0d44404b7f6d7a3bee5689b0dccadaf1a1 | 12232 | success |

本轮新增166063字节，低于524288字节阈值；旧累计185009字节，更新累计351072字节。逐项cat-file验证blob类型并按Git对象头部/内容重算OID，内容SHA256见规范证据；每个隔离库只含所请求对象，不导入主对象库/原fork/源码锁或构建输入，不上传blob内容。原始网络诊断留隔离目录，公开仅非敏感命令/exit/严格结果/大小/OID/哈希；时间仅run.json及操作记录，不进入规范负载。

离线validator复用旧校验，先重验上一批及完整前五项前缀，再核对新规范选择/全局顺序/链哈希/逐项对象和响应哈希、请求数、累计与本轮计数、停止规则及false状态。未知/重复字段/OID、非法hash、旧已验证对象重复选择、链绑定/顺序漂移、成功类型/OID/hash不符、失败或未尝试元数据、停止后请求和payload矛盾均拒绝。原子不覆盖发布及失败清理沿用原工具；已有不同输出拒绝。

发生了什么：原单对象四项、原四项批次四项、增量链四项和门禁三项共十五项测试通过。网络测试全部为明确synthetic的本地Git服务，覆盖旧v1完整兼容、全成功、增量链/全局排序/重复选择与输入篡改、累计计数、已有输出冲突、新阈值不受旧累计误触发、达到阈值后停止、第二项拒绝后未尝试、旧超时/类型/哈希与失败清理。实际旧v1证据另已核验字节不变；两个实际6.6入口仍退出2，旧单对象工具/清单/源码锁/候选锁/provenance与实验包哈希保持。

[第二批规范证据](../research/next-three-blob-stage/batch.json)，[结果/保留哈希/断点](../research/next-three-blob-stage/checkpoint.json)。可直接运行相关完整离线测试（仅合成本地Git服务）：

```sh
python3 -m unittest discover -s tools -p 'test_single_object_probe.py'
python3 -m unittest discover -s tools -p 'test_four_blob_batch.py'
python3 -m unittest discover -s tools -p 'test_next_three_blob_batch.py'
python3 tools/test_6_6_gate_integration.py
```

离线新validate API必须给旧manifest/single/previous的精确原字节、三个绑定SHA及旧/新隔离根目录；不再调用run，禁止重复本轮实际网络批次。旧validate入口仍可核验旧证据。全部history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/hardware_tested为false；八个孤立blob成功不代表完整历史、上游归属或携带策略。

下一断点：仅审阅现有隔离对象利用与后续独立范围，本轮不扩更多获取、不迁主库、不做资格放行。无rebase/merge/cherry-pick、DTS/defconfig/boot/vendor/固件/init/fstab改动、编译/打包或真机测试；保留4.19及全部旧实验/发布包/门禁，不宣称可刷、启动或硬件兼容。

[带时区记录](operations/next-three-blob-2026-10-12.md)。实时额度不可读取，71%/40%仅用户快照；同步后立即暂停。
