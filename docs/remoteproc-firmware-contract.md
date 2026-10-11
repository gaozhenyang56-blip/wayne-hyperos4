# 固件／remoteproc启动依赖离线审计

时间：2026-10-11T09:18:55.328799-07:00；基线9cc0173。目标仅国行wayne/SDM660原始静态分区，独立6.6实验；不以jasmine、Miku UI或动态分区为基线。

做了什么：检查工作区、diff、最新报告和断点，只读提取保存的6.6源码配置、外国板级DTS、历史4.19/vendor及非Miku vendor参考的配置/固件路径/加载命令。新增tools/verify_remoteproc_contract_stage.py保存来源哈希、行号及固定输入比对；不复制固件、不改DTS/config/加载参数、不编译打包。

发生了什么：最高优先可证明缺口是模块与早期固件加载交付未闭合。保存的6.6 defconfig将Q6V5_MSS/PAS/WCSS、WCNSS_PIL/CTRL及IPA声明为=m；实际构建入口仅make Image.gz和DTB，旧报告modules_built=false。不能据此认定最终生成.config全部仍=m，或实际wayne必须使用每个驱动；但现有材料不足以证明启动所需驱动、固件与加载时序齐备。入口没有固件复制/打包步骤，没有可证明的“忽略missing firmware”分支，外国板级include已由现有DTB门禁拒绝，故本轮只记录矩阵，不臆造文件存在性门禁或修改配置为=y。

| 契约项 | 当前仓库证据 | 阻塞／范围 |
| --- | --- | --- |
| 6.6驱动配置 | 保存defconfig REMOTEPROC=y、Q6V5/WCNSS/IPA=m、SMEM与GLINK/RPMSG声明；固定输入哈希比对见JSON | 非最终.config；未交付模块，模块依赖与时序未知 |
| 4.19接口 | 历史嵌入defconfig REMOTEPROC未启用，但MSM_PIL、SUBSYSTEM_RESTART、SMEM、GLINK/RPMSG有声明 | actual_build_configuration=false；不能将mainline REMOTEPROC=n解释成历史系统没有DSP/基带启动 |
| ADSP/CDSP/SLPI | 历史init.target写/sys/kernel/boot_adsp/boot、使用/vendor/dsp/cdsp/fastrpc_shell_3；非Miku init.qcom声明boot_slpi/ssr权限 | 历史用户空间请求，不证明6.6提供同接口，未确认当前wayne节点/驱动/固件 |
| modem／PIL／SSR | 非Miku参考init.qcom请求pil_msa、peripheral_loader和subsystem_restart参数；fstab参考modem挂载至/vendor/firmware_mnt | 不能静默替换成6.6 remoteproc接口，不证明实际分区或服务可用 |
| 固件名与DT | 当前6.6 DTS直接继承jasmine；保存jasmine DTS含qcom/adsp.mdt及GPU/venus firmware-name | 外国板级源码证据，不是wayne固件要求；ADSP/CDSP/SLPI/modem/WCNSS/IPA真实节点与绑定均待核实，禁止照抄 |
| 搜索/交付路径 | 历史vendor ueventd声明/vendor/firmware_mnt/image/，历史system声明/etc/firmware/、/odm/firmware/、/vendor/firmware/、/firmware/image/ | 不证明内核直读/用户helper及mount时序闭合；非实际当前搜索链 |
| 固件库存 | 本地历史vendor有GPU/相机/指纹等选定固件，实际modem/DSP分区原件未取得 | 提取范围不完整，不能用“找不到”推断设备无固件；不猜文件名或复制替换 |
| 共享内存／GLINK／RPMSG | 配置有声明，真实DTB/reserved-memory、通道/endpoint和日志缺失 | 不能凭配置存在声称共享内存布局、服务连接或硬件已验证 |

集成点：两个6.6workflow → ci_kernel_66_probe.main/build及ci_allocator_implementation.main/--kernel共用build。未来真实资料齐全后，应在实际模块/固件交付入口核对文件哈希、DTB绑定、搜索路径与mount/uevent时序；本轮未创建此入口。既有DTB拒绝保持，boot/ABI仅有证据差距记录，没有独立打包/ABI放行门禁，不能虚称已验证。

复核：

```sh
python3 tools/verify_remoteproc_contract_stage.py
```

三项既有门禁测试通过，两个真实preflight均退出2，五项保留哈希不变；[断点与精确行号](../research/remoteproc-contract-stage/checkpoint.json)。无实际remoteproc启动测试，无新固件产物。

下一步实际设备只读采集（尚未执行；错误/无权限/缺节点须原样保存）：

```sh
adb pull /sys/firmware/fdt wayne-current.dtb
adb pull /proc/config.gz wayne-current-config.gz
adb shell 'cat /proc/mounts; cat /proc/cmdline; ls -l /dev/block/bootdevice/by-name; ls -l /sys/class/remoteproc' > wayne-firmware-layout.txt
adb shell 'for p in /sys/class/remoteproc/*; do echo "$p"; cat "$p/name" "$p/firmware" "$p/state"; readlink -f "$p/device/of_node"; done' > wayne-remoteproc-status.txt
adb shell 'cat /sys/module/firmware_class/parameters/path; find /vendor /odm /lib/firmware /firmware -type f' > wayne-firmware-inventory.txt
adb shell 'cat /vendor/etc/ueventd.rc; cat /system/etc/ueventd.rc; find /vendor/etc/init /odm/etc/init -type f' > wayne-firmware-init-inventory.txt
adb shell dmesg > wayne-remoteproc-kernel-log.txt
adb shell logcat -b all -d > wayne-remoteproc-logcat.txt
```

只读sysfs状态，不写state、不触发start/stop/SSR；缺mainline sysfs不证明downstream PIL不可用。依据实际mount清单追加对应固件挂载根目录库存，逐项拉取实际文件/init/fstab并哈希，保存来源、带时区时间与真实执行命令；不预设分区名或固件名。DTB身份读取只输出根属性，完整remoteproc子节点与reserved-memory需另用可用只读DT工具核对，当前未完成。

保留4.19与6.6及既有实验包；SELinux、显示/GPU、相机、音频、加密、基带、Wi-Fi与启动等风险未解除。无真机测试，不宣称remoteproc或硬件可用。实时额度无法读取，67%/82%仅用户快照；同步后立即暂停。
