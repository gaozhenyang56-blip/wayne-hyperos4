# 首个隔离 blob 浅历史边界父提交补证

时间：2026-10-13T00:47:00.698147-07:00；基线a091e75。国行wayne/SDM660静态分区、独立Linux 6.6实验，与Miku UI无关。

做了什么：检查status/diff、最近执行结果和历史边界断点。没有已跟踪修改，原有空白未跟踪MD保留。重用完整隔离blob/归属/历史边界校验，确认原边界71c631a9fb211df4ea5a59ac68a310c5854f07f1的原始commit父为6fbaeffc3a92b4a32b8e320e486cf644ff30d240，且该父在主Git库与原fork库均missing。只处理首个blob和已证精确路径，不扫描第二blob或其他历史分支。

随后对原锁https://github.com/sdm660-mainline/linux.git发起一次精确父OID fetch，独立bare目录downloads/parent-commit-probe-a091e75，depth=1、filter=blob:none、无tag/子模块/FETCH_HEAD写入、禁凭证交互与重定向。60秒截止杀进程组，对象存储超过8MiB或认证/过滤不支持/人机验证/异常即停止，无重试。该命令仅请求一个提交及其树闭包，不补其父历史，不取得blob内容；不是完整源码克隆或批量加深。请求命令与响应字节哈希在规范证据中，当前时间仅进本记录/操作日志。

发生了什么：唯一一次请求退出0。独立对象存储2807933字节；类型枚举仅一个指定commit及tree，无blob或其他commit。depth=1 shallow记录仅6fbaeff…；对象文件按相对名称记录大小和SHA256。提交类型commit、853字节，重算Git OID完全匹配，commit原始SHA256为aa328514a6bd3b7c65cfd295e56e6feec26b652f8ea6fbd0877758318b9fdb17，根树961dcbc0ae13197dc288075f0929d5ea38dd94f7。原始commit记录的更早父为50ae1c470491481328363639c227020691469f29，本轮不获取。

逐级类型/OID/原始SHA256树链证明父提交在arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi路径上仍引用001fb2723fbb7c6dd6a2f19ef00bdfb862a17bf4，与71c631a…的同路径相同。blob类型/17271字节/规范内容SHA256958dd0d910f9cfed3914fa628e12a4ff2e3bfa7fcb6342accfa8a543abdff495由原隔离证据再次核对。此处排除71c631a…相对直接父的该路径引入转换；只能将“已存在”的祖先见证推进到6fbaeff…，不能确定更早来源或全历史唯一。

最小新增isolated_parent_commit_probe.py，显式--attempt才能请求；已存在请求目录拒绝再次执行。默认audit/check只读且禁协议/lazy fetch。schema=wayne.isolated-parent-boundary-evidence.v1，绑定原boundary规范SHA256及独立request规范SHA256，记录原child树链、新parent树链、同路径差异、请求次数/边界/响应哈希和对象文件哈希。未知字段、非法OID/类型、链漂移、树关系不一致、额外历史/blob、主对象库污染和资格误报拒绝，原子不覆盖发布。失败不提供合格parent快照，解析异常也不发布部分证据。规范负载不含当前时间或绝对工作区路径。

四项实际隔离父/确定性、明确synthetic格式/树/链/资格篡改、synthetic错误分类、原子冲突测试通过；既有门禁三项通过，共七项，无测试网络请求。两个实际6.6入口仍退出2。上轮保留清单全部SHA256不变，父commit仍不进入主库或原fork库。history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/source_lock_input/build_gate_authorization/hardware_tested均false；relationship_status仍unresolved，局部引入边界和唯一引入提交均null。

[规范证据](../research/isolated-parent-stage/evidence.json) · [请求证据](../research/isolated-parent-stage/request.json) · [实际测试及断点](../research/isolated-parent-stage/checkpoint.json) · [带时区操作记录](operations/isolated-parent-2026-10-13.md)

仅离线复核（不要再次--attempt）：

```sh
python3 tools/isolated_parent_commit_probe.py --check research/isolated-parent-stage/evidence.json
python3 tools/test_isolated_parent_commit_probe.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：6fbaeff…仍携带相同blob，唯一引入阻断不变。更早父50ae1c…仅为已解析commit中的OID声明，其精确路径树关系未核验，不把父OID声明当内容/来源证明。本轮请求额度已用完，不递归、不重试、不自动获取该父，不扩展其他路径/分支。后续阶段需另行限定证据范围与停止条件；更新资格/候选携带策略未审。

无rebase/merge/cherry-pick、主库对象迁移、sources.lock/候选锁、DTS/defconfig/boot/vendor/固件/init/fstab/4.19/provenance/既有实验包修改，无编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。77%/96%为用户额度快照，无法读取实时额度，不声称精确控制或保留。同步GitHub后立即暂停。
