# 小米官方 wayne 源码发布入口发现

时间：2026-10-13T05:35:26.277041-07:00；基线8c94125。国行wayne/SDM660静态分区、独立Linux 6.6实验，与Miku UI无关。

做了什么：检查status/diff、最近提交、pm660关联报告与实际测试；没有已跟踪改动，原空白未跟踪MD保留。离线检查现有文档、锁和来源记录，未发现已固定的小米官方wayne发布入口；已记录的Miku和jakecommon来源不升级为官方或真实国行板级基线，不继续第三方jasmine包含链。

仅对已知小米开源主体MiCode的固定仓库https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git执行一次窄范围git ls-remote --heads查询，模式refs/heads/wayne*。这次唯一仓库选择基于已知官方开源主体，不是多个仓库猜测或通用搜索。60秒截止杀进程组、响应大小限制64KiB、禁止交互认证/重定向，认证/拒绝/人机验证/异常停止；无重试、替代源、第三方fork枚举、源码克隆/下载或递归API。

发生了什么：实际命令退出0，stdout和stderr均为空，匹配引用为0。空字节SHA256为e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。请求次数、固定URL、精确命令、结果及响应哈希保存于query-run.json和discovery.json。没有取得或导入任何源码对象，没有可固定的分支/tag/commit，source_entry=null、discovery_status=unresolved。

结论严格限于该仓库在此次查询的wayne前缀heads范围没有返回匹配。不能推出小米没有发布过6X源码、没有其他命名分支/标签/发布表或其他官方入口。未查这些范围，也不把jasmine或同平台通用树替代为wayne。MiCode仓库的选择/可达元数据不是实际国行板级包含链证明，board_baseline_verified=false、target_association=unresolved。没有解析任何新的板级include链。

最小新增wayne.xiaomi-official-source-discovery.v1及离线校验器，绑定8c94125已有pm660关联规范哈希和原始query-run哈希。固定官方命名空间/仓库/精确查询范围，严格拒绝未知字段、重复键、非法OID、URL或命令漂移、响应哈希篡改、截断和重复/冲突ref。可变分支不能单独成为入口，必须同时固定广告OID；多匹配不自动择一。第三方fork URL拒绝。若实际响应含OID，audit须检查它仍未导入主库；本次没有响应对象，ls-remote不写对象库。报告发布复用原子不覆盖工具，失败无部分合格记录，规范负载不含当前时间或绝对目录。

实际空响应/字节稳定测试，以及明确synthetic引用的不可变OID绑定、重复/第三方/哈希/未知字段/可变ref-only拒绝、多匹配不择一、资格漂移和原子冲突测试三项通过；三项既有门禁测试通过，共六项。合成引用不是实际官方发布证据。两个实际6.6入口仍退出2，保留清单全部SHA256未变。history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/build_gate_authorization/source_lock_input/hardware_tested全部false。

[规范发现报告](../research/xiaomi-official-entry-stage/discovery.json) · [实际查询记录](../research/xiaomi-official-entry-stage/query-run.json) · [测试及断点](../research/xiaomi-official-entry-stage/checkpoint.json) · [带时区操作记录](operations/xiaomi-official-entry-2026-10-13.md)

仅离线复核，不再次查询：

```sh
python3 tools/check_xiaomi_official_source_entry.py --check research/xiaomi-official-entry-stage/discovery.json
python3 tools/test_xiaomi_official_source_entry.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：官方入口未固定，实际查询范围已用完。若后续另定短阶段，应先明确官方发布表/发行说明/标签等一种精确证据范围，核对设备标注及不可变OID；不能拿此次空heads响应猜别的分支、自动扩大搜索或重试。本轮保持unresolved并暂停，不导入源码、不解析包含链、不更改任何锁。

无fetch/clone/rebase/merge/cherry-pick、对象迁移或候选锁/DTS/defconfig/boot/vendor/固件/init/fstab/4.19/provenance/既有包修改，无编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。87%/89%仅用户额度快照，无法读取实时用量，不声称精确控制或保留。同步GitHub后立即暂停。
