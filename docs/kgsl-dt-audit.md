# 6.6 KGSL设备树与接口短阶段审计

时间：2026-10-09T20:15:24.295995-07:00（America/Los_Angeles）。从 `a7b4140` 继续，目标国行小米6X（wayne/SDM660）、原版静态分区。项目独立，与Miku UI无关；jasmine不是目标基线。当前用户DTB、vendor与运行日志未取得，已有非Miku参考包和公开源码不能冒充当前设备证据。

做了什么：核对仓库已有wayne DTS/DTSI来源、include请求、KGSL与供电/时钟/IOMMU文本线索，以及已记录的非Miku vendor图形接口。新增带源码摘要校验的include闭包审计，修复“直接片段未发现KGSL就当全树没有KGSL”的审计缺口。只使用已有材料，不下载新供体，不改设备树或硬件参数，不重编内核。

发生了什么：4项正反例通过：完整模拟include可记录KGSL文本；缺失include不能证明KGSL缺失；循环引用不算闭包完整；注释中的GPU和include不算证据。即使文本闭包完整，也不代表CPP、DTC、绑定或phandle解析通过。测试中的模拟节点不是硬件配置，不应用到产品。

| 对象 | 可确认内容 | 未能确认的依赖 |
| --- | --- | --- |
| 下游wayne入口与片段 | 固定来源摘要一致；实际解析到3份wayne源码，另有10项未解析include请求 | 公共SDM660节点、GPU绑定及供电/时钟/IOMMU provider |
| 供电属性文本 | 片段含hall设备的 `vdd-io-supply`，只记录为未归属GPU的普通属性线索 | 不能据此填写GPU供电，不能证明clock/power-domain/IOMMU映射 |
| 6.6 wayne文件 | 仍include jasmine，仅改model/compatible；本轮未改写该历史编译脚手架 | 无国行wayne板级验证，不能因compatible标签就通过GPU审核 |
| 非Miku参考vendor | libgsl指向KGSL与ION；gralloc需要ION；显示库需要MSM framebuffer | 6.6实验profile未提供三类旧ABI，配对仍拒绝；当前用户vendor未知 |

本次审计只扫描仓库保存的文本映射，不知道原构建CPP include搜索根。报告给出的缺失路径是相对查找候选，不能当成已证明的原始文件位置；每条未解析请求另保存include原文与引用源文件。下游公共缺失项包括 `sdm660.dtsi`、`sdm660-mtp.dtsi`、`xiaomi-sdm660-common.dtsi`、`longcheer-sdm660-base.dtsi` 等，完整清单见报告。固定参考源码提交也未与参考ROM内核精确匹配。

新工具把供电/时钟/IOMMU匹配标为未归属节点的文本线索，不冒认GPU依赖；不猜寄存器、中断、时钟ID、固件文件名或新增别名设备节点。DT节点存在不等于KGSL驱动/ioctl存在，主线DRM路径不能直接满足旧KGSL用户空间。现有4.19、6.6报告、图形profile、设备树和实验包均保持不变。

下一步需要的证据：

- 当前实际boot及运行中的DT，包含root compatible、实际GPU节点和所有引用provider；若系统导出 `/sys/firmware/fdt`，在已获root的环境只读采集 `adb exec-out su -c 'cat /sys/firmware/fdt' > current-wayne-live.dtb`。未导出时记录缺失，不用jasmine替代。
- 与该DTB匹配的完整源码/commit、CPP include搜索路径和bindings；据此解析regulator、clock、power-domain和IOMMU/context的真实phandle。实际目标GPU节点路径未知，不能预先猜路径。
- 当前 `/dev/kgsl*` 与 `/dev/dri` 的存在性、标签和权限，以及GPU初始化、IOMMU、regulator/clock、固件请求相关dmesg/内核日志。已有root时可只读采集dmesg；未授权或读取失败则保留错误，不改设备状态。
- 当前vendor图形ELF的摘要、依赖及匹配内核KGSL UAPI/驱动实现。先记录实际固件请求，再确认所需文件，不凭其他机型填名称。

这些命令本轮未执行，没有真机测试，不宣称GPU、显示、启动或硬件可用。本阶段没有移植整套KGSL或生成可刷包。

[审计与来源](../research/kgsl-dt-stage/audit.json)、[测试](../research/kgsl-dt-stage/tests.json)、[下一断点](../research/kgsl-dt-stage/checkpoint.json)、[逐次时间记录](operations/kgsl-dt-audit-2026-10-09.md)。最小改动为新增 [审计工具](../tools/audit_kgsl_dt_closure.py) 与 [定向测试](../tools/test_kgsl_dt_closure.py)，不改变现有构建配置。运行 `python3 tools/audit_kgsl_dt_closure.py` 与 `python3 tools/test_kgsl_dt_closure.py -v` 可复现。

短阶段已保存并暂停。用户报告5小时75%、周43%，各保留约20%；未发现实时额度工具，不声称精确控制用量。
