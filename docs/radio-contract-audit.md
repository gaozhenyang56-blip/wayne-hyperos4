# 国行wayne Radio/基带材料短审计

时间：2026-10-10T21:57:50.986210-07:00；基线1858697。目标国行小米6X（wayne/SDM660）、原始静态分区；不以jasmine、动态分区或Miku UI为基线。

做了什么：复核工作区和执行断点，校验已保存非Miku wayne比较样本文件SHA256，新增Radio/RIL材料完整性门禁。缺少候选HAL/RIL二进制、RIL配置、真实当前国行vendor来源、modem交付/实际分区清单或接口绑定证据时拒绝判断。所有证据标志必须是显式布尔值。文件名候选及人工证据声明只开放材料复核，不验证HAL版本、固件语义或运行兼容；其他命名需真实清单复核。

发生了什么：两项正反例通过，实际样本按预期退出2。模拟完整证据不宣称通话、短信、数据、VoLTE或硬件可用；参考vendor即使文件齐全，也不能代替当前国行来源。未提取不等于完整vendor缺文件或设备不支持。没有材料齐全、可证明的具体接口矛盾。

| 已保存参考材料 | 可证明内容及边界 |
| --- | --- |
| build.prop声明persist.radio.multisim.config=dsds及多项persist.vendor.radio属性 | 仅是参考属性期望，不能证明SIM数量、基带版本、通话/数据/VoLTE能力或用户当前属性 |
| init创建/dev/socket/qmux_radio、/data/vendor/radio，复制/vendor/radio/qcril_database/qcril.db | 路径来自真实文本；数据库、RIL二进制和实际节点未提取，目录请求不能当作协议/驱动绑定证据 |
| init声明/vendor/bin/qrtr-ns并请求pil_msa的modem_auth_timeout参数 | 不能证明QMI服务、remoteproc ABI、modem认证或固件加载满足6.6；未添加参数或节点别名 |
| 同一init出现radio_iris_transport/fmsmd_set | 属于文本中的FM相关请求，不作为蜂窝Radio接口证明 |
| 历史4.19嵌入配置有QRTR等通用声明 | provenance已明确不是实际生成.config或用户当前基线，不证明真实modem绑定 |
| 6.6保存报告modules_built=false，早期模块/固件加载未集成 | 不排除内建驱动；目前没有已审计的rmnet/IPA/QRTR/remoteproc或其他实际Radio绑定 |

[证据](../research/radio-contract-stage/audit.json)保存参考行号/哈希；[断点](../research/radio-contract-stage/checkpoint.json)保存测试、历史配置行与五项既有文件未变哈希；[时间戳记录](operations/radio-contract-2026-10-10.md)保存原始测试。复现`python3 tools/verify_radio_stage.py`；单独`python3 tools/audit_radio_contract.py`对当前材料预期退出2。

下一步先采集真实当前国行wayne证据。以下只读命令未执行，权限不足、命令缺失或节点不存在须原样保留错误，日志先保留本地：

```sh
adb shell getprop ro.product.device
adb shell getprop gsm.version.baseband
adb shell getprop > wayne-radio-properties.txt
adb shell 'find /dev/block -type l' > wayne-actual-partition-links.txt
adb shell 'ls -lZ /dev; ls -l /sys/class/net /sys/class/remoteproc /sys/bus/rpmsg/devices' > wayne-radio-node-inventory.txt
adb shell 'ip link; cat /proc/modules; zcat /proc/config.gz' > wayne-radio-kernel-inventory.txt
adb shell 'find /vendor /odm /lib/modules -type f' > wayne-radio-vendor-delivery-inventory.txt
adb shell lshal > wayne-radio-hal-services.txt
adb shell dumpsys -l > wayne-service-inventory.txt
adb shell logcat -b radio -d > wayne-radio-logcat.txt
adb shell dmesg > wayne-radio-boot-kernel.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

属性字符串本身不证明国行硬件身份或固件认证；还需当前系统/vendor/boot来源和实际分区表证据，不凭属性猜基带版本。按真实清单再pull HAL/RIL、32/64位传递依赖、配置、init/VINTF和modem交付描述并计算SHA256，依据实际分区与DTB明确固件来源/加载链路。节点目录不证明rmnet、IPA、QRTR或remoteproc均为必要条件，需结合真实配置、驱动绑定、启动日志与SELinux/AVC。不得猜服务编号、分区容量、固件文件或HAL版本；不读取/改写EFS校准分区、不刷modem、不发起拨号、短信、数据连接或重启基带。

4.19、6.6独立实验和既有实验包保留；未下载大供体、重编内核或生成刷机包。SELinux、固件交付、DTB、接口绑定及各硬件/启动问题仍未验证。无真机测试，不宣称蜂窝功能或硬件可用。实时额度无法读取，93%/99%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
