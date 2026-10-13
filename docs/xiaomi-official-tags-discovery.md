# 小米官方源码标签元数据补充核验

时间：2026-10-13T06:42:18.502135-07:00；基线6e0419f。国行wayne/SDM660静态分区、独立Linux 6.6实验，与Miku UI无关。

做了什么：检查status/diff、最近提交、上一轮真实空响应及断点，无已跟踪改动，原空白未跟踪MD保留。离线核验原MiCode/Xiaomi_Kernel_OpenSource固定URL、命令、响应哈希、discovery规范哈希与6e0419f Git字节一致；未重复heads分支查询，也未据前轮阴性结果声称小米没有其他官方入口。

只选择本轮允许的tags引用范围，对同一仓库执行一次git ls-remote --tags。筛选为wayne、mi6x/MI6X/Mi6X及连字符/下划线拼写、小米6X/小米6x；这些是同一既知产品标识的有限拼写，不新增其他设备标识。精确命令保存在query-run.json。60秒截止杀进程组、响应64KiB停止阈值、禁交互认证/重定向，遇拒绝/异常/人机验证/速率限制停止。请求开始标记以独占创建防重复。本轮未查release API/发布说明，不回退、不重试，不查其他仓库或第三方fork。

发生了什么：实际标签查询退出0，stdout/stderr均为空，匹配标签0。原始空字节SHA256为e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855，实际响应与单次请求记录已保存。没有可审计的目标tag/不可变对象绑定，因此source_entry=null、discovery_status=unresolved、target_association=unresolved；没有取得或导入任何源码对象。

结果只说明本次同仓库、这些名称模式的标签广告没有匹配。不能外推全局不存在官方6X源码、没有其他命名tag/release、发布表或历史入口。release_api_queried=false、no_global_absence_claim=true；未验证真实国行板级基线，未解析include链，不回退jasmine/其他SoC/Miku UI。

最小新增wayne.xiaomi-official-tags-discovery.v1及只读离线校验器，绑定前轮discovery规范SHA256和实际query-run SHA256。规范JSON无当前时间/绝对工作区路径，固定官方命名空间URL和单次查询命令，拒绝未知字段/重复键、来源与输入绑定漂移、非法OID、重复/冲突ref、截断或哈希篡改及第三方URL冒充官方。若有唯一明确设备标签，仅完整tag对象/peeled OID广告可作为元数据固定候选，不能以可变名称单独冒充不可变源；缺peeled、多匹配或标签含混继续unresolved。实际有响应OID时检查主库仍missing它们；本次响应为空且ls-remote不写对象库。原子不覆盖发布，异常无部分合格记录。

三项实际空响应与稳定字节、明确synthetic tag/peeled/来源/输入漂移拒绝、资格误报与原子冲突测试通过；三项既有门禁测试通过，共六项，合成标签不是实际发布证据。两个实际6.6入口退出2。保留清单全部SHA256不变；sources.lock、候选锁、4.19/6.6成果、provenance及包未改，未迁对象或新增构建输入。history_complete/upstream_membership_verified/carry_strategy_reviewed/eligible/build_gate_authorization/source_lock_input/hardware_tested全部false。

[规范报告](../research/xiaomi-official-tags-stage/discovery.json) · [实际查询](../research/xiaomi-official-tags-stage/query-run.json) · [测试及断点](../research/xiaomi-official-tags-stage/checkpoint.json) · [带时区记录](operations/xiaomi-official-tags-2026-10-13.md)

仅离线复核，不重复查询：

```sh
python3 tools/check_xiaomi_official_tags.py --check research/xiaomi-official-tags-stage/discovery.json
python3 tools/test_xiaomi_official_tags.py
python3 -m unittest discover -s tools -p test_6_6_gate_integration.py -v
```

下一断点：官方源入口仍未固定。本次没有查询release正文/发布表，其他命名不在范围内；如后续另定阶段，需要先限定同一官方主体的一种精确发布元数据证据范围及设备标识/不可变OID判据，不自动扩大搜索、不重复heads/tags、不在此阶段追加请求。暂停，不导入源码或解析板级包含链。

无fetch/clone/rebase/merge/cherry-pick、源码迁移、锁/DTS/defconfig/boot/vendor/固件/init/fstab/4.19/provenance/既有包修改，无编译或打包。无真机测试，不宣称可启动、可刷或硬件兼容。75%/87%仅用户额度快照，无法读取实时用量，不声称精确控制或保留。同步GitHub后立即暂停。
