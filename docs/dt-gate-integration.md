# 6.6设备树身份门禁接入

时间：2026-10-11T04:20:38.802484-07:00；基线b11efe4。目标国行wayne/SDM660、原始静态分区；4.19和6.6成果保留，不以jasmine/Miku UI为目标。

做了什么：读取上一轮报告/断点，确认两个实际workflow及共用构建函数，在ci_kernel_66_probe.main/build和ci_allocator_implementation.main开头调用既有audit_6_6_firstboot。新增--preflight只检查模式；allocator的--kernel走受保护的共用build。门禁拒绝码原样传播，当前clone-only DTS在依赖安装、源码fetch、构建、报告改写前退出2。

发生了什么：三项集成测试及两项既有门禁正反例通过，共五项。正例只模拟审计子进程成功且仅调用审计；负例检查三个Python入口尚未chdir或执行构建命令就停止。两个真实--preflight均返回2，没有执行构建或workflow dispatch。没有接入4.19打包入口。对现有package脚本的搜索未发现6.6专用打包调用，不能宣称所有打包路径都受保护。

| 实际集成点 | 调用链 |
| --- | --- |
| .github/workflows/kernel-6.6-probe.yml | tools/ci_kernel_66_probe.py main → preflight → 原有步骤；--build/build也再次检查 |
| .github/workflows/allocator-implementation.yml | tools/ci_allocator_implementation.py main → preflight；--kernel → 受保护build |
| 共用门禁 | require_board_preflight调用上一轮audit_6_6_firstboot，失败原样SystemExit |

当前上一轮审计CLI始终使用无真实绑定证据的材料；因此正常6.6构建会保持拒绝。没有伪造真实参考或硬编码放行开关；未来需先取得真实来源，再小范围扩展证据读取/核实，不能仅删include、改compatible或提供任意哈希声明来宣称适配。上一轮审计仅看直接jasmine include和声明/哈希关联，不递归验证完整DT语义，其局限仍保留。

| 待核实国行wayne板级证据 | 现状／下一证据 |
| --- | --- |
| 当前DTS来源 | 已知直接继承jasmine，仅改身份；真实板级绑定仍缺失 |
| DTB/DTBO及live DT | 缺真实当前国行来源与overlay对应关系；需哈希及完整include/板级对照 |
| 存储、PMIC/供电/时钟、中断及reserved-memory | 未声明实际差异，待真实DT/硬件日志对照；不猜地址或参数 |
| boot/header/ramdisk与静态GPT | 仅有旧参考/实验报告，缺当前真实boot参数和GPT容量/布局 |
| vendor ABI和firmware/remoteproc | 既有阻塞未解除；需当前vendor/固件加载链路及启动/AVC证据 |

直接执行（当前两个门禁均预期退出2）：

```sh
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
python3 tools/verify_6_6_gate_integration.py
```

第三条仅运行五项测试、两个preflight及保留检查，不编译。[断点](../research/dt-gate-integration-stage/checkpoint.json)保存结果与五项旧材料未变哈希；[时间戳记录](operations/dt-gate-integration-2026-10-11.md)保存原始日志；上一轮[差距报告](firstboot-6.6-gap-audit.md)仍保留原始历史结论，以本轮作为接入后的更新。

下一步先采集真实当前设备，以下只读命令尚未执行，无权限/不存在须原样记录：

```sh
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
adb shell 'cat /proc/cmdline; cat /proc/partitions; find /dev/block -type l' > wayne-static-boot-partition-evidence.txt
adb shell getprop > wayne-current-properties.txt
adb shell 'find /vendor /odm -type f; ls -l /sys/class/remoteproc' > wayne-vendor-firmware-inventory.txt
adb shell dmesg > wayne-current-boot-kernel.txt
adb shell logcat -b all -d > wayne-current-boot-logcat.txt
```

取得实际分区路径后在可读环境采集当前boot/DTBO/GPT，保存来源和SHA256并只读解析；不指定未知块设备、不刷写。门禁通过、静态检查或编译均不是真机启动验证。

未修改DTS、4.19入口、配置或已有实验包，未下载大源码/供体、长编译或打包。实时额度不可读取，77%/91%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
