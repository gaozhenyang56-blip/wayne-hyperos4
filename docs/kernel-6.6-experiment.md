# wayne 6.x 内核实验

更新时间：2026-10-09（UTC）。目标：探索 Linux 6.x，当前选择 6.6 编译探针。

做了什么：检索高版本源码，固定 SDM660 主线分支 `qcom-sdm660-6.6.y`，提交 `6a4e475000ecc7e864911959a1984a0664088464`。读取 Makefile 确認实际版本为 **6.6.9**，不是最新 6.6 稳定版。保留原 4.19 静态实验包，新增独立实验配置。

发生了什么：该分支提供 `sdm660_defconfig` 和小米 A2（jasmine）设备树，没有 wayne 专用设备树。另找到 wayne 专用 Linux 7.0.9 项目，作为板级差异参考；它采用 Debian 用户空间，作者的硬件测试结果不是本项目测试结果。下载部分原始文件时遇到 HTTP 429，改用 GitHub 内容 API 后成功取得证据。

当前限制：

- 6.6 的 wayne 定义将先复用 jasmine 设备树并修改板名；面板、触摸、供电及固件仍需逐项核对，不代表整机适配完成。
- Android 参考设备配置声明 `/dev/kgsl-3d0`、`/dev/ion`、`/dev/msm_camera/*`、`/dev/msm_pcm_lp_dec`。主线 DRM GPU、DMA heaps 和音视频接口不能直接当作这些厂商接口的替代品。
- 7.0.9 参考配置启用了 Binder，却未启用文件系统加密，且不提供已验证的 Android SELinux 配置。不能直接套入 HyperOS。
- boot 格式、早期模块/固件加载、VINTF 内核要求、厂商二进制 ABI 和实际启动均未验证。
- 用户设备维持原版大小的静态分区；本实验不更改分区，不生成可刷 boot，不替换公开实验包。

下一步：建立可复现的 6.6.9 Image 与 wayne DTB 构建，检查 Android 配置是否真正生效。编译通过之后，再处理 KGSL/显示、音视频和启动接口；无真机时不把构建成功记为启动成功。

源码证据：

- [SDM660 6.6 源码](https://github.com/sdm660-mainline/linux/tree/6a4e475000ecc7e864911959a1984a0664088464)
- [wayne 7.0.9 板级参考](https://github.com/jakecommon/linux-sdm660-xiaomi-wayne/tree/eefc44180fdfc30cdc760109c8acf189482c238d)
- [本项目固定版本与证据哈希](../config/kernel-6.6-experiment.json)
