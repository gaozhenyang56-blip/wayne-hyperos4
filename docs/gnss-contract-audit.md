# wayne GNSS/定位接口短审计

时间：2026-10-10T02:57:18.855015-07:00。基线36be91a。目标仅为国行小米6X（wayne/SDM660），原始静态分区；不是jasmine，与Miku UI无关。

做了什么：核验现有非Miku wayne比较样本提取文件SHA256，检查定位相关文本，补齐HAL/配置、实际传输/驱动绑定与固件交付证据门禁。缺任一类别拒绝判断，证据标志必须为显式布尔值。文件名仅用于候选材料检查，不验证HAL版本、配置语义或固件加载；自定义命名必须取得真实清单后复核。

发生了什么：三项最小正反例通过，真实清单按预期返回2。完整模拟清单只开放材料门禁，契约/定位/硬件标志仍为false；属性、目录及服务声明不能代替HAL或链路绑定，字符串证据标志被拒绝。缺文件仅指没有提取，不代表完整vendor缺失或硬件不可用。没有发现材料齐全、可证明的具体接口矛盾。

| 现有证据 | 边界 |
| --- | --- |
| init.qcom.rc第299至305行创建/data/vendor/location及/dev/socket/location目录，第479至482行声明/system/vendor/bin/loc_launcher、late_start、gps用户/组 | 仅为该样本用户空间路径和服务期望；服务二进制/配置未提取，不证明串口、QMI服务、RPMSG或节点要求 |
| 本次选定build.prop没有直接GNSS/GPS属性证据 | 不能推出完整vendor或当前用户没有关键属性，不能填入猜测值 |
| 4.19历史嵌入配置QRTR/RPMSG/QCOM_QMI_HELPERS=y | 不是实际生成.config或用户当前基线，不证明定位专用QMI服务、设备绑定或链路可用 |
| 6.6保存报告modules_built=false，早期模块/固件加载未集成 | 不排除内建或用户空间路径；实际GNSS配置、交付与传输未知 |

证据：[audit.json](../research/gnss-contract-stage/audit.json)保存文本行号/哈希；[checkpoint.json](../research/gnss-contract-stage/checkpoint.json)保存测试、历史配置行及五项既有文件不变的哈希。原始测试见[时间戳记录](operations/gnss-contract-2026-10-10.md)。复现`python3 tools/verify_gnss_stage.py`；单独`python3 tools/audit_gnss_contract.py`对目前材料预期退出2。原4.19、6.6及已有实验包均保留，未改配置或DTB、未大下载、未重编内核、未生成刷机包。

下一步只先采集真实当前wayne证据。以下只读命令未执行，不存在、工具缺失或无权限应保留原始错误：

```sh
adb shell getprop > wayne-gnss-properties.txt
adb shell 'ls -lZ /dev; ls -l /sys/class/tty /sys/bus/rpmsg/devices /sys/class/remoteproc' > wayne-gnss-node-inventory.txt
adb shell cat /proc/modules > wayne-loaded-modules.txt
adb shell 'zcat /proc/config.gz' > wayne-current-kernel-config.txt
adb shell 'find /vendor /odm /lib/modules -type f' > wayne-gnss-vendor-inventory.txt
adb shell lshal > wayne-gnss-hal-services.txt
adb shell dumpsys location > wayne-location-service.txt
adb shell logcat -b all -d > wayne-gnss-logcat.txt
adb shell dmesg > wayne-gnss-dmesg.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

根据真实清单再pull GNSS HAL、定位服务/库、配置、init/VINTF、32/64位传递依赖、固件交付和模块/builtin清单并保存SHA256；模块列表不代表内建驱动清单。只在日志、配置和实际DTB证明绑定后进一步检查对应串口/QMI/RPMSG或共享无线接口、DAC/SELinux和相关AVC。不把目录直接当设备节点，不猜芯片、端口、服务编号、固件或HAL版本，不打开串口、不启动定位或写remoteproc状态。

SELinux、显示/GPU、音频、相机、无线、定位、加密及启动仍待核实。无真机测试，不宣称定位、启动或硬件可用。实时额度不可读取，用户77%/34%只是快照，不声称精确控制。本轮同步后暂停。
