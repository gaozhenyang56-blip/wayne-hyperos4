# 逐次操作日志

时间显示为 America/Los_Angeles，同时保留 UTC 审计时间。

## 2026-10-09T19:34:50.652401-07:00 — resume-fbe-vold-audit

UTC 起始：2026-10-10T02:34:50.652401+00:00；结束：2026-10-10T02:34:50.666328+00:00。

做了什么：检查 dddc2f5 断点、fstab/vold及4.19和6.6加密配置证据。

发生了什么：无开发差异。4.19保存配置是embedded defconfig而非实际构建配置；6.6已确认FS_ENCRYPTION但未确认ICE。static_fstab会去掉metadata而未拒绝保留的metadata密钥目录依赖，存在可复现检查缺口，现有data条目没有该引用。

下一步：增加严格的metadata keydirectory拒绝检查，保留现有FBE/FDE参数并验证正反例。

证据：[原始日志](../../logs/20261010T023450652401Z-resume-fbe-vold-audit.log)。

## 2026-10-09T19:36:36.294614-07:00 — test-fbe-vold-audit

UTC 起始：2026-10-10T02:36:36.294614+00:00；结束：2026-10-10T02:36:36.370257+00:00。

做了什么：修复metadata密钥目录依赖检查缺口，记录fstab/vold与内核能力证据边界。

发生了什么：5项定向与4项历史回归通过；旧代码会输出引用已删除metadata挂载的keydirectory，新代码拒绝相同样例。真实现有转换结果逐字节不变，未改加密算法或路径。4.19 defconfig声明和6.6 FS_ENCRYPTION前置项不升级为ICE能力证明。

下一步：保存最小补丁、来源、只读采集项与下一断点，短阶段结束后暂停。

证据：[原始日志](../../logs/20261010T023636294614Z-test-fbe-vold-audit.log)。

