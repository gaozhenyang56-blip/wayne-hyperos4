# 6.6 GPU / 内存分配器阶段断点

时间：2026-10-09 12:52，America/Los_Angeles（UTC 19:52）。

做了什么：检查工作区、Git 差异及上轮报告，保留 4.19 和首次 6.6 编译成果。优先检查同机型非 Miku 成品包，完成图形 ABI 审计，修正基线声明并补齐后续 6.6 分配器配置。

发生了什么：本阶段的取证、配置小修复与 8 项离线测试完成。没有重编译内核，没有新的 boot/刷机包，没有真机验证。

## 基线纠正

目标是国行小米 6X（wayne），不是小米 A2/jasmine，保持原版大小的静态分区。用户当前系统不是 Miku UI，实际 boot/vendor 二进制尚未知。项目独立，与 Miku UI 无关；历史文件曾使用 Miku 第三方样本，应保留其真实来源，不能把它当作用户系统、原厂硬件基线或新 6.x 默认 vendor。

README、项目要求与 6.6 文档已纠正。既有 Releases、原 4.19 方案、来源锁和旧测试报告保留，不重写历史。首次 6.6 DTB 继承 jasmine 板级内容，只能证明构建成功，6X 面板、触摸、电源及保留内存差异仍待核对。

## 成品包对照结论

