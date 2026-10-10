# wayne Sensors接口短审计

时间：2026-10-10T03:12:27.410520-07:00。基线a8b13e8。目标国行小米6X（wayne/SDM660），原始静态分区；jasmine、Miku UI不作为目标基线。

做了什么：校验现有非Miku比较样本文件哈希，核对传感器属性/init请求，补齐HAL/配置、实际接口绑定及校准交付证据门禁。缺任一类别拒绝判断，证据标志须为显式布尔值。校准交付证据可以是经核实“不要求该文件”的结论，不强制猜测文件或格式；文件名候选分类不能代替HAL/配置语义验证，其他命名需真实清单复核。

发生了什么：三项正反例通过，真实清单按预期退出2；模拟完整证据只开放材料门禁，不证明硬件或契约兼容。init请求/目录不能代替HAL或实际绑定，字符串标志被拒绝。未提取不等于完整vendor缺文件或设备不支持，没有材料齐全、可证明的具体接口矛盾。

现有参考init确实请求/sys/kernel/boot_slpi/boot，修改/persist/sensors和/mnt/vendor/persist/sensors下registry、sns.reg等路径权限，列出多个/sys/class/sensors下enable/poll_delay请求，并声明/vendor/bin/sensors.qti（core、system用户/组）。这些是样本文本期望，不证明节点存在、实际传感器型号或必需校准格式，未套用到目标设备。参考build.prop有ro.vendor.sensors.dev_ori=true等属性，不能证明该功能由6.6提供。

4.19历史嵌入配置有INPUT/INPUT_EVDEV等通用声明，但不是实际生成.config或用户当前ROM基线，不证明Sensors HAL采用input/IIO或中枢接口。6.6保存报告的modules_built=false及早期模块/固件加载未集成，不排除内建或用户空间路径；实际驱动、DTB、接口和校准要求未知。

[审计证据](../research/sensors-contract-stage/audit.json)保留文本行号/哈希；[断点](../research/sensors-contract-stage/checkpoint.json)保留三项测试、拒绝退出码、历史配置行及五项既有文件未变哈希。原始输出见[时间戳记录](operations/sensors-contract-2026-10-10.md)。复现`python3 tools/verify_sensors_stage.py`；单独`python3 tools/audit_sensors_contract.py`对当前材料预期退出2。

下一步先采集真实当前wayne证据。以下只读命令未执行，节点不存在、无权限、命令缺失须原样保留错误：

```sh
adb shell getprop > wayne-sensors-properties.txt
adb shell 'ls -lZ /dev/input /dev/iio*; ls -l /sys/class/input /sys/bus/iio/devices /sys/class/sensors' > wayne-sensors-node-inventory.txt
adb shell cat /proc/bus/input/devices > wayne-input-devices.txt
adb shell 'find /vendor /odm /lib/modules -type f' > wayne-sensors-vendor-inventory.txt
adb shell 'ls -lZ /persist/sensors /mnt/vendor/persist/sensors' > wayne-sensors-calibration-inventory.txt
adb shell cat /proc/modules > wayne-loaded-modules.txt
adb shell 'zcat /proc/config.gz' > wayne-current-kernel-config.txt
adb shell lshal > wayne-sensors-hal-services.txt
adb shell dumpsys sensorservice > wayne-sensors-service.txt
adb shell logcat -b all -d > wayne-sensors-logcat.txt
adb shell dmesg > wayne-sensors-dmesg.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

依据真实清单再pull HAL、32/64位传递依赖、配置、init/VINTF、模块/builtin与固件交付材料并保存SHA256；结合实际DTB、driver绑定及AVC确认IIO/input/中枢或其他接口。校准先取路径/权限/来源证据，不生成、覆盖或公开设备校准内容。不猜型号、编号、通道或格式，不写enable/poll_delay，不读取事件流或启动测量。

4.19、6.6独立实验及现有实验包保留，没有大下载、完整内核重编译或新刷机包。SELinux及显示/GPU、音频、相机、无线、定位、传感器、加密和启动仍待核实；无真机测试，不宣称可用。实时额度无法读取，70%/33%仅为用户快照，不声称精确控制。本轮同步后暂停。
