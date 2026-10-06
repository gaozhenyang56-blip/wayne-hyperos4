# 操作与变化记录

## 2026-10-06：公开仓库初始化前历史追记

本节依据工作区现有文件追记。此前没有 Git 提交与完整命令审计，不能声称逐条原始操作均已保存。已有工具、检查输出与来源元数据随初始化提交公开；从此开始记录命令及逐阶段提交。

1. 获取小米 15 官方 OS4 OTA 的目录、metadata、payload manifest，校验 metadata SHA-256；提取 system、system_ext、init_boot 并核验各分区 SHA-256。证据：`research/donor-dada-os4/`、`research/*extract.log`。
2. 获取 wayne Miku UI Android 15 底包目录与 boot、vendor 数据，检查内核 4.19.315；重建 vendor 并通过 EROFS 检查。证据：`research/base-miku-a15/`、`research/base-*.log`。
3. 固定设备树、内核和 vendor 构建文件提交；内核与 vendor 部分检出。证据：`sources.lock.json`。
4. 检查 VINTF、SELinux mapping、分区容量及 HAL 直接依赖。发现 FCM 5 与官方供体矩阵不匹配，原始分区组合超限；没有完成策略编译和导出符号检查。证据：`audit.json`、`research/base-hal-dependencies.json`。
5. 原厂 MIUI 12 完整下载速度过慢，终止，保留 `.part`；没有将不完整文件当成成功下载。
6. 按用户要求重选接近配置的供体，检索 lavender/ginkgo/spes/tapas/topaz/creek/Mi8937 的官方规格、内核源码、公开 ROM 索引和社区记录。证据：`research/candidates/*.json`、内核 Makefile。
7. 实际提取 spes 社区 OS4 的 boot，确认 Linux 4.19.325；OTA metadata 为沿用 Android 13，系统内部版本待核验。首轮完整下载发生 HTTP 403。证据：`research/candidates/spes-os4/`、`spes-download.log`。
8. 找到 Mi8937 的 OS4／4.19 发布记录，检查远程 ZIP 目录和安装脚本，启动完整下载。是否完成与完整性校验另行记录。
9. 用户要求使用 GitHub 创建公开仓库，记录全部步骤、变化和最终成品。已通过连接核验账号；CLI 同账号认证可用。创建前整理此文档、供体比较和仓库忽略规则。

## 当前状态

供体调查阶段；spes 暂列首选，Mi8937 为备选及旧平台补丁参考。没有完成 ROM，没有真机测试。大型文件发布状态见 `artifacts/README.md`。

## 2026-10-06 06:38 UTC：新建公开仓库被权限限制阻止

- 通过 GitHub 连接确认账号为 `gaozhenyang56-blip`；CLI 使用同一账号。
- 使用已授权 CLI 请求新建公开仓库 `gaozhenyang56-blip/wayne-hyperos4`。
- 返回：`GraphQL: Resource not accessible by integration (createRepository)`，退出码 1。未建立远程仓库，也未上传文件。
- 精确命令、时间和输出：`logs/20261006T063818014984Z-create-public-repository.{json,log}`。
- 已告知用户创建空的公开仓库并提供链接；在等待期间完成本地 Git 提交与工程备份。

## 初始化时新增的记录机制

新增 `tools/record_step.py`，对后续命令保存 UTC 起止时间、完整参数、退出码、输出文件和输出 SHA-256。新增 `AGENTS.md`，要求按阶段更新本日志并提交。

历史原始 shell 命令未完整留存，本地初始提交代表现有工程快照；后续提交才逐项反映新增变化。

## 2026-10-06 06:39 UTC：Mi8937 候选包完整性与内核实证

- 完整下载大小 2,683,141,762 字节；全部 17 个 ZIP 条目 CRC 检查通过。
- 本地计算 SHA-256：`1a9a9eb684e1174455ae3a84524de2e4f309ddc62e7dacae6565aa8d2dd14c39`。没有发布者可信哈希或签名核验，不将 CRC 等同于真实性保证。
- 提取 boot 并解压内核，从二进制确认 `4.19.325-cip135-st19-FuntimeKernel-v2.5-[OC]-erofs`，不再仅依赖发布者的内核声明。
- 完整性检查成功后，`.part` 改名为 `.zip`。内部 system 的 HyperOS／Android 版本依然待核验。
- 精确命令与输出在 `logs/*validate-mi8937-download*`、`logs/*inspect-mi8937-boot*`、`logs/*finalize-mi8937-download-name*`。
- Python 脚本编译检查通过，见 `logs/*compile-project-scripts*`。
- 初始化本地提交 `95480b7` 已完成；公开 GitHub 仓库仍因创建权限限制等待建立。

## 2026-10-06 06:46 UTC：用户创建仓库，上传被写入授权阻止

- 用户提供公开仓库：https://github.com/gaozhenyang56-blip/wayne-hyperos4 。通过 CLI 和 GitHub 插件确认 PUBLIC；初始远程仓库为空。
- 设置本地 origin；尝试正常推送 main 的已有两次提交，返回 HTTP 403：`Permission to gaozhenyang56-blip/wayne-hyperos4.git denied to gaozhenyang56-blip`。
- GitHub 插件仓库元数据返回 push/admin 等权限为 true，但实际 create_file 写入 README 同样返回 HTTP 403：`Resource not accessible by integration`，错误码 FORBIDDEN。该写入未成功，远程 README 未建立。
- 因而目前没有上传任何工程文件，也没有发布最终产物。请求用户在 GitHub 应用设置中授权新仓库，或重新连接并选择该仓库；没有改用其他身份绕过限制。
- CLI 命令与失败输出：`logs/*configure-github-remote*`、`logs/*push-initial-history*`。插件失败摘要见 `logs/github-write-access.json`。

## 2026-10-06 06:49 UTC：授权更新后使用插件同步

- 用户确认已更新授权。Git 传输重试返回 HTTP 401，见 `logs/*push-after-authorization*`；不能根据其中的 Everything up-to-date 判断上传成功。
- GitHub 插件 create_file 已成功，远程初始化提交为 `dc69c7a6a5cac57b5c4e970d53e3aa26dc8b41ca`。说明插件写入权限现已可用。
- 后续通过插件的 Git tree/commit/ref 接口上传完整工程快照，保留远程初始化提交作为父提交。
- 原本的本地提交不会因快照同步而拥有相同的远程 SHA；将其完整历史保存为 `artifacts/project-history.bundle` 随工程上传，可用 `git clone project-history.bundle restored-history` 恢复。
- 本记录写入时快照正在准备；远程发布结果以 main 分支实际文件和提交为准。没有发布最终 ROM。
