# wayne Wi-Fi接口短审计

时间：2026-10-10T00:55:36.776781-07:00。基线4e2c24b。目标国行小米6X（wayne/SDM660），原始静态分区；不以jasmine或Miku UI为目标基线。

做了什么：核验现有非Miku wayne比较样本提取文件SHA256，检查build.prop/init.qcom.rc的无线相关行，补齐材料完整性门禁。缺少候选Wi-Fi HAL、配置、真实驱动交付/config证据或固件清单/加载要求时拒绝契约判断。模块交付额外要求模块清单，内建交付不要求模块清单；未知保持未知。证据标志必须为显式布尔值。

发生了什么：三项最小测试通过，实际材料按预期退出2。正例只是模拟已声明证据齐备、开放材料门禁；任何结果均不宣称接口兼容或硬件可用。文件名分类和人工证据声明不等于ELF、配置、固件加载、nl80211私有命令或运行语义验证；自定义命名须取得真实清单后复核。缺文件仅指未提取，不是完整vendor或硬件缺失。

| 参考材料 | 可证明的内容及边界 |
| --- | --- |
| init.qcom.rc第147行设置wifi.interface wlan0 | 仅为该样本接口名期望；不假定用户当前接口名或6.6会创建同名接口 |
| 同一init第283行请求/persist/WCNSS_qcom_wlan_nv.bin权限 | 路径来自真实文本，不是猜测；未提取对应文件，不能证明芯片、文件存在、强制固件要求或当前用户需求 |
| init声明cnss-daemon，路径/system/vendor/bin/cnss-daemon，并请求/sys/kernel/shutdown_wlan/shutdown写入 | 仅为参考服务/内核接口期望，二进制与真实节点未取证；不能据此推断具体驱动、HAL版本或加载成功 |
| init创建/data/vendor/wifi系列目录及/dev/socket/wifihal；build.prop有iwlan电话相关属性 | 目录/权限期望不能替代HAL或无线接口证据；iwlan属性不作为Wi-Fi驱动验证 |
| 4.19历史嵌入配置CFG80211=y、WLAN=y、MAC80211未设置 | 来源明确不是实际生成.config或用户当前基线；不能推出具体fullmac/softmac实现或运行能力。mac80211不是所有无线驱动的共同必要条件，不能据此断言无Wi-Fi |
| 6.6保存报告modules_built=false，早期模块/固件加载未集成 | 不能推出内建驱动不存在；尚无经审计的实际无线配置、驱动交付或固件要求，不能放行接口契约判断 |

未发现材料齐全且可证明的具体接口矛盾。本轮修复的是材料不足时的拒绝检查，没有更改属性、接口名、驱动、DTB、固件、SELinux或启动配置。

证据：[audit.json](../research/wifi-contract-stage/audit.json)保存参考文本行号/哈希；[checkpoint.json](../research/wifi-contract-stage/checkpoint.json)保存测试、实际拒绝退出码、历史配置和既有材料未变的哈希。原始测试见[时间戳记录](operations/wifi-contract-2026-10-10.md)。复现`python3 tools/verify_wifi_stage.py`，只做离线审计；单独`python3 tools/audit_wifi_contract.py`对当前样本预期返回2。

下一步先采集真实当前wayne材料。以下只读命令未执行；不存在、无权限或工具缺失都保留原始错误，不自动填值：

```sh
adb shell getprop > wayne-wifi-properties.txt
adb shell 'ip link; iw dev; cat /proc/net/wireless' > wayne-wireless-interfaces.txt
adb shell 'ls -l /sys/class/net /sys/class/ieee80211' > wayne-wireless-sysfs.txt
adb shell cat /proc/modules > wayne-loaded-modules.txt
adb shell 'zcat /proc/config.gz' > wayne-current-kernel-config.txt
adb shell 'find /vendor /odm /lib/modules -type f' > wayne-vendor-module-firmware-inventory.txt
adb shell lshal > wayne-wifi-hal-services.txt
adb shell dumpsys wifi > wayne-wifi-service.txt
adb shell logcat -b all -d > wayne-wifi-logcat.txt
adb shell dmesg > wayne-wifi-dmesg.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

根据真实清单再pull Wi-Fi HAL、supplicant/hostapd服务及配置、VINTF/init、32/64位传递依赖、模块及modules.dep/builtin（如存在）、固件清单并计算SHA256。加载模块列表不是内建驱动清单；须用实际构建.config与builtin/驱动绑定证据交叉核对。再依据实际枚举的接口/phy查驱动绑定、cfg80211/nl80211及vendor命令要求、固件请求失败和SELinux/AVC。不猜芯片、模块名、接口名、固件文件或HAL版本；不执行modprobe、insmod、ip link set、扫描、连接或热点启动。材料中的参考路径不应用到用户设备。

4.19方案、6.6实验及既有实验包保留；无大下载、完整内核重编译或新刷机包。SELinux、显示/GPU、音频、相机、加密、Wi-Fi/热点及启动仍待核实，无真机测试，不宣称硬件可用。本轮保存同步后暂停。实时额度无法读取，用户96%/37%只是快照，不假称精确控制。
