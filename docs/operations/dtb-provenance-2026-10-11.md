# 逐次操作日志

时间显示为 America/Los_Angeles，同时保留 UTC 审计时间。

## 2026-10-11T18:52:03.027576-07:00 — dtb-provenance-tests

UTC 起始：2026-10-12T01:52:03.027576+00:00；结束：2026-10-12T01:52:06.722214+00:00。

做了什么：检查93bf21a工作区、sources.lock历史来源、导入/身份/导出与断点；新增版本化provenance manifest严格验证和独立确定性哈希绑定envelope，仅提交明确合成fixture。

发生了什么：四项新测试与四十二项既有回归通过；容器实际切片核对或无容器声明降级均不认证实物；两个真实preflight仍退出2，五项保留哈希不变，规范consumer schema未改。

下一步：保存绑定层、实际测试、限制与下一断点并同步暂停，不增加签名信任链或构建放行。

证据：[原始日志](../../logs/20261012T015203027576Z-dtb-provenance-tests.log)。


## 2026-10-11T18:53:12.987953-07:00 — 合成fixture同步

做了什么：补充跟踪被全局bin规则忽略的小型合成容器fixture并同步GitHub。

发生了什么：manifest及容器均明确synthetic/not device evidence，未上传虚构真机采集物。

下一步：保存后暂停；真实采集链仍待取得。
