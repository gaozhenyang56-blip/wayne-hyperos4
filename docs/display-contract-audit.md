# wayne 6.6 显示接口短审计

时间：2026-10-09 21:13 America/Los_Angeles（2026-10-10 04:13 UTC）。基线：18d4c6b。目标仅为国行小米6X（wayne/SDM660）、原始静态分区；与 Miku UI 无关，jasmine 不作为目标。

做了什么：沿用仓库已保存的非 Miku wayne 成品包比较材料，校验提取文件 SHA256，核对 ELF 依赖、设备路径、显示属性和 init 服务。修复审计器将字符串 `"false"` 当作真值的问题：KGSL、ION、MSM-FB 能力必须全部是显式 JSON 布尔值，缺失或错误类型立即拒绝。没有修改设备树、内核配置、属性或服务。

发生了什么：四项针对性测试通过，旧版本绕过得到复现，修复后拒绝。真实参考样本与现有6.6实验的配对检查按预期返回2。原有参考材料和已保存内核报告不变，4.19方案、6.6成果和现有实验包保留；没有完整重编译或生成可刷包。

| 参考样本证据 | 与6.6实验的关系 |
| --- | --- |
| 32/64位 libgsl 引用 `/dev/kgsl-3d0`、`/dev/ion`，gralloc.sdm660 引用 `/dev/ion` | 当前能力声明缺少 KGSL/ION；受限 system-heap 适配器不补足这两个旧 ABI |
| hwcomposer.sdm660 依赖 libsdmcore/libsdmutils；后者引用 `/dev/graphics/fb`、`/sys/devices/virtual/graphics/fb0/mdp/caps`、`msm_fb_type` 等 | 当前能力声明缺少 MSM-FB；libsdmcore 同时依赖 libdrm，不能据此删除旧 FB 要求 |
| build.prop 包含 `ro.hardware.egl=adreno`、`vendor.gralloc.enable_fb_ubwc=1` 及 display/surface_flinger 属性 | 仅是参考用户空间期望，未证明6.6支持其缓冲布局、修饰符或颜色行为；未猜测或修改属性 |
| 保存的 composer@2.1 init 服务声明 IComposer default、system 用户、graphics/drmrpc 组，并在重启时重启 surfaceflinger | 仅是该样本的服务契约，不能推出用户当前 HAL 版本，也不能证明6.6 DAC/SELinux及服务启动满足要求 |

复现：`python3 tools/audit_display_contract.py`。报告：[audit.json](../research/display-contract-stage/audit.json)，其中逐条保留文本路径、行号、哈希和测试结果；ELF 节点与 DT_NEEDED 见 [graphics-contract.json](../research/display-contract-stage/graphics-contract.json)。最小补丁：[minimal-flag-validation.patch](../research/display-contract-stage/minimal-flag-validation.patch)。审计通过仅说明静态检查自身符合预期，布尔能力仍是配置声明，不是运行验证。

下一步：先采集用户当前 wayne 的 vendor 二进制（32/64位及传递依赖、SHA256）、实际DTB、服务注册、节点权限和启动日志。本地参考样本不是当前 vendor；缺少文件可能在 system 或其他路径，不能断言系统运行时缺库。以下只读命令尚未执行，节点不存在、命令缺失或权限不足也应原样记录：

```sh
adb shell getprop ro.hardware.egl
adb shell getprop vendor.gralloc.enable_fb_ubwc
adb shell getprop > wayne-current-properties.txt
adb shell 'ls -lZ /dev/kgsl* /dev/ion /dev/graphics /dev/dri /dev/dma_heap'
adb shell 'ls -lZ /sys/devices/virtual/graphics'
adb shell lshal > wayne-current-hal-services.txt
adb shell dumpsys SurfaceFlinger > wayne-current-surfaceflinger.txt
adb shell logcat -b all -d > wayne-current-logcat.txt
adb shell dmesg > wayne-current-dmesg.txt
```

这些输出需要与实际 vendor init/VINTF、ueventd/SELinux策略及 AVC 对照。不得伪造 ioctl、HAL版本、固件、寄存器或节点；不得创建别名把 DRM 冒充 MSM-FB。待核实 buffer handle、fence/cache coherency、UBWC/secure-buffer、32/64位装载与显示供电时钟/IOMMU依赖。SELinux、显示/GPU、相机、音频、加密、启动仍有阻塞，无真机验证，不宣称显示可用或可启动。

断点：[checkpoint.json](../research/display-contract-stage/checkpoint.json)。本轮到此保存暂停。无法读取实时额度，不声称精确控制用量；仅保留用户给出的62%/41%为会话参考。
