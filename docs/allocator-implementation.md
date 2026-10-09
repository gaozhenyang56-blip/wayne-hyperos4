# 6.6 受限分配器实现与构建阶段

更新：2026-10-09 13:31 PDT（20:31 UTC）。本轮目标为国行小米 6X（wayne），原版静态分区；当前系统不是 Miku UI，小米 A2 只作为明确标注的差异对照。4.19 与既有静态实验成果保留。

做了什么：实现可撤回的 `compat/wayne_dma_heap` 源代码客户端适配器，并提交独立构建流程。只接受项目自定义 profile 与 system mask、固定宽度 24 字节分配请求、cached 非安全内存，大小 1 字节至 16 MiB。真实后端打开 `/dev/dma_heap/system`、调用 DMA-heap 分配 ioctl，关闭 heap FD，将 buffer FD 的所有权交给调用者。它不创建 `/dev/ion`，不截获旧 vendor 调用，不声明 Qualcomm/OEM heap-id 等价。

发生了什么：host mock 正例、负例及 FD 生命周期检查通过；GNU/Linux ARM64、ARM32 对象与静态库交叉编译通过，ELF 类型已核对。未进行 Android bionic/NDK 链接或 ARM 运行测试。独立新配置内核构建通过，版本 `6.6.9-sdm660+`；完整 olddefconfig 后 system/CMA heap、DMA_CMA、SYNC_FILE 等配置核对通过。生成 Image.gz（8,266,726 字节）及研究 DTB（49,676 字节），不生成可刷 boot。

传统 32/64 位 handle-based ION、CUSTOM/SHARE/FREE、OEM heap、uncached/secure 标记及未知请求均拒绝。当前没有 CPU cache 同步、fence、GPU import 或 Android native_handle 实现；返回的 buffer 不能因此当作可交给图形 HAL 的成品。

## 证据与复现

- [源代码实现](../compat/wayne_dma_heap/adapter.c)、[针对性测试](../compat/wayne_dma_heap/test_adapter.c)、[本机报告](../research/allocator-implementation/host-tests.json)。
- [新内核构建报告](../artifacts/kernel-6.6-allocator-probe.json)、[最终断点](../research/allocator-implementation/checkpoint.json)、[实际应用补丁后的复现测试](../research/allocator-implementation/reproduction-test.json)、[最小补丁](../research/allocator-implementation/minimal-source-client.patch)。
- [ARM 双架构报告](../research/allocator-implementation/cross-build.json)、[独立云端构建](https://github.com/gaozhenyang56-blip/wayne-hyperos4/actions/runs/37986150560)。输出是研究对象、静态库和内核编译产物，不是刷机包。
- [旧 vendor 拒绝报告](../research/allocator-implementation/legacy-pairing.json)及[预期退出码检查](../research/allocator-implementation/interface-test.json)：仍缺 KGSL、ION 和 MSM framebuffer，预期退出码 2 实际为 2。
- [设备树/接口审计](../research/allocator-implementation/board-interface-audit.json)、[固定下游源码来源](../research/allocator-implementation/dts-sources.json)、[专属 include 来源](../research/allocator-implementation/dtsi-sources.json)。下游参考提交不能证明与成品包精确内核提交一致，更不能代表用户当前 vendor。

本机运行 `python3 tools/build_allocator_adapter.py --report research/allocator-implementation/host-tests.json`；配齐 GNU/Linux ARM 工具链后加 `--cross`，报告写入独立路径。独立工作流安装依赖、运行 mock 与双架构编译，再构建固定 6.6.9 源码及新的 heap/sync 配置。没有重发旧内核构建或覆盖旧报告。云端任务用时 10 分 26 秒，全部通过。

最小补丁相对已完成研究基线 `f40b63c`，只包含本轮兼容源码、构建脚本和独立工作流，仓库保存补丁及源提交 `0681027`。在独立 worktree 使用 `git apply --check` 再应用；不在4.19目录操作。回退可以删除新适配器和独立工作流，恢复构建脚本的可选报告路径改动；原实验镜像和发布资产不变。

## 设备与阻塞项

wayne 下游 board-id 为 `0x020008/0x50008`，jasmine 为 `0x030008/8`。两者共用部分硬件 include，但 wayne.dtsi 明确补充物理 system 的早期挂载，不能互换。成品包 fstab 明示 Non-A/B、物理分区、DT 早挂载和 `encryptable=ice`。参考 DT 的 system 类型为 ext4，而既有静态实验系统为 EROFS，后续须单独核对 first-stage 挂载方案，不能直接照搬。公开文件只能证明该参考的配置，不能证明用户设备的运行时配置或面板批次。

既有 6.6 DTS 仍继承 jasmine，修改 model/compatible 只用于编译脚手架。不能当国行 wayne 硬件支持；本轮没有盲目复制下游4.4绑定至6.6。固定6.6内核的公共 dma-heap 头未声明 `dma_heap_find`/`dma_heap_buffer_alloc`，因此未虚构基于这些函数的内核 ION 桥。

下一步：优先在源代码客户端路径补齐 `DMA_BUF_IOCTL_SYNC` 与同步负例，再做 Android NDK 双架构链接；随后需要真实兼容的 DRM/Mesa/mapper/composer 路径和 GPU DMA-BUF import 验证。若选择保留旧 vendor，必须完整移植 KGSL ioctl、旧 ION handle/OEM heap、MSM framebuffer 与相关 IOMMU/安全内存语义，跨度远超本轮最小补丁，不能靠设备节点别名解决。

剩余风险包括 SELinux 设备标签及 HAL 域权限（旧静态包严格 neverallow 仍失败）、显示面板与 DRM/KMS/composer、相机/音频下游驱动及 HAL ABI、ICE/用户数据解密、bootloader DT 选择、第一阶段挂载、固件与模块加载、VINTF 内核约束。保持 enforcing 目标，不以 permissive 宣称修复。

本轮已保存构建报告和下一断点并停止。研究资产 [11643856340](https://github.com/gaozhenyang56-blip/wayne-hyperos4/actions/runs/37986150560/artifacts/11643856340) 的上传日志与 API 元数据已核对；当前环境下载签名 blob 返回 HTTP 403，未完成本地读回。另发现本次 upload-artifact 默认排除了隐藏的 `.config`，其摘要与配置检查保留在报告中；已修正以后上传的设置，未为此重复内核编译。不生成6.6可刷 boot，不更改GPT或用户数据。没有真机测试，不能宣称可启动或任何硬件可用。用户报告额度为5小时75%、周58%，各保留约20%；工具未提供用量查询，按单次有时限构建控制工作范围，不声称精确控制额度。
