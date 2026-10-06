# 小米 6X / wayne HyperOS 4 移植工程

更新：2026-10-06（逐项精确时间见[操作记录](docs/operations/2026-10-06.md)）。

目标是 Snapdragon 660 的小米 6X，保留 wayne 的 Linux 4.19 硬件支持，移植 HyperOS 4。没有真机测试。目前已生成研究用 boot/system 镜像；Mi8937 已降为适配参考，基于它的最终包制作与发布已暂停。尚未确认最终供体，也没有发布刷机成品。

## 当前采用的材料

| 用途 | 已验证的材料 | 状态 |
| --- | --- | --- |
| 仅作旧平台适配参考 | Mi8937 社区标称 HyperOS 4.0.0.16 Beta 的包 | SD430/435 老平台；版本属性与 CRC 已检查，但不能据此证明框架真实性或官方 HyperOS 4 身份；不作为最终供体 |
| 目标硬件支持 | Miku UI wayne Android 15 | 保留 wayne vendor、4.19.315 内核、DTB、cmdline 和数据加密挂载参数 |
| 配置较接近的候选 | Redmi Note 11 spes，SD680 / 4.19 | boot 已核验；完整下载受阻，系统内部版本未确认，暂未用于构建 |
| 官方框架对照 | 小米 15 dada 官方 OS4 | 用于对照，不使用其硬件支持或启动镜像 |

Mi8937 使用更老的 SD430/435，并非相同 SoC。此前用它进行离线实验，是因为包内声明 Android 17 / OS4，且发布者声称有 4.19 旧平台适配。属性核对不足以验证实际框架版本，现暂停这条成品路线，继续检查配置更接近的候选。更接近候选的证据和取舍见[供体记录](docs/donors.md)。

## 当前检查结果

- system 重打包通过 EROFS 解码检查；原有 9,134 个路径的 UID/GID、模式和二进制 xattr 保持一致；所有文件内容与软链接已逐项比较。
- 实际改动为三份设备身份属性及新增 FCM 5 矩阵。没有把 vendor 的 FCM 等级改成新设备等级。
- 合并 wayne vendor HAL 清单及碎片后，通过固定提交的 AOSP libvintf 框架矩阵检查。此检查不覆盖 APEX、内核、运行时服务或 linker namespace。
- 相机及显示入口的依赖文件和入口未定义符号检查通过；不能据此宣称硬件可用。
- SELinux 严格 neverallow 检查失败；Android init 风格的 -N 模式可以编译，但不会被记作严格检查通过。
- boot 保留 wayne 内核，替换供体 first-stage init，适配合并后的分区布局；尚未验证启动。

参考内核的 IKCONFIG 被源码构建规则固定为旧 defconfig，不是实际生成的 .config。其 EROFS_FS 字段不能用于判定当前内核是否支持 EROFS；二进制中已发现 EROFS 实现痕迹。用户手机的实际内核二进制和配置仍未取得。

## 记录与复现

每次操作通过 tools/record_step.py 记录时间、命令、结果和输出哈希；每次 Markdown 修改后立即通过 GitHub 插件提交。同步失败时先处理失败，不积攒到阶段末尾。

- [逐次操作日志](docs/operations/2026-10-06.md)
- [阶段工作记录](docs/worklog.md)
- sources.lock.json：固定上游源码提交。
- tools/：下载、镜像转换、元数据保留重打包和离线兼容性检查工具。
- research/：来源、哈希及检查结果。

大型原包、镜像和解包目录不进入 Git。最终成品应通过 Releases 或分卷资产发布，并标明构建提交、哈希和验证范围；当前还没有最终成品。
