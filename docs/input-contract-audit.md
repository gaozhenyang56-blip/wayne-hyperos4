# 国行wayne触摸/按键输入材料短审计

时间：2026-10-11T01:25:34.204498-07:00；基线c077544。目标国行小米6X（wayne/SDM660）、原始静态分区；不以jasmine、动态分区或Miku UI为基线。

做了什么：检查工作区与断点，核验现有非Miku比较样本提取文件SHA256，新增布局/通用回退、实际设备身份、event到配置/DTB绑定和DAC/SELinux/固件要求材料门禁。缺证据拒绝判断，声明必须为显式布尔值。文件名候选与人工声明只是材料门禁，不能证明布局语义、触摸型号、坐标、手势或实际兼容。

发生了什么：两项正反例通过，真实清单按预期退出2。模拟已确认的system通用keylayout回退可通过材料门禁，不一概强制厂商IDC/KCM；通用布局或INPUT_EVDEV选项本身不能证明真实绑定，字符串标志被拒绝。硬件/触摸/按键/手势/契约验证始终为false。

已有参考清单未提取keylayout、IDC/KCM或输入专用配置，etc/ueventd.rc也记录为未提取；在选定build.prop/init.qcom.rc的触摸、输入节点和布局关键词检查没有匹配行。这不代表完整vendor、system/product/odm没有配置或硬件不支持。4.19历史嵌入配置INPUT/EVDEV/GPIO按键声明不是实际生成.config或用户当前基线，多种触摸驱动选项更不能确定真实IC。6.6保存报告没有已审计的触摸/GPIO/event/固件到Android配置绑定。没有材料齐全、可证明的具体接口矛盾。

[证据](../research/input-contract-stage/audit.json)保存清单与文本哈希；[断点](../research/input-contract-stage/checkpoint.json)保存测试、历史通用配置行和五项既有材料未变哈希；[时间戳记录](operations/input-contract-2026-10-11.md)保存原始测试。复现`python3 tools/verify_input_stage.py`；单独`python3 tools/audit_input_contract.py`对目前材料预期退出2。

下一步先采集真实当前国行wayne证据。以下只读命令未执行，无权限、无节点或无工具须原样保存错误，日志先留本地：

```sh
adb shell getprop > wayne-input-properties.txt
adb shell 'cat /proc/bus/input/devices; ls -lZ /dev/input; ls -l /sys/class/input' > wayne-input-node-inventory.txt
adb shell getevent -lp > wayne-input-capability-inventory.txt
adb shell dumpsys input > wayne-inputreader-bindings.txt
adb shell 'find /system/usr /system_ext/usr /vendor/usr /odm/usr /product/usr -type f' > wayne-input-config-inventory.txt
adb shell 'find /vendor /odm /lib/modules -type f' > wayne-input-firmware-driver-inventory.txt
adb shell 'cat /proc/modules; zcat /proc/config.gz' > wayne-input-kernel-inventory.txt
adb shell ps -AZ > wayne-input-service-domains.txt
adb shell logcat -b all -d > wayne-input-logcat.txt
adb shell dmesg > wayne-input-boot-kernel.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

getevent仅列已有设备能力，不采集实时触摸/按键事件。按真实InputReader输出和设备name/id绑定找到实际选用的KL/KCM/IDC或回退，再pull相关文件、ueventd/SELinux、驱动/固件交付描述并保存SHA256；结合真实国行来源、DTB和driver绑定确认IC、GPIO按键及固件加载要求。不从文件名或配置选项猜IC，不一概要求厂商IDC/KCM；不猜event编号、坐标、手势或键码，不写sysfs、校准/灵敏度、固件更新接口，不用input命令注入事件或执行触摸测试。

4.19、6.6独立实验和既有实验包保留，未下载大供体、重编内核或生成刷机包。真实身份、固件、DTB、节点策略及启动/触摸/AVC日志仍待核实，其余硬件/启动问题保留。无真机测试，不宣称触摸、按键、手势、启动或硬件可用。实时额度不可读取，68%/95%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
