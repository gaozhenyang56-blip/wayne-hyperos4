# wayne 6.x 内核实验

更新时间：2026-10-09（UTC）。目标：探索 Linux 6.x，当前选择 6.6 编译探针。

2026-10-09 12:48（America/Los_Angeles）基线纠正：目标仅为国行小米 6X（wayne），原版静态分区；项目与 Miku UI 无关，历史 Miku 文件仅是第三方研究样本，不是当前系统或 6.x 默认 vendor 基线。用户实际 boot/vendor 尚未知。6.6 编译探针继承了 jasmine DTS 的板级定义，这只验证构建，不能当作小米 A2 与 6X 硬件完全相同的证明。

本轮没有重复编译。新增 DMA-BUF heaps/system/CMA 和 sync 配置请求，仅作用于后续实验；上次内核及其报告保持不变。[本轮 GPU/内存分配器阶段记录](gpu-allocator-stage.md)保存成品包证据、测试范围与后续断点。

做了什么：检索高版本源码，固定 SDM660 主线分支 `qcom-sdm660-6.6.y`，提交 `6a4e475000ecc7e864911959a1984a0664088464`。读取 Makefile 确認实际版本为 **6.6.9**，不是最新 6.6 稳定版。保留原 4.19 静态实验包，新增独立实验配置。

发生了什么：该分支提供 `sdm660_defconfig` 和小米 A2（jasmine）设备树，没有 wayne 专用设备树。另找到 wayne 专用 Linux 7.0.9 项目，作为板级差异参考；它采用 Debian 用户空间，作者的硬件测试结果不是本项目测试结果。下载部分原始文件时遇到 HTTP 429，改用 GitHub 内容 API 后成功取得证据。

当前限制：

- 6.6 的 wayne 定义将先复用 jasmine 设备树并修改板名；面板、触摸、供电及固件仍需逐项核对，不代表整机适配完成。
- Android 参考设备配置声明 `/dev/kgsl-3d0`、`/dev/ion`、`/dev/msm_camera/*`、`/dev/msm_pcm_lp_dec`。主线 DRM GPU、DMA heaps 和音视频接口不能直接当作这些厂商接口的替代品。
- 7.0.9 参考配置启用了 Binder，却未启用文件系统加密，且不提供已验证的 Android SELinux 配置。不能直接套入 HyperOS。
- boot 格式、早期模块/固件加载、VINTF 内核要求、厂商二进制 ABI 和实际启动均未验证。
- 用户设备维持原版大小的静态分区；本实验不更改分区，不生成可刷 boot，不替换公开实验包。

## 首次构建结果

时间：2026-10-09T14:38:22Z（UTC）。

做了什么：运行固定源码的交叉编译，并检查实际生成的配置和 DTB。

发生了什么：[云端任务 37944711030](https://github.com/gaozhenyang56-blip/wayne-hyperos4/actions/runs/37944711030) 全部通过。生成 `6.6.9-sdm660+` 内核 `Image.gz`（8,261,631 字节）及 wayne DTB（49,676 字节），Binder、Binderfs、SELinux、文件系统加密、EXT4、EROFS 和 32 位兼容配置检查通过。DTB 的 compatible 为 `xiaomi,wayne qcom,sdm660`。完整驱动模块未构建，不能直接作为 Android 启动内核刷入。

生成配置、内核和 DTB 已保存在该任务的 `wayne-kernel-6.6-research-only` Artifact 中；[构建报告及哈希](../artifacts/kernel-6.6-probe.json) 已写入仓库。编译日志也已实时上传。尝试在当前工作区下载 Artifact 时遇到 HTTP 403，因此尚未完成本地独立读回；不将云端生成的哈希记作本地复核结果。

下一步：优先解决 KGSL/ION 与参考 vendor 的接口兼容，再核对 wayne 面板/触摸差异、早期模块和固件、音视频、boot 封装及 VINTF 内核要求。当前分支仍是 6.6.9，若继续作为长期基线，需要合入后续稳定版修复。无真机时不把构建成功记为启动成功。

源码证据：

- [SDM660 6.6 源码](https://github.com/sdm660-mainline/linux/tree/6a4e475000ecc7e864911959a1984a0664088464)
- [wayne 7.0.9 板级参考](https://github.com/jakecommon/linux-sdm660-xiaomi-wayne/tree/eefc44180fdfc30cdc760109c8acf189482c238d)
- [本项目固定版本与证据哈希](../config/kernel-6.6-experiment.json)
