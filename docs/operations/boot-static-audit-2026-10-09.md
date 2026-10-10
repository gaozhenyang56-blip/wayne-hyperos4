# 逐次操作日志

时间显示为 America/Los_Angeles，同时保留 UTC 审计时间。

## 2026-10-09T18:49:11.328012-07:00 — resume-static-boot-audit

UTC 起始：2026-10-10T01:49:11.328012+00:00；结束：2026-10-10T01:49:11.339252+00:00。

做了什么：检查 f3cb6fc 工作区与已有 boot/init/fstab/FBE 证据，限定短阶段离线审计。

发生了什么：无开发差异；真实当前boot/vendor和GPT未取得。非Miku wayne参考boot是header0、无super参数；现有static_cmdline却强制要求super参数，证明转换工具仍错误依赖动态样本。保留历史来源与成果，不作为当前设备基线。

下一步：修复静态cmdline输入的错误前置条件，核对本地既有产物和加密风险并运行正反例。

证据：[原始日志](../../logs/20261010T014911328012Z-resume-static-boot-audit.log)。

## 2026-10-09T18:51:20.763435-07:00 — test-static-boot-audit

UTC 起始：2026-10-10T01:51:20.763435+00:00；结束：2026-10-10T01:51:20.815690+00:00。

做了什么：修复 static_cmdline 对super参数的错误依赖，完成静态boot/fstab/init与加密证据检查。

发生了什么：4项定向正反例和4项既有转换回归通过；真实非Miku参考cmdline旧代码拒绝、新代码接受。既有静态boot摘要、ramdisk的fstab/init和静态cmdline只读检查通过。未发现data fstab悬空metadata密钥参数，但供体init有metadata路径，加密/持久性仍未知。

下一步：记录header0/1限制、FDE/FBE参考差异及只读真机采集命令，保存补丁和断点后暂停。

证据：[原始日志](../../logs/20261010T015120763435Z-test-static-boot-audit.log)。

## 2026-10-09T18:55:10.947620-07:00 — finish-static-boot-audit

UTC 起始：2026-10-10T01:55:10.947620+00:00；结束：2026-10-10T01:55:10.957166+00:00。

做了什么：保存静态启动/加密审计、最小修复、测试结果与采集断点并结束本轮。

发生了什么：旧4.19/6.6和静态发布报告逐字节不变，实际本地boot摘要匹配已保留发布清单。首次保留核验误把忽略的本地metadata当Git文件，已改用发布清单校验。无容量猜测、无新可刷包、无内核重编。header、metadata持久性、vold/ICE解密和当前设备状态仍待真机证据。

下一步：暂停；下轮先收集当前boot/fstab/GPT/mountinfo和不含密钥的加密日志，再确定定向适配，不格式化userdata。

证据：[原始日志](../../logs/20261010T015510947620Z-finish-static-boot-audit.log)。

