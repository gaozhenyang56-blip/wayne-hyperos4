# vendor ABI／模块契约离线阶段

时间：2026-10-11T08:43:40.425348-07:00；基线5b20e27。目标仅国行wayne/SDM660原始静态分区，独立6.6实验；不以jasmine、GKI或Miku UI为目标。

做了什么：读取boot阶段报告/断点，检查现有6.6构建、产物报告、历史4.19与非Miku vendor材料；新增只读复核脚本，输出材料范围、配置声明、模块文件与加载命令以及门禁/保留哈希结果。不修改配置、模块或任何旧实验包。

发生了什么：最高优先ABI缺口是实际当前用户vendor模块契约缺失。6.6报告记录modules_built=false，本地没有对应生成.config、Module.symvers或模块；未发现6.6入口执行modules_install、复制4.19模块或打包vendor_dlkm，因此没有可安全接入的错误模块路径，不凭假设添加入口。三项既有门禁集成测试通过；两个真实preflight均退出2，五项保留材料哈希不变。boot阶段保留的是契约缺口记录，并没有独立boot打包门禁；本轮不虚称存在该门禁。

| 项目 | 可证明材料 | 未解决证据 |
| --- | --- | --- |
| UTS/版本 | 6.6旧编译报告为6.6.9-sdm660+；历史比较boot banner为4.19.315-Miku-Vampire_v2-g3a74d7，仅历史来源 | 用户目前4.19准确uname/config/vendor未知，不等同历史版本 |
| MODVERSIONS | 历史嵌入vendor defconfig声明=y | 来源说明actual_build_configuration=false；非实际生成配置，6.6fragment未规定此项，最终状态未知 |
| module_layout/vermagic | 本地提取材料未找到.ko/modules.dep，范围见JSON | 实际模块的vermagic、依赖符号与module_layout CRC均缺，不能用release字符串替代CRC核对 |
| 模块签名 | 历史defconfig声明SIG/FORCE/ALL=y，hash=sha512、key路径certs/signing_key.pem | 不证明实际构建强制签名，实际信任证书/签名模块与6.6策略未知；不采集私钥、不签名 |
| 加载路径 | 历史init.target请求/vendor/lib/modules/wlan.ko；历史netmgrd请求/vendor/lib/modules及5.4-gki路径；非Miku选定init里的qce示例是注释 | 仅历史/条件加载请求，不证明执行或文件交付；不得据5.4-gki字样判定目标GKI |
| 必需符号 | 6.6旧报告明确legacy KGSL/ION/MSM-FB ABI未提供；模块所需ELF undefined符号未取得 | 缺模块ELF、Module.symvers、真实/proc/kallsyms与加载错误；built-in也需单独核对，不能把modules_built=false解释为全部驱动缺失 |
| GKI/KMI | 固定SDM660源码研究构建，没有仓库证据建立KMI兼容承诺 | VINTF配置片段或内核版本不证明GKI/KMI；不给通用模块兼容结论 |
| vendor_dlkm | 无实际当前设备挂载/分区清单；6.6workflow仅上传.config/Image.gz/DTB | 未确认存在或不存在；不得因此添加分区或动态布局 |

集成点：ci_kernel_66_probe.main/build、ci_allocator_implementation.main及--kernel共用build，前置既有DTB身份门禁；未来若出现模块交付入口，须先补真实来源/config/symvers与模块绑定后再设计拒绝检查。本轮没有新增放行或构建入口。

直接复核，不编译、不打包：

```sh
python3 tools/verify_vendor_module_contract_stage.py
```

[断点与精确本地加载请求](../research/vendor-module-contract-stage/checkpoint.json)。库存为空只描述被提取的本地材料，不代表用户实际系统或完整供体无模块。

下一步只读采集（尚未执行；不存在、工具缺失或无权限须保留原始错误）：

```sh
adb shell 'uname -a; cat /proc/version; cat /proc/modules; cat /proc/mounts' > wayne-module-runtime.txt
adb shell 'ls -l /dev/block/bootdevice/by-name; ls -ld /vendor_dlkm /system_dlkm /vendor/lib/modules /system/lib/modules' > wayne-module-layout.txt
adb shell 'find /vendor /odm /system /vendor_dlkm /system_dlkm -type f -name "*.ko"; find /vendor /odm /system /vendor_dlkm /system_dlkm -type f -name "modules.*"' > wayne-module-inventory.txt
adb pull /proc/config.gz wayne-current-config.gz
adb shell cat /proc/kallsyms > wayne-current-kallsyms.txt
adb shell dmesg > wayne-module-kernel-log.txt
adb shell logcat -b all -d > wayne-module-logcat.txt
```

确认清单后，逐个adb pull实际模块及modules.dep/alias/softdep/load到本地，保存来源、带时区时间、实际命令和SHA256；不猜模块名或路径。对本地真实.ko执行modinfo FILE（vermagic/signer/sig_key/sig_hashalgo）、readelf -Ws FILE（UND符号），有版本节时只读检查__versions；缺modinfo/readelf明确保留失败。kallsyms可能受权限限制或地址清零，不能当完整导出/CRC证据；最终仍需实际生成.config、Module.symvers及运行加载日志。仅采集公有证书/签名信息，不采集签名私钥，不insmod试验。

DTB阻断和boot契约缺口不解除；SELinux、显示/GPU、相机、音频、加密、固件与启动风险保留。没有真机测试，不宣称兼容、启动或硬件已验证。实时额度不可读，89%/85%仅为用户快照；同步后立即暂停。
