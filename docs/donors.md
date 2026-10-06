# 更接近小米 6X 的供体

检索日期：2026-10-06。目标为 Snapdragon 660 的 wayne，用户提供当前内核系列 4.19。

## 首选：Redmi Note 11（spes/spesn）

- Snapdragon 680，不是与 660 相同的 SoC，但仍是高通中低端平台。
- [官方规格](https://www.mi.com/global/product/redmi-note-11/specs/)
- [社区发布记录](https://t.me/RedmiNote11Mods/1675)：声明 HyperOS 4 Beta／Android 17。
- [不含 Kaorios 修改的下载链接](https://pixeldrain.com/u/kmZT7B8z)
- 文件名：`hos4.0.0.17.wpacnxm_a17_spes.zip`，4,813,008,353 字节。
- 服务端提供 SHA-256：`cec53dad779dc1e4c4477f24da00408a209a1d1d70fcbae25f1639b8f7e907c2`，完整 ZIP 尚未下载校验。
- 已提取并核验 boot 条目 CRC；二进制 banner 为 `4.19.325-hanbal-gforce-base`。
- ZIP 的 OTA metadata 沿用 Android 13，不能用文件名确认内部 Android 17。下一步检查 system 的 build.prop、framework、APEX 和 VINTF。
- 首次完整下载出现 HTTP 403，留下不完整 `.part`；不算成功下载。

证据：`research/candidates/spes-os4/`、`spes-clean-info.json`、`spes-download.log`。

## 备选及补丁参考：Mi8937

- 支持 santoni、ugg、land；属于比 660 更老的高通平台，不是同 SoC。
- [发布者页面](https://alphas-trashdump.github.io/#/r/Mi8937/hyperos-4.0.0.16-beta)
- [原包链接](https://drive.google.com/file/d/1_Tu-HcN1PIz4PItm5vvCuh5FrjJpfDTX/view)
- 发布者声明 Android 17／HyperOS 4.0.0.16 Beta、4.19、NON-RDP，并提及 SurfaceFlinger 补丁。
- system.new.dat 解压后约 2.94 GB，值得检查旧平台适配与分区占用。
- 完整下载并通过全部 ZIP 条目 CRC 检查，实测 boot 内核为 `4.19.325-cip135-st19-FuntimeKernel-v2.5-[OC]-erofs`；本地 SHA-256 见 `local-zip-check.json`。未核验来源签名。
- metadata 混有旧 Android 信息，安装脚本的版本声明不能代替系统内部验证。

证据：`research/candidates/mi8937-os4-release.json`、`mi8937-os4/inspection.json`。

## 其他候选

Redmi Note 12 4G tapas/topaz 使用 Snapdragon 685，已找到 OS4 社区包，但官方内核源码为 5.15，优先级低于已有 4.19 的 spes。

Redmi Note 7 lavender 使用同款 Snapdragon 660；本次找到 HyperOS 1/2 的社区记录，未找到可核验的 HyperOS 4 下载包。这个结论仅限本次检索，不代表不存在。

小米 15 的官方 OS4 用于框架对照。其启动布局、内核要求与 wayne 差异较大，因此不继续把它作为优先供体。
