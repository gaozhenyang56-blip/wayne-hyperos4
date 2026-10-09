# 逐次操作日志

时间显示为 America/Los_Angeles，同时保留 UTC 审计时间。

## 2026-10-09T14:53:38.178710-07:00 — resume-short-selinux

UTC 起始：2026-10-09T21:53:38.178710+00:00；结束：2026-10-09T21:53:38.204417+00:00。

做了什么：检查 9e22a9b 断点和策略来源，读取本地非Miku wayne 成品包 SELinux 材料。

发生了什么：无开发差异。历史严格策略失败不能代表当前用户系统。发现适配器以 O_RDWR 打开 system heap，而本地平台对 allocator 的显式 heap allow 无 write；固定6.6驱动不要求 heap FD 写模式。只读提取初次debugfs路径错误，纠正后成功。

下一步：把 heap控制节点改为只读打开，保留返回buffer读写标志，运行正例/拒绝测试并保存域和neverallow待核实项。

证据：[原始日志](../../logs/20261009T215338178710Z-resume-short-selinux.log)。

