# 逐次操作日志

时间显示为 America/Los_Angeles，同时保留 UTC 审计时间。

## 2026-10-09T20:12:35.283953-07:00 — resume-kgsl-dt-audit

UTC 起始：2026-10-10T03:12:35.283953+00:00；结束：2026-10-10T03:12:35.293428+00:00。

做了什么：检查 a7b4140 断点、wayne设备树片段和非Miku vendor图形接口，限定短阶段审计。

发生了什么：无开发差异。wayne下游片段include闭包不完整，不能把直接片段未见KGSL当全树缺失；6.6文件仍继承jasmine编译脚手架，不是wayne板级基线。既有非Miku vendor需要KGSL/ION/MSM-FB，而实验profile未提供这些ABI。

下一步：增加include闭包证据检查与正反例，记录供电/时钟/IOMMU缺失来源，保存断点暂停。

证据：[原始日志](../../logs/20261010T031235283953Z-resume-kgsl-dt-audit.log)。

