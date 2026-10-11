# 本地板级证据入口

时间：2026-10-11T12:56:09.194889+00:00；基线38f41da。目标仅国行wayne/SDM660、原版静态分区；不以jasmine或Miku UI为目标。

做了什么：新增tools/import_wayne_board_evidence.py，只读检查清单中的来源说明、带时区采集时间、采集命令、机型/区域/布局声明、文件SHA256及可解析身份字段。最小格式参见tests/fixtures/wayne-evidence/manifest.json，明确标注synthetic_fixture，不能冒充真机材料。真实导入使用actual_device_capture，来源声明仍须人工核实。getprop核对device/model及其他产品device，DTB由fdtget解析根model/compatible。文件缺失、路径越界、哈希错误、来源不明、jasmine身份、model或compatible不一致及缺解析工具均拒绝。boot参数、DTBO和分区表格式本轮尚未实现，提交这些kind将拒绝。

发生了什么：两个测试方法涵盖一个合成正例和七个拒绝分支。DTB compatible负例使用模拟解析器，当前无fdtget，没有真实DTB解析通过结果。两个真实6.6 preflight均退出2；五项保留材料哈希不变。校验仅验证声明一致性，无法识别所有人为伪造或证明国行实物身份；所有输出physical_identity_verified、board_bindings_verified和build_gate_authorization均为false。没有把输入清单接入既有构建门禁，没有修改DTS、内核配置或实验包，无编译/下载/真机验证。

可直接执行：

```sh
python3 tools/test_wayne_board_evidence.py
python3 tools/import_wayne_board_evidence.py tests/fixtures/wayne-evidence/manifest.json
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

下一步：在用户实际设备采集，以下命令尚未执行，权限失败须保存原始错误：

```sh
mkdir -p local-wayne-evidence
adb shell getprop > local-wayne-evidence/getprop.txt
adb pull /sys/firmware/fdt local-wayne-evidence/wayne-current.dtb
adb shell 'cat /proc/cmdline; cat /proc/partitions; find /dev/block -type l' > local-wayne-evidence/boot-partitions.txt
sha256sum local-wayne-evidence/*
```

复制fixture清单到本地证据目录，改为实际来源与时间、实际执行命令，替换每项路径与真实哈希；不得把fixture当实物。当前仅支持getprop/dtb，boot-partitions保留为待人工解析材料。DTB需要可用fdtget，否则明确拒绝；即便身份一致也须另行真实板级绑定对照，不解锁6.6。公开上传前去除属性中的设备个人标识；本地保留原件，脱敏副本重新哈希并记录处理，不把脱敏副本当原始捕获。

[断点](../research/board-evidence-stage/checkpoint.json)。SELinux、显示/GPU、相机、音频、加密、固件/remoteproc与启动等原阻塞继续保留。不宣称启动或硬件可用。无法读取实时额度，70%/90%仅为用户快照。本轮实现与保存略超约3分钟目标，不继续扩展，同步后暂停。
