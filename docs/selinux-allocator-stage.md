# 短阶段 SELinux 静态审计

更新时间：2026-10-09T14:56:06.036035-07:00（America/Los_Angeles）。基线为 `9e22a9b`，目标是国行小米6X（wayne/SDM660）、原版静态分区。项目与 Miku UI 无关，jasmine 不是目标。没有真机或 AVC。

做了什么：检查 Git 状态、既有断点和历史策略结果；从本地已保存的非Miku Lineage19.1 wayne vendor 镜像只读提取4项SELinux材料。下载仅限固定6.6源的一份8KB驱动文件，没有大包、内核编译或完整GPU移植。历史 neverallow 失败材料仍保留原来源，不能当用户当前策略。

发生了什么：发现适配器用 `O_RDWR` 打开 `/dev/dma_heap/system` 控制FD，引入多余 write 权限需求。实验供体平台的 `hal_graphics_allocator -> dmabuf_system_heap_device` 显式规则列出 read/open/ioctl 等权限，无 write；固定6.6 dma-heap驱动的 open/allocate 不检查控制FD可写。已将控制FD改为 `O_RDONLY | O_CLOEXEC`；返回buffer仍用 `O_RDWR | O_CLOEXEC`。这只减少权限需求，不证明客户端已获授权，其他属性规则仍可能授予write。

本机 mock 正例、heap/buffer标志分别检查、EACCES/EPERM 在 open 和 ioctl 阶段的直接拒绝、FD生命周期及原ION/OEM/secure负例通过。基线旧代码被新的只读控制测试拒绝，证明该测试能发现原问题。没有执行实际SELinux内核访问检查、Android/ARM运行测试或新的交叉编译。

| 节点/策略 | 已有材料证明的内容 | 未核实项 |
| --- | --- | --- |
| `/dev/dma_heap/system` | 实验平台显式标签为 `dmabuf_system_heap_device`，不同于通配 `dmabuf_heap_device` 和 secure heap类型 | 当前设备最终合并标签、调用者实际域、属性展开、DAC、ioctl xperm |
| `/dev/kgsl-3d0` | 非Miku参考vendor显式标签为 `gpu_device`；现代实验平台有 app_zygote 等域的GPU neverallow | 当前vendor与平台配对后的实际授权/冲突；6.6仍未提供旧KGSL |
| `/dev/ion` | 参考CIL有 `ion_device_32_0` 相关allow； inspected两份contexts未发现此节点显式标签 | 平台其他contexts、最终标签及32.0映射；6.6仍未提供旧ION |
| neverallow | 已保存语法层面的相关规则证据；历史严格编译确实失败 | 历史失败不能外推本轮或当前设备；本轮未合并不匹配版本策略，不宣称无冲突 |

没有添加allow、重标记节点或启用permissive。没有把 `hal_graphics_allocator` 当作新客户端的已知域。非Miku参考vendor策略版本32.0与实验供体平台不能未经映射就拼接；属性、neverallow及allowx证据只作线索，不能凭字符串扫描判定最终访问。

下一步：先确认重新编译客户端的实际域，取得当前用户vendor策略、完整匹配平台/映射及节点标签；再做严格合并编译和ioctl xperm检查。真机可用后收集 `ls -Z`、DAC及AVC，才考虑范围明确的策略修复。无这些证据不添加宽泛授权。

[静态证据](../research/selinux-allocator-stage/audit.json)、[来源与提取摘要](../research/selinux-allocator-stage/sample-source.json)、[固定6.6驱动来源](../research/selinux-allocator-stage/kernel-source.json)、[本机结果](../research/selinux-allocator-stage/tests.json)、[旧代码拒绝结果](../research/selinux-allocator-stage/regression.json)、[最小补丁](../research/selinux-allocator-stage/readonly-control.patch)、[下一断点](../research/selinux-allocator-stage/checkpoint.json)、[逐次记录](operations/selinux-allocator-2026-10-09.md)。

复现测试：`python3 tools/build_allocator_adapter.py --output downloads/allocator-selinux-test --report research/selinux-allocator-stage/tests.json`。审计工具 `tools/audit_allocator_selinux.py` 读取本地实验平台与参考vendor原始材料；原始策略放在忽略的 raw 目录，公开报告保留路径、SHA256及带行号的证据。补丁仅改两份C源码，可以在9e22a9b独立worktree应用；回退该补丁即可，不影响旧内核和发布包。

阶段已保存并暂停，旧4.19/6.6报告、静态成果及历史严格策略报告逐字节保持不变。不宣称启动或硬件验证。用户报告5小时39%、周52%，各须保留约20%；未发现实时用量读取工具，不能精确核算剩余额度。此次不延长审计。
