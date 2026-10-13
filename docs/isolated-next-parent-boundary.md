# 首个隔离 blob 再向前一层直接父补证

时间：2026-10-13T01:22:17.760330-07:00；基线7ed2ee3。国行wayne/SDM660静态分区独立Linux 6.6实验，与Miku UI无关。

做了什么：先检查工作区status/diff、上轮规范证据/断点及实际测试。无已跟踪修改，原有空白未跟踪MD保留。复用前序所有本地证据链校验，从隔离库中实际6fbaeffc3a92b4a32b8e320e486cf644ff30d240提交原始字节再次重算OID/SHA256并解析parent，明确得到唯一直接父50ae1c470491481328363639c227020691469f29；不是猜测或把断点文字当提交证明。确认它在主库、原fork库和前轮隔离库均missing。

随后只对原固定https://github.com/sdm660-mainline/linux.git请求该精确OID一次。独立bare目录downloads/next-parent-probe-7ed2ee3；复用原引擎的60秒截止、8MiB对象存储停止阈值、depth=1/blob:none、禁认证交互/重定向、无tag/子模块/FETCH_HEAD写入和异常停止逻辑。未重试、换源、递归获取祖先或补blob。只取得指定commit及其tree闭包，不是完整源码/批量历史。

发生了什么：请求退出0，隔离对象存储2808402字节；类型清单只有一个指定commit及tree，无blob或其他commit，shallow仅该父。50ae1c…类型commit、1856字节，重算Git OID完全一致，原始SHA256为aca6379c910df8a751d08f42aa536d3eb092f93f51a3279f3ec7e550b908f6a8，根树1dc2140d99e2cb0717de90bd6abc86fbd6b65c87。逐级树链证明其在arch/arm64/boot/dts/qcom/sm8450-sony-xperia-nagara.dtsi路径仍引用001fb2723fbb7c6dd6a2f19ef00bdfb862a17bf4，和直接子6fbaeff…相同。

首blob的类型blob、17271字节、规范内容SHA256958dd0d910f9cfed3914fa628e12a4ff2e3bfa7fcb6342accfa8a543abdff495及隔离链重新核对。此次排除6fbaeff…相对直接父的该路径引入转换，只证明该blob已经存在于50ae1c…快照；唯一引入、wayne适用性、上游成员关系或携带策略仍未证明。局部引入边界/唯一引入提交均null，relationship_status=unresolved。

最小增量isolated_next_parent_probe.py复用原请求和树校验代码，通过独立模块实例设置已解析的一层上下文，不改原引擎文件或原模块全局。新增schema=wayne.isolated-next-parent-boundary-evidence.v2，用previous_evidence_sha256明确绑定上轮证据，另绑定原引擎源码SHA256；版本递增原因是输入来源由初始shallow报告变为前轮已验证parent快照。嵌套request_engine_evidence保留v1引擎记录结构，其中旧boundary_sha256字段在此适配上下文中绑定前轮evidence规范字节；它不是最初boundary.json的哈希，也不作为原v1独立入口输入。仅v2适配器重读实际父对象、校验前序链后核验新记录。原v1证据及入口仍原样可验证。

规范负载稳定UTF-8，无当前时间/绝对目录，保留请求精确命令、父OID解析命令、child/parent树链、对象文件哈希、次数和边界。严格比较实时重审得到的规范字节，未知字段、重复/非法OID、类型/树关系/证据绑定漂移、主库污染或资格误报拒绝；复用原子不覆盖发布，异常不输出部分合格记录。默认check/audit禁协议和lazy fetch；--attempt仅显式请求，已存在隔离目录即拒绝重试。

三项真实本地父关系/稳定字节、明确synthetic格式/链/树/资格篡改拒绝、原子冲突测试通过；三项既有门禁测试通过，共六项，测试无网络动作。两个实际6.6 preflight退出2。旧引擎、上轮规范证据/请求和原边界字节与7ed2ee3完全一致；原保留清单全部SHA256不变。新对象未进入主库、原fork库或旧隔离库，未写任何锁/构建输入。内外层history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/source_lock_input/build_gate_authorization/hardware_tested均false。

[规范增量证据](../research/isolated-next-parent-stage/evidence.json) · [实际请求](../research/isolated-next-parent-stage/request.json) · [测试及断点](../research/isolated-next-parent-stage/checkpoint.json) · [带时区操作记录](operations/isolated-next-parent-2026-10-13.md)

仅离线复核，不再次--attempt：

```sh
python3 tools/isolated_next_parent_probe.py --check research/isolated-next-parent-stage/evidence.json
python3 tools/test_isolated_next_parent_probe.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：首blob在50ae1c…同路径仍存在，唯一引入继续阻断。该commit记录的唯一父9a6ed4ea985ac4b7a566faddeb16271b8ea54d36仅是新提交原始字节中的parent声明，未取得/核对其树，不推断其内容。请求已用完，到此停止，不自动补下一层、不扩展其他路径/旁支或第二blob。

无rebase/merge/cherry-pick、对象迁入主库、sources.lock/候选锁/DTS/defconfig/boot/vendor/固件/init/fstab/4.19/provenance/旧实验包修改，无编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。68%/95%只为用户额度快照，无法读取实时用量，不声称精确控制或保留。同步GitHub后立即暂停。
