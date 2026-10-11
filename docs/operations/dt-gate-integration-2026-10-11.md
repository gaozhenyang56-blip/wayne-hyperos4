# 逐次操作日志

时间显示为 America/Los_Angeles，同时保留 UTC 审计时间。

## 2026-10-11T04:19:25.113257-07:00 — resume-dt-gate-integration

UTC 起始：2026-10-11T11:19:25.113257+00:00；结束：2026-10-11T11:19:25.135615+00:00。

做了什么：检查b11efe4断点、差异和既有报告，定位真实6.6内核probe与allocator入口。

发生了什么：无开发差异，仅原有空MD；两个workflow分别调用ci_kernel_66_probe与ci_allocator_implementation，共用build函数，可在副作用之前接入门禁。

下一步：最小接入主入口和build，提供只读preflight命令并测试拒绝时没有构建副作用。

证据：[原始日志](../../logs/20261011T111925113257Z-resume-dt-gate-integration.log)。

## 2026-10-11T04:19:26.834070-07:00 — dt-gate-integration-tests

UTC 起始：2026-10-11T11:19:26.834070+00:00；结束：2026-10-11T11:19:27.313171+00:00。

做了什么：接入两个6.6主入口及共用build，增加仅门禁模式，运行三项集成检查、两项既有门禁正反例和两个真实preflight拒绝检查。

发生了什么：五项测试通过，两个真实preflight均返回2；拒绝发生在chdir、依赖安装、fetch和编译前，五项旧材料不变。未启动workflow或长编译。

下一步：保存集成点、缺证据矩阵和命令，同步后立即暂停。

证据：[原始日志](../../logs/20261011T111926834070Z-dt-gate-integration-tests.log)。

