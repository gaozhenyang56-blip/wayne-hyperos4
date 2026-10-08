# 小米 6X / wayne HyperOS 4 移植工程

**当前目标已更正：用户设备为非动态分区，分区大小与原版一致，也不是 Miku UI。现有 `offline-20261006` 仅为 Miku RDP 布局研究产物，不适用于该设备，不能直接刷入。此前交付不满足当前设备要求。静态分区版本尚未生成；继续查证原厂分区容量与兼容的 4.19 启动/硬件底包，保留原分区表。**


更新：2026-10-09（北京时间；[本轮操作记录](docs/operations/2026-10-09.md)，[连接恢复与修复记录](docs/operations/2026-10-08.md)）。

目标是 Snapdragon 660 的小米 6X，保留 wayne 的 Linux 4.19 硬件支持，移植 HyperOS 4。没有真机测试。已按用户允许的 Mi8937 社区供体路线完成云端构建，并发布约 3.17 GB 的分卷实验刷机包。完整归档读回、镜像哈希和公开资产大小/摘要核验通过。[下载实验包](https://github.com/gaozhenyang56-blip/wayne-hyperos4/releases/tag/offline-20261006)。尚未验证启动或硬件功能。

## 当前采用的材料

| 用途 | 已验证的材料 | 状态 |
| --- | --- | --- |
| 实验系统供体 | Mi8937 社区标称 HyperOS 4.0.0.16 Beta 的包 | SD430/435 老平台；版本属性与 CRC 已检查，但不能据此证明框架真实性或官方 HyperOS 4 身份；继续作为实验候选，不能视为官方机型支持 |
| 目标硬件支持 | Miku UI wayne Android 15 | 保留 wayne vendor、4.19.315 内核、DTB、cmdline 和数据加密挂载参数 |
| 配置较接近的候选 | Redmi Note 11 spes，SD680 / 4.19 | boot 已核验；完整下载受阻，系统内部版本未确认，暂未用于构建 |
| 官方框架对照 | 小米 15 dada 官方 OS4 | 用于对照，不使用其硬件支持或启动镜像 |

Mi8937 使用更老的 SD430/435，并非相同 SoC。此前用它进行离线实验，是因为包内声明 Android 17 / OS4，且发布者声称有 4.19 旧平台适配。属性核对不足以验证实际框架版本，现继续实验路线：与官方对照包比较的 61 个框架/APEX 文件中有 47 个完全一致，核心框架文件仍有差异，补丁来源未完全核验。spes 保留为备选。更接近候选的证据见[材料选择记录](research/candidates/selection.json)。

## 当前检查结果

- system 重打包通过 EROFS 解码检查；原有 9,134 个路径的 UID/GID、模式和二进制 xattr 保持一致；所有文件内容与软链接已逐项比较。
- 实际改动为三份设备身份属性、新增 FCM 5 矩阵，以及换回 wayne 自身的设备 HAL 矩阵。没有把 vendor 的 FCM 等级改成新设备等级。
- 合并 wayne vendor HAL 清单及碎片后，通过固定提交的 AOSP libvintf 框架矩阵检查。此检查不覆盖 APEX、内核、运行时服务或 linker namespace。
- 相机及显示入口的依赖文件和入口未定义符号检查通过；不能据此宣称硬件可用。
- 2026-10-07 新增实际 runtime APEX bionic 与传递版本符号审计：四个目标在选定作用域内均无缺库或未解析必需符号；LIBSYNC 的 AOSP 全局回退单独记录。[报告](research/wayne-os4-native-versions.json)不代表实际 Android 命名空间或硬件功能通过。独立编译的版本正反例及打包拒绝场景已验证。
- SELinux 严格 neverallow 检查失败；Android init 风格的 -N 模式可以编译，但不会被记作严格检查通过。
- boot 保留 wayne 内核，替换供体 first-stage init，适配合并后的分区布局；尚未验证启动。

参考内核的 IKCONFIG 被源码构建规则固定为旧 defconfig，不是实际生成的 .config。其 EROFS_FS 字段不能用于判定当前内核是否支持 EROFS；二进制中已发现 EROFS 实现痕迹。用户手机的实际内核二进制和配置仍未取得。

## 记录与复现

每次操作记录时间、做了什么、发生了什么和下一步；原始命令与输出另存日志。2026-10-08 GitHub 连接恢复，此前未同步的原生库审计代码、报告和 MD 已补传，恢复每次 MD 修改后立即上传。

- [当前逐次操作日志](docs/operations/2026-10-09.md)
- [2026-10-08 操作记录](docs/operations/2026-10-08.md)
- [云端构建完整阶段记录](docs/operations/github-build-37803213948.md)
- [云端复现流程](.github/workflows/build-experimental.yml)
- [实际交付状态](artifacts/delivery-status.json)
- [实验分卷与镜像哈希](artifacts/candidate-package.json)
- sources.lock.json：固定上游源码提交。
- tools/：下载、镜像转换、元数据保留重打包和离线兼容性检查工具。
- research/：来源、哈希及检查结果。

大型原包、镜像和解包目录不进入 Git。实验成品使用 Releases 分卷资产，并标明构建提交、哈希和验证范围。

## 旧 RDP 实验产物（不适用于当前设备）

公开预发布：[https://github.com/gaozhenyang56-blip/wayne-hyperos4/releases/tag/offline-20261006](https://github.com/gaozhenyang56-blip/wayne-hyperos4/releases/tag/offline-20261006)。

下载 `.zip.001`、`.zip.002`、`SHA256SUMS`、`INSTALL.txt` 和 `manifest.json`。两份分卷大小分别为 1,900,000,000 与 1,268,883,752 字节；按编号合并为 ZIP 后解压，不能单独刷入某个分卷。详细安装步骤见 Release 的 `INSTALL.txt`。构建提交为 `73526dd35460dc6c65465333b6b01d2851e95649`；Release 标签与该提交一致。[分卷及镜像摘要](artifacts/candidate-package.json)、[发布核验报告](artifacts/release-publication.json)。

仅适用于已经采用 Miku wayne retrofit 动态分区布局的设备。安装器要求 Python 3.11+，默认仅校验镜像；显式刷写时验证设备、分区布局、空间和镜像哈希，再写入 system/vendor/boot。此包不转换原厂或其他分区布局。

[成功云端任务](https://github.com/gaozhenyang56-blip/wayne-hyperos4/actions/runs/37803213948)完成原包哈希、镜像内容与元数据、boot、原生库版本符号、进度推送竞态回归、HAL 声明、ZIP 完整读回和远端资产摘要检查。公开的安装说明、清单与校验文件也已独立下载核验。本次为未真机验证的实验预发布；严格 SELinux neverallow 仍失败，运行时 linker/APEX、启动、加密和硬件行为尚未验证。

此前本地分卷保留为旧检查点，与此次云端成品哈希不同；旧报告保存在本地 `artifacts/releases/local-checkpoint-c7926a9/`。安装与校验请使用同一 Release 的完整附件。
