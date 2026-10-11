# DTB身份读取回退阶段

时间：2026-10-11T06:15:22.341250-07:00；基线580cfc9，目标仅国行wayne/SDM660原始静态分区，与Miku UI无关。

做了什么：新增tools/read_dtb_identity.py，工具缺失时只读解析v17（last compatible=16）FDT。限制8MiB、128层与4096项reservation；检查magic、总长度、块边界/重叠/对齐、reservation终止、token/嵌套、属性长度与名称偏移、NUL和填充、重复节点/属性及END。仅输出根model、compatible、必要头部信息；未知版本、结构或非ASCII身份拒绝。优先现有fdtget；其失败直接拒绝，不回退掩盖。未接入任何构建放行。

发生了什么：新增四项测试通过，两个既有入口回归通过。使用仓库真实二进制小fixture（明确为合成格式向量，不是真实wayne设备树），覆盖正例、compatible=jasmine而model=MI 6X伪装、model冲突、畸形和截断。遍历正例每个截断长度，另测偏移、token、缺NUL与重复属性。移除旧入口测试中的模拟身份解析结果；工具失败测试仅模拟失败，不产生身份字段。当前无fdtget，实工具路径未验证；两个真实6.6 preflight仍返回2，五项既有材料哈希未变。未改板级DTS、内核配置、4.19或实验包，未编译/下载，无真机验证。

直接检查：

```sh
python3 tools/test_dtb_identity.py
python3 tools/test_wayne_board_evidence.py
python3 tools/import_wayne_board_evidence.py tests/fixtures/wayne-evidence/dtb-manifest.json
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

下一步：取得实际国行设备的来源/采集链材料，命令尚未执行：

```sh
adb shell getprop > wayne-current-properties.txt
adb pull /sys/firmware/fdt wayne-current.dtb
sha256sum wayne-current-properties.txt wayne-current.dtb
```

失败原样保存；按上一轮清单填写真实来源、带时区时间、实际命令及哈希，保持本地原件。身份字符串一致不能证明实物来源或板级绑定，即便人为同时修改字符串也不会解锁门禁。DTBO、完整语义/include、overlay以及真实板级差异均未验证；解析器通过不等于启动、GPU或任何硬件可用。SELinux、显示、相机、音频、加密、固件/remoteproc等阻塞保留。

[断点](../research/dtb-reader-stage/checkpoint.json)。上一轮报告的“缺fdtget拒绝DTB”是历史状态，本轮以受限回退更新，实物证据缺口不变。实时额度不可读，63%/89%仅用户快照；同步后立即暂停。
