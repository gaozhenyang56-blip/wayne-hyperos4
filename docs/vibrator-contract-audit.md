# 国行wayne振动/触觉材料短审计

时间：2026-10-11T02:49:28.573346-07:00；基线4f45447。目标国行小米6X（wayne/SDM660）、原始静态分区；jasmine、动态分区或Miku UI不作为基线。

做了什么：检查工作区及执行断点，核验现有非Miku比较样本文件SHA256，新增HAL、明确实际后端、国行设备/驱动/DTB/节点及服务权限/SELinux材料门禁。后端未知或材料缺失即拒绝判断，声明必须为显式布尔值。timed_output、LED class、input force-feedback及厂商路径作为替代候选，不强制所有接口同时存在。文件名和人工声明只开放材料复核，不验证HAL版本、参数或兼容性。

发生了什么：两项正反例通过，实际清单按预期退出2；正例分别模拟四种已明确后端，只通过材料门禁，振动/效果/硬件及契约验证始终为false。未知后端、缺HAL/实际绑定、非法后端名或字符串证据标志被拒绝。

现有参考清单没有Vibrator HAL、专用服务或策略；etc/ueventd.rc未提取。选定build.prop/init.qcom.rc的vibrator/haptic/timed_output/force-feedback关键词无匹配。未提取不代表完整vendor/system中没有实现或硬件不支持。历史4.19嵌入配置有ANDROID_2026-10-11T02:49:28.573346-07:00D_OUTPUT、LEDS_CLASS等声明，INPUT_FF_MEMLESS未设置，但provenance明确不是实际生成.config或用户当前基线；这些声明不能选定真实驱动，FF_MEMLESS未设置也不能一概否定force-feedback。6.6报告没有已审计的Vibrator后端/服务策略绑定。没有材料齐全、可证明的具体接口矛盾。

[证据](../research/vibrator-contract-stage/audit.json)保存清单与文本哈希；[断点](../research/vibrator-contract-stage/checkpoint.json)保存测试、历史配置行及五项既有材料未变哈希。[时间戳记录](operations/vibrator-contract-2026-10-11.md)保存原始输出。复现`python3 tools/verify_vibrator_stage.py`；单独`python3 tools/audit_vibrator_contract.py`对当前材料预期退出2。

下一步先采集真实当前国行wayne证据。以下只读命令未执行，节点不存在、工具缺失或权限不足必须原样保存错误，日志先留本地：

```sh
adb shell getprop > wayne-vibrator-properties.txt
adb shell 'ls -lZ /dev/input; ls -l /sys/class/timed_output /sys/class/leds /sys/class/input' > wayne-vibrator-node-inventory.txt
adb shell 'cat /proc/bus/input/devices; getevent -lp' > wayne-vibrator-input-capabilities.txt
adb shell 'find /vendor /odm /system/lib/hw /system/lib64/hw /lib/modules -type f' > wayne-vibrator-vendor-inventory.txt
adb shell lshal > wayne-vibrator-hal-services.txt
adb shell dumpsys -l > wayne-vibrator-service-inventory.txt
adb shell dumpsys vibrator > wayne-vibrator-service.txt
adb shell ps -AZ > wayne-service-domains.txt
adb shell 'cat /proc/modules; zcat /proc/config.gz' > wayne-vibrator-kernel-inventory.txt
adb shell logcat -b all -d > wayne-vibrator-logcat.txt
adb shell dmesg > wayne-vibrator-boot-kernel.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

getevent仅列设备能力，不读取实时事件或上传触觉效果。依据真实服务清单（新版本可能使用不同service名称，先枚举，不猜版本）再pull HAL或旧库集成、init/VINTF、ueventd/SELinux、32/64位依赖和驱动交付描述并保存SHA256。用实际DTB、driver和日志确定后端，再检查实际枚举节点的DAC/标签及AVC；目录清单和通用LED/input能力自身不证明振动绑定。不猜节点、强度、效果、供电或电压，不写timed_output/LED/input/sysfs，不用cmd vibrator/service call或加载FF效果，不改permissive或驱动参数，不发起振动调用测试。

4.19、6.6独立实验及既有实验包保留；未下载大供体、重编内核或生成刷机包。真实HAL/后端、DTB、节点权限、SELinux及启动/既有调用日志仍待核实，其余硬件/启动问题保留。无真机测试，不宣称振动、触觉效果、启动或硬件可用。实时额度不可读取，98%/94%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
