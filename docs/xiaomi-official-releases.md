# 小米官方仓库 release 元数据核验

时间：2026-10-13T08:44:35.202467-07:00；基线1f2a896。国行wayne/SDM660静态分区、独立6.6实验；当前系统与具体布局未验证的信息仍待核实，不以jasmine、Miku UI或其他设备替代。

做了什么：检查status/diff、前序分支/标签阴性证据和下一断点，无已跟踪修改，原空白未跟踪MD保留。离线重验既定MiCode/Xiaomi_Kernel_OpenSource来源链及1f2a896 Git绑定，没有重复分支/标签查询。

只请求https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/releases?per_page=20&page=1一次；60秒总超时、15秒连接超时、1MiB正文上限、零重试且不跟随重定向。请求开始独占标记防重复。不分页递归、不查询其他仓库、不取源码树或附件，遇认证/拒绝/限流/人机验证/异常停止，不交互或绕过。

发生了什么：curl退出0，HTTP200。正文是完整JSON空数组，共5字节，与Content-Length=5一致；最终API响应Content-Type为application/json，无Link分页头，未请求下一页。response_scope逐项记录page=1/per_page=20、returned_releases=0、transfer_complete=true、has_pagination_link=false、additional_pages_requested=false、attachments_downloaded=false。原始响应、HTTP头和stderr保留哈希，headers中的动态时间只作为原始查询证据，不直接进入生成的规范字段。

设备匹配规则限定wayne、MI 6X（含已知间隔拼写）、小米6X，本页零发布，匹配候选为空。source_entry=null、discovery_status/target_association=unresolved。此结果仅描述本次API响应范围，不推出所有官方源码入口不存在；不把release稳定ID或可变target_commitish冒充Git不可变对象。若未来离线fixture有匹配，仅保留发布ID/官方URL/tag/设备文字命中、原文哈希及声明commit OID未验证状态，不提升板级或构建资格。

新增必要的wayne.official-releases-evidence.v1及离线校验，绑定前轮标签证据与实际请求/响应哈希。校验固定官方URL、一次第一页策略、最终HTTP状态、正文完整性、分页头、来源/发布ID一致性、重复键和哈希漂移；未知自有schema字段、第三方冒充、可变引用误报、资格误报及源码对象导入主库均拒绝。发布沿用原子不覆盖写入，失败不留下部分合格结果，规范JSON无当前时间/绝对路径。

三项实际完整空页/字节稳定、明确synthetic分页/候选可变目标/限流拒绝/来源漂移、schema/哈希/资格误报与原子冲突测试通过；三项既有门禁测试通过，共六项。合成发布不是实际官方入口。两个实际6.6 preflight均退出2。保留清单全部SHA256不变，sources.lock、候选锁、4.19/6.6成果、DTB provenance和既有包保留；无DTS/defconfig/boot/vendor/固件/init/fstab改动、对象迁移、编译或打包。history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/build_gate_authorization/source_lock_input/hardware_tested全部false。

[规范结果](../research/xiaomi-official-releases-stage/discovery.json) · [实际请求](../research/xiaomi-official-releases-stage/request.json) · [原始正文](../research/xiaomi-official-releases-stage/response.body) · [测试及断点](../research/xiaomi-official-releases-stage/checkpoint.json) · [带时区记录](operations/xiaomi-official-releases-2026-10-13.md)

仅离线复核：

```sh
python3 tools/check_xiaomi_official_releases.py --check research/xiaomi-official-releases-stage/discovery.json
python3 tools/test_xiaomi_official_releases.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一项有信息增益的可行工作：同一官方仓库的产品发布索引/README映射精确核验，寻找明确Mi6X/wayne产品标注、所指发布引用与文件/对象标识，而非重复空heads/tags/releases查询。需另定一次有界文件元数据范围和停止条件，不能把官方表中同平台引用自动等同真实国行板级包含链，更不能回退第三方或jasmine。当前没有执行此请求，源码入口和pm660关联仍未决，保存后暂停。

无真机验证，不宣称可启动、可刷或移植完成。48%/83%仅用户额度快照，无法读取实时值，不声称精确保留约20%。同步GitHub后立即暂停。
