# wayne 蓝牙接口短审计

时间：2026-10-10T01:31:43.507910-07:00。基线471f71d。目标国行小米6X（wayne/SDM660），原始静态分区；不以jasmine或Miku UI为目标基线。

做了什么：校验现有非Miku wayne比较样本提取文件SHA256，核对蓝牙属性及init权限请求，补齐材料完整性门禁。缺少候选HAL/vendor库、配置、实际传输/驱动绑定证据或固件交付要求时拒绝判断。文件名和布尔证据声明仅作材料门禁，不验证HAL版本、ELF/配置语义或运行兼容；自定义命名须取得真实清单后复核。

发生了什么：三项最小测试通过，实际清单按预期退出2。模拟完整证据只开放材料检查，本阶段蓝牙/通话/硬件及契约验证标志仍为false。属性、UART/rfkill权限请求不能代替HAL或传输绑定；字符串证据标志被拒绝。文件缺失仅指没有提取，不代表完整vendor或硬件缺失。本轮未发现材料齐全、可以证明的具体接口矛盾。

| 参考材料 | 可证明内容及边界 |
| --- | --- |
| build.prop第105行vendor.qcom.bluetooth.soc=cherokee | 仅为该样本属性值，不据此确认用户当前芯片或HAL版本 |
| init对/dev/ttyHS0、/dev/ttyHS2、rfkill0、hci_uart/hci_smd参数、bluetooth_power及/proc/bluetooth/sleep/proto请求权限 | 路径确实来自参考文本，未猜测；多种通用请求不能选定实际UART/HCI编号、共享无线链路或强制需求，也不能证明节点存在 |
| init创建/data/vendor/bluetooth和持久化相关目录 | 不能替代HAL、固件交付和驱动绑定证据 |
| 4.19历史嵌入配置BT=y、BT_HCIUART未设置、MSM_BT_POWER=y | provenance明确不是实际生成.config或用户当前基线；与init请求之间只能记录待核实点，不能宣称运行冲突或必须启用HCIUART |
| 6.6保存报告modules_built=false，早期模块/固件加载未集成 | 不排除内建驱动或用户空间HCI路径；实际蓝牙配置、绑定与固件要求仍未知 |

证据：[audit.json](../research/bluetooth-contract-stage/audit.json)保存文本行号/哈希；[checkpoint.json](../research/bluetooth-contract-stage/checkpoint.json)保存测试、历史配置行与既有材料未变哈希。原始测试见[时间戳记录](operations/bluetooth-contract-2026-10-10.md)。复现：`python3 tools/verify_bluetooth_stage.py`；单独`python3 tools/audit_bluetooth_contract.py`对当前样本预期退出2。

下一步先取真实当前wayne材料。以下只读命令未执行，无权限、缺工具或节点不存在均保留原始错误，不填推测值：

```sh
adb shell getprop > wayne-bluetooth-properties.txt
adb shell 'ls -l /sys/class/bluetooth /sys/class/rfkill /sys/class/tty' > wayne-bluetooth-sysfs.txt
adb shell 'ls -lZ /dev' > wayne-device-nodes.txt
adb shell cat /proc/modules > wayne-loaded-modules.txt
adb shell 'zcat /proc/config.gz' > wayne-current-kernel-config.txt
adb shell 'find /vendor /odm /lib/modules -type f' > wayne-bluetooth-vendor-inventory.txt
adb shell lshal > wayne-bluetooth-hal-services.txt
adb shell dumpsys bluetooth_manager > wayne-bluetooth-service.txt
adb shell logcat -b all -d > wayne-bluetooth-logcat.txt
adb shell dmesg > wayne-bluetooth-dmesg.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

依据真实清单再pull蓝牙HAL、vendor库、32/64位传递依赖、配置、init/VINTF、实际firmware及module/builtin交付清单并计算SHA256；模块列表不是内建驱动清单。按实际枚举路径只读检查设备driver绑定、rfkill的type/name及HCI/UART或共享传输日志，核对真实DTB、电源/时钟、私有接口与SELinux/DAC/AVC。不得把参考端口套到用户设备，不猜固件文件，不执行rfkill写入、hciattach、btattach、modprobe、配对、通话或音频测试。

4.19、6.6独立实验和原有实验包保留，没有大下载、完整内核重编译或新刷机包。SELinux、显示/GPU、音频、相机、加密、Wi-Fi、蓝牙/通话和启动仍待核实，无真机测试，不宣称硬件可用。实时额度无法读取，用户88%/35%仅为快照，不假称精确控制。本轮同步后暂停。
