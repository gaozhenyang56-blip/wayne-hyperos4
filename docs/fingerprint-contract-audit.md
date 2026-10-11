# 国行wayne指纹HAL—TEE/内核材料短审计

时间：2026-10-10T23:32:55.339264-07:00；基线4efaf4c。目标国行小米6X（wayne/SDM660）、原始静态分区；jasmine、动态分区和Miku UI不作为目标基线。

做了什么：核查工作区与断点，校验现有非Miku wayne比较样本文件SHA256，新增HAL/服务、真实设备和传感器身份、节点/权限/SELinux绑定及TEE交付材料门禁。缺任一类别拒绝判断，证据声明必须为显式布尔值。候选文件名和人工声明只开放材料复核，不能证明HAL版本、TEE协议或实际兼容；自定义服务/文件命名须真实清单人工复核。

发生了什么：三项正反例通过，实际清单按预期退出2。构建fingerprint被明确排除为指纹硬件证据；模拟完整材料只开放门禁，录入/识别/解锁/硬件及契约验证始终为false。参考包缺已选材料不能推出完整vendor没有文件或硬件不支持，没有材料足够证明的具体接口矛盾。

| 材料 | 可证明内容与边界 |
| --- | --- |
| build.prop第15行ro.vendor.build.fingerprint | 构建标识，不是指纹传感器型号、HAL或绑定证据；已从相关文本证据排除 |
| init.qcom.rc第237至238行创建/data/vendor/qtee | 仅为通用QTEEConnector目录请求，不能证明指纹TEE协议、可信应用或设备节点要求 |
| 选定清单无指纹HAL、指纹服务或策略，etc/ueventd.rc记录为未提取 | 不知道实际服务域、节点DAC/SELinux标签、IRQ/SPI/input/电源链路；不猜厂商/型号或新增allow |
| 历史4.19嵌入配置QSEECOM、SPI、INPUT_EVDEV=y | provenance明确不是实际生成.config或用户当前基线；不能证明指纹厂商协议或实际绑定 |
| 6.6已有报告没有已审计的指纹/TEE绑定 | 通用配置或模块未构建不能证明兼容或不兼容；实际DTB、节点权限和TEE交付未知 |

[证据](../research/fingerprint-contract-stage/audit.json)保存来源哈希、相关文本和排除的构建标识行；[断点](../research/fingerprint-contract-stage/checkpoint.json)保存测试、历史配置行及五项既有材料未变哈希。[时间戳记录](operations/fingerprint-contract-2026-10-10.md)保存原始执行结果。复现`python3 tools/verify_fingerprint_stage.py`；单独`python3 tools/audit_fingerprint_contract.py`对目前材料预期退出2。

下一步先采集真实当前国行wayne证据。以下只读命令未执行，无权限、无节点或无工具必须保留原始错误，日志先存本地：

```sh
adb shell getprop > wayne-fingerprint-properties.txt
adb shell 'ls -lZ /dev /dev/input; ls -l /sys/bus/spi/devices /sys/class/input' > wayne-fingerprint-node-inventory.txt
adb shell 'cat /proc/interrupts; cat /proc/bus/input/devices' > wayne-fingerprint-irq-input-inventory.txt
adb shell ps -AZ > wayne-service-domains.txt
adb shell 'find /vendor /odm /lib/modules -type f' > wayne-fingerprint-vendor-delivery-inventory.txt
adb shell 'cat /proc/modules; zcat /proc/config.gz' > wayne-fingerprint-kernel-inventory.txt
adb shell lshal > wayne-fingerprint-hal-services.txt
adb shell dumpsys fingerprint > wayne-fingerprint-service.txt
adb shell dumpsys biometric > wayne-biometric-service.txt
adb shell logcat -b all -d > wayne-fingerprint-logcat.txt
adb shell dmesg > wayne-fingerprint-boot-kernel.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

依据真实清单再pull HAL、服务/init/VINTF、32/64位传递依赖、ueventd及SELinux策略、TEE交付描述并保存SHA256；用真实国行来源、DTB/driver绑定/启动日志明确传感器身份及IRQ、SPI、input、电源接口实际需求（不存在的接口需证据说明，不一概要求通用input）。再核对真实服务域、节点DAC/标签和AVC，不能凭文件名猜可信应用、协议或固件文件。不读取/修改指纹模板或TEE密钥、不打开传感器接口、不写电源/IRQ/SPI节点、不切permissive、不录入/识别/解锁测试。

4.19、6.6独立实验及既有实验包保留，未下载大供体、重编内核或生成刷机包。SELinux、真实身份/DTB、TEE交付及节点绑定仍待核实，其余硬件/启动问题仍保留。无真机测试，不宣称指纹或硬件可用。实时额度不可读取，81%/97%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
