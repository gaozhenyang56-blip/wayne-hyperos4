# 国行wayne USB/充电材料短审计

时间：2026-10-11T00:39:20.160027-07:00；基线b936d04。目标国行小米6X（wayne/SDM660）、原始静态分区；不以jasmine、动态分区或Miku UI为基线。

做了什么：检查工作区与执行断点，核验已保存非Miku比较样本文件SHA256，新增直接USB init导入的材料闭包检查。已观察到的导入缺材料，或含动态/通配符等不能确定的路径，立即拒绝判断；不猜测运行时展开。检查仅限直接USB导入，不能证明递归导入齐备、HAL/驱动兼容或硬件可用。

发生了什么：两项正反例通过，实际参考样本因两个导入均未提取按预期退出2。完整模拟导入只通过闭包检查，充电/USB数据/ADB/OTG/硬件及契约验证始终为false。未提取不等于完整vendor没有文件，没有发现材料齐全、可证明的具体接口矛盾。

| 参考证据 | 内容及边界 |
| --- | --- |
| init.qcom.rc第28至29行导入/vendor/etc/init/hw/init.qcom.usb.rc及/vendor/etc/init/hw/init.msm.usb.configfs.rc | 两条路径来自真实文本，不是猜测，当前清单无这两份材料；不能从文件名推断UDC或configfs运行配置 |
| 第158行请求/sys/devices/platform/msm_hsusb/gadget/usb_state权限 | 仅是参考节点请求，不能证明实际UDC、role/extcon绑定或6.6存在该节点 |
| 第530行声明/system/bin/charger，第535行seclabel u:r:charger:s0 | 不证明健康HAL版本、电池/充电配置、SELinux完整策略或充电协议 |
| build.prop的persist.sys.usb.config=none，init的on charger设置mass_storage | 不同状态的请求，材料不足时不能当作配置矛盾或更改为ADB；USB音频offload属性也不证明数据/OTG能力 |
| 历史4.19来源与6.6已保存报告 | 4.19嵌入配置不是实际生成.config或用户当前基线；6.6没有已审计的当前USB/健康HAL到UDC、power_supply、extcon/role节点映射 |

[证据](../research/usb-charging-stage/audit.json)保存精确导入路径、行号及文本哈希；[断点](../research/usb-charging-stage/checkpoint.json)保存测试、拒绝退出码和五项既有文件未变哈希。[时间戳记录](operations/usb-charging-2026-10-11.md)保存原始测试。复现`python3 tools/verify_usb_charging_stage.py`；单独`python3 tools/audit_usb_charging_contract.py`对当前材料预期退出2。

下一步先采集真实当前国行wayne证据。以下只读命令未执行，节点不存在、权限不足或命令缺失须原样保存错误，日志先留本地：

```sh
adb shell getprop > wayne-usb-charging-properties.txt
adb shell 'mount; ls -lZ /sys/class/udc /config/usb_gadget /sys/kernel/config/usb_gadget /sys/class/power_supply /sys/class/extcon /sys/class/usb_role /sys/class/typec' > wayne-usb-charging-node-inventory.txt
adb shell 'find /vendor /odm -type f' > wayne-usb-charging-vendor-inventory.txt
adb shell lshal > wayne-usb-health-hal-services.txt
adb shell ps -AZ > wayne-service-domains.txt
adb shell dumpsys usb > wayne-usb-service.txt
adb shell dumpsys battery > wayne-battery-service.txt
adb shell logcat -b all -d > wayne-usb-charging-logcat.txt
adb shell dmesg > wayne-usb-charging-boot-kernel.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

adb采集命令仅供已有可用连接时执行，不证明本项目ADB能用。依据真实清单再pull当前USB/健康HAL、充电配置、完整相关init及其递归导入、VINTF/ueventd/SELinux、32/64位依赖，保存SHA256和来源；对应实际DTB与driver绑定核对UDC/configfs、power_supply、extcon或role控制的实际需求（不要求所有接口同时存在）。只按已枚举路径读类型/绑定与日志，不猜节点名、协议、功率或阈值，不写UDC/functions/sysfs、不切USB模式、不改充电电流、不控制插线/OTG状态或执行电池模拟命令。

4.19、6.6独立实验和既有实验包保留；未下载大供体、重编内核或生成刷机包。SELinux、当前HAL/配置、DTB、节点及启动/插线日志仍缺证据，各硬件/启动问题仍保留。无真机测试，不宣称充电、数据、ADB、OTG、启动或硬件验证。实时额度不可读取，75%/96%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