样本：[发布者的 LineageOS wayne 包](https://sourceforge.net/projects/lineageos-wayne/files/lineage-19.1-20251122-UNOFFICIAL-wayne.zip/download)。这是非官方 LineageOS 包，不认定为用户 ROM或官方硬件验证结果。只读取必要 ZIP 成员；成员 CRC 通过并记录 SHA256，没有验证整包签名/发布者整包哈希。没有执行其安装脚本。

| 项目 | 包内证据 | 对 6.6 的意义 |
| --- | --- | --- |
| 设备 / 布局 | pre-device=wayne；脚本断言 wayne，使用物理 system/vendor/boot | 不采用 A2 或动态分区假设；脚本还写 splash，不直接沿用 |
| 启动 | boot v0，实际 4.4.302；metadata SDK 32 | 只能作为接口样本，不能当作 6.6 可启动证明；旧 MIUI 指纹不能代表实际系统版本 |
| GPU | 32/64 位 libgsl 含 KGSL 和 ION 路径；GLES 入口依赖图已记录 | 不能把闭源 Adreno GLES 库直接配主线 MSM DRM |
| 分配器 | 32/64 位 gralloc.sdm660 含 /dev/ion；allocator 2.0、mapper 2.1 | 要核对 ioctl、heap、句柄布局、缓存与同步，路径替换不够 |
| 显示 | libsdmcore/libsdmutils 含厂商 framebuffer 和 MDP 路径；composer 2.1 | DRM framebuffer 控制台不等于厂商 MDP ioctl；合成器也需要替换/适配 |
| 数据与挂载 | vendor fstab 使用物理分区，含 encryptable=ice | 只记录，不套用其加密或挂载规则到用户未知系统 |

以上是 ELF 字符串、DT_NEEDED、HAL 和启动配置证据，不是实际 ioctl 调用轨迹。选出的 vendor 样本不包含 libion.so，不能因此推断运行时缺库；其系统侧依赖、命名空间和完整图形符号闭包未在本阶段验证。

证据：[ZIP 目录/成员哈希](../research/gpu-allocator-stage/lineage-wayne/inspection.json)、[vendor 恢复哈希](../research/gpu-allocator-stage/lineage-wayne/vendor-restoration.json)、[选择文件清单](../research/gpu-allocator-stage/lineage-wayne/selected-files.json)、[图形依赖与接口报告](../research/gpu-allocator-stage/graphics-contract.json)。原始 ELF 不上传仓库，以来源和哈希复现。

## 本阶段落实的修复

6.6 配置片段新增 DMA-BUF heaps、system/CMA heaps、DMA_CMA 和 SYNC_FILE；未来编译器检查同步要求这些选项。固定源码的分配器 Kconfig 子树测试确认请求可生效，外部 DMA_CMA 关闭时 CMA heap 不会伪装成启用。此测试没有解析完整内核 Kconfig，也没有重新执行 olddefconfig/编译。

旧构建 Artifact 下载仍返回 403，实际旧 .config 未独立读回。因此缺口表述为“原配置源与片段未明确请求 heaps”，不宣称已读到旧内核的实际禁用位。旧 Image/DTB 与报告保持不变，新配置尚未产生内核成品。

新增只读取证工具、样本哈希校验和图形接口拒绝检查。`--reject-legacy-pairing` 对当前闭源样本配主线 DRM/heap 的组合返回 2；即使没有发现旧路径，也不判定硬件兼容或能够启动。

8 项测试涵盖三类旧接口拒绝、现代路径仍不承诺硬件成功、哈希篡改、空样本、原生 C UAPI 对比、固定 Kconfig 子树、稀疏恢复与重叠拒绝。C 对比使用固定 Lineage 源码的 ION UAPI，不是该包精确内核提交：该包短提交在所查仓库无法解析，不能据此确认旧 vendor 的所有 ioctl 细节。

## 选定的后续适配路径

沿用本项目固定的 SDM660 6.6 主线源码，后续单独建立 **Freedreno Gallium GLES + 主线 MSM DRM + 匹配的 gralloc/mapper/allocator + DRM hwcomposer** 图形实验。必须按一致的 dma-buf/native_handle/格式修饰符约定重建整条图形链，而不是只换 GPU 库或建 /dev/ion 软链接。需要同步处理 32/64 位、Android linker/VNDK、HAL 清单、属性、init 和 SELinux；主线 heaps 并未提供 Qualcomm 安全/保护堆的完整替代。

[Mesa 官方 Freedreno 文档](https://docs.mesa3d.org/drivers/freedreno.html)区分了 GLES 与 Turnip：A512 属于 a5xx，不能套用面向 a6xx 等较新 GPU 的 Turnip Vulkan 安装方案。HyperOS 对 Vulkan 的实际要求与替代策略仍未验证。参考 [Mesa Android 构建文档](https://docs.mesa3d.org/android.html)、[AOSP ION/heap 迁移说明](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)及 [AOSP DRM hwcomposer](https://android.googlesource.com/platform/external/drm_hwcomposer/)。这些提供组件路径，不构成本机集成结果；用户空间具体源码版本及 buffer ABI 必须在下一阶段固定。

保留旧闭源 vendor 的另一条路线需要真实移植 KGSL、对应 ION/安全堆和厂商显示 ABI 到 6.6。本轮没有找到并验证这样的 wayne 成品包，故不把它列作已可复现的现成解决方案。保留 4.19 作为独立旧方案。

## 复现与断点

依赖固定于 requirements-gpu-audit.txt；还需现有 requirements.txt、cc 与只读 debugfs。Linux UAPI/Kconfig 证据保留 SPDX 和来源哈希。Debian debugfs 工具只解包到本地，来源记录见 ext4-reader-source.json，不改系统包。

使用 `tools/extract_wayne_graphics_sample.py` 的 URL 常量，向分析输出目录读取指定成员；传入本地 debugfs 及 library-dir。已有缓存用 `--from-local`，避免再次下载。该工具校验成员哈希，拒绝增量/重叠 OTA 范围，稀疏恢复后只 dump 所选文件。

使用 `tools/audit_graphics_contract.py`：输入 selected-vendor、selected-files.json、config/kernel-6.6-graphics-profile.json，输出 graphics-contract.json。仅取证时不加拒绝选项，评估旧组合时加 `--reject-legacy-pairing`，预期退出 2。离线回归入口是 `python3 tools/test_graphics_contract.py -v`；无需下载成品包或重新编译内核即可运行保存证据及 UAPI/Kconfig 回归。

下一步：固定 GLES/分配器/合成器源码及 native_handle 合约，先做共享缓冲区导入导出与格式/同步离线测试，再决定是否进入新的构建阶段。本阶段在此结束，不自动发起内核重编译或刷机。

剩余：历史严格 SELinux neverallow 仍失败；6.x 图形设备/heap/service 标签及权限未集成；安全堆、缓存一致性、fence、UBWC/modifiers、固件加载、完整模块、VINTF 内核要求、boot 封装、加密与硬件均未验证。6.6.9 也需后续稳定版修复，不当作已维护的生产内核。

无法读取用户页面/周用量，未假称精确额度控制；本轮采用限定阶段，无持续大构建或无限重试。机器断点：[checkpoint.json](../research/gpu-allocator-stage/checkpoint.json)。逐项记录：[阶段 MD](operations/gpu-allocator-stage-2026-10-09.md)。
