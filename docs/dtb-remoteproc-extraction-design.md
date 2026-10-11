# 完整DTB子节点证据提取：设计断点

时间：2026-10-11T10:01:20.030293-07:00；基线b941ebe。国行wayne/SDM660、原始静态分区，独立6.6实验，与Miku UI无关。

做了什么：检查工作区/status/diff、上轮报告/断点及read_dtb_identity、导入入口和测试。现有walker校验token后仅保留根model/compatible，丢弃子节点属性；不存在phandle索引、reg cell解释或binding引用解码。本轮采用用户明确允许的设计保存分支，不提交半成品提取器，不新增放行条件。

发生了什么：安全扩展不只是输出节点名。memory-region是phandle列表，但clocks/mboxes/interrupts-extended等可能带provider参数；任意32位cell不能当phandle。reg的宽度及地址空间由父节点/总线决定；GLINK/RPMSG/SMEM绑定可能通过父子关系或特定属性关联。未知binding不能靠名称猜语义。三个既有测试模块共九项测试通过，两个真实6.6 preflight仍退出2，五项保留哈希未变。没有新增remoteproc提取测试通过结果或二进制fixture，设计向量不是实测结果。

拟议最小结构（尚未实现）：

1. 从同一个至多8MiB的不可变字节快照计算SHA256并提取。共享现有严格v17结构walker，保留重复/截断/NUL/偏移/token拒绝；增加节点≤16384、属性≤65536、深度≤128、引用边≤65536和单属性长度≤1MiB上限。节点规范路径唯一，属性带结构块原始位置、长度和原始hex；失败给路径、偏移、属性名及错误码。任何失败退出非零，诊断不是合格提取结果。
2. 根身份复用已有导入拒绝规则；存在fdtget时优先对同一快照的临时只读文件取身份，工具失败不得回退掩盖。完整子树始终来自同一严格walker，不能用mock输出替代。当前入口未处理此快照一致性扩展，本轮不改代码。
3. 两遍索引phandle与linux,phandle：要求单个BE32且非0/0xffffffff；同节点两个声明必须一致；不同节点重复值拒绝。第一遍只建表，第二遍解析明确已支持的引用类型，允许正常前向引用，缺目标/长度非4倍数拒绝。索引不保证真实硬件绑定。
4. 枚举所有节点路径和实际compatible；remoteproc候选仅由后续审阅的、注明来源/版本/哈希的binding分类表识别。不能从adsp/modem等节点名字直接认定功能。尚无分类表时保留完整原始树清单及unclassified状态，不宣称不存在remoteproc。status和firmware-name仅记录实际属性及缺失标志，不填默认固件名，不从缺status推断运行状态。
5. memory-region按BE32纯phandle列表解码，输出属性原始位置、索引、原始值和目标路径；如有memory-region-names按实际字符串列表校验对应数量。对应目标须是/reserved-memory的合法子节点，目标越界或无法分类拒绝合格提取；不把FDT头部reservation map等同/reserved-memory节点。
6. reserved-memory输出实际reg原始cell、no-map/reusable及父节点#address-cells/#size-cells/ranges。仅支持明确声明的1或2 cell宽度，缺声明/未知宽度/不整除元组拒绝数值解码；先输出DT地址空间内的原始地址和长度，不推断CPU物理地址。未知非空ranges须标注unsupported，不静默做地址翻译。no-map/reusable须零长度且不能同时存在；无reg但size/alignment等动态分配形式单列unsupported，不猜最终地址。
7. GLINK/RPMSG/SMEM只输出实际父子包含关系和分类表明确支持的引用属性；每条边附binding依据及原始字节。未知供应者参数数量或未知属性保留raw/unresolved，并拒绝“关系完整”资格。只在已支持的依赖边子图中用有界迭代DFS检查循环，自环/循环拒绝；不能将所有cell或合法父子双向描述混成图误报循环。引用长度/值域/目标范围/图规模分别检查。
8. 输出恒定physical_identity_verified=false、board_bindings_verified=false、runtime_verified=false、build_gate_authorization=false。记录manifest来源/角色/采集命令/带时区时间、DTB SHA256/大小、header、节点/属性原路径、引用与错误。synthetic_fixture始终标明合成，不作为真实国行wayne布局；即便人为更改根身份字符串也不会解锁两个构建入口。

| 证据字段 | 处理规则 |
| --- | --- |
| source / sha256 / header / role | 来自原件快照和现有清单；来源声明不等于物理认证 |
| nodes[].path / raw_properties[] | 真实节点路径、原始偏移/长度/hex；无字段不得补值 |
| compatible / status / firmware-name | 严格NUL字符串或列表，重复/冲突拒绝，缺失显式记录 |
| memory_regions[].phandle / target_path | 只解析明确引用类型，保留顺序与原值，悬空拒绝 |
| reserved_memory[].reg / cells / ranges | 同时保留原始cell与明确宽度，未知转换不输出物理解释 |
| no_map / reusable | 由零长度属性实际存在性得出，冲突拒绝 |
| links[].kind / binding_basis / resolved | 不猜供应者参数，未分类关系不得宣称完整 |
| errors[].code / node_path / property / offset | 非零退出的诊断；不得留下部分“验证通过”结果 |

[十四类测试向量设计](../research/dtb-remoteproc-design-stage/test-vectors.json)覆盖合成正例、jasmine伪装、缺/重复/保留phandle值、循环、越界引用、reg宽度、布尔冲突、逐字节截断、结构畸形、未知binding、资源上限、可选缺字段及工具失败。下一实现阶段必须将这些构造为真实二进制小fixture并实际运行，不能用字符串改名或模拟解析结果代替。所有合成地址/固件/节点名仅格式输入，不作为wayne事实。

精确集成点：read_dtb_identity.read_identity内部walker可拆为受限树读取器，原根身份API行为必须用既有二进制回归保持；import_wayne_board_evidence.validate的dtb分支拟增加单独、明确的只读提取选项。该选项/提取器现在不存在，不提供虚构可运行命令。ci_kernel_66_probe.require_board_preflight及两个构建入口保持原样；boot与ABI仍是证据缺口记录，不是新增独立门禁。

当前可直接复核：

```sh
python3 tools/test_dtb_identity.py
python3 tools/test_wayne_board_evidence.py
python3 tools/test_6_6_gate_integration.py
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

实际材料待采集（尚未执行；失败须原样记录）：

```sh
adb pull /sys/firmware/fdt wayne-current.dtb
adb shell getprop > wayne-current-properties.txt
sha256sum wayne-current.dtb wayne-current-properties.txt
adb shell 'ls -l /sys/class/remoteproc; cat /proc/cmdline; cat /proc/mounts' > wayne-remoteproc-context.txt
adb shell dmesg > wayne-current-kernel-log.txt
```

保留来源、时间和原件；live FDT与原始boot DTB/DTBO不一定相同，须记录采集对象及overlay应用状态，不能相互替代。没有实物资料，无完整DTB提取结果；不写sysfs，不触发start/stop/SSR，不修改固件、DTS、内核配置、init或fstab，不下载或编译打包。

下一断点：先审阅上述受限共享walker与binding分类范围，再完整实现树索引+有类型引用+二进制向量测试，全部通过后才接只读证据输出；始终不接构建放行。若仍不能安全实现，继续保持设计状态，不宣称已完成提取。

[保存断点](../research/dtb-remoteproc-design-stage/checkpoint.json)。4.19/6.6及实验包均保留，SELinux、boot、ABI、固件与各硬件风险未解除。测试/解析成功不是真机启动验证。实时额度不可读取，57%/80%仅用户快照；同步后立即暂停。
