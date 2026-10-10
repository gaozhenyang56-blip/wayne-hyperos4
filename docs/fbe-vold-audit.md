# 静态分区 FBE/vold/ICE 一致性短阶段

时间：2026-10-09T19:38:05.770597-07:00（America/Los_Angeles）。从 `dddc2f5` 继续；目标国行小米6X（wayne/SDM660）、原版静态分区。当前用户vendor、GPT和真机日志未取得。固定wayne配置和非Miku成品包作为参考，历史第三方材料仅证明既有产物来源，不是目标基线。

做了什么：检查工作区、已有断点、fstab加密标志、metadata引用、vold启动参数和保存的4.19/6.6配置证据。修复静态转换中遗漏的依赖检查：工具删除metadata挂载后，保留条目若显式设置 `keydirectory=/metadata` 或其子目录，即拒绝转换并要求持久存储证据。不猜测替代分区或密钥目录，不删除该标志来绕过错误。

发生了什么：旧代码能输出上述矛盾样例，新代码确实拒绝。5项定向正反例和4项历史转换回归通过；包含保留FBE标志、保留FDE参考标志、来源曾有metadata挂载仍须拒绝、以及不误判 `/metadata_backup` 等边界。边界样例通过只表示不触发这一检查，不证明该目录正确或持久。最小补丁在dddc2f5独立worktree应用检查通过。

现有实验fstab没有metadata keydirectory或metadata_encryption参数，其转换结果逐字节未变。没有修改实际FBE/FDE算法、fstab文件、加密路径或发布镜像。

| 证据 | 能确认的内容 | 不能确认的内容 |
| --- | --- | --- |
| 固定wayne配置与既有实验data | `fileencryption=ice`，ext4/f2fs候选行保留 | 用户userdata实际文件系统、fscrypt策略与解锁状态 |
| 非Miku wayne参考vendor | `encryptable=ice`，与FBE参考参数不同 | 哪一种参数适合用户当前数据；不据此切换模式 |
| 4.19保存kernel.config | 文本声明FS_ENCRYPTION、ext4/f2fs encryption、QCOM ICE、DM_DEFAULT_KEY等 | 元数据明确 `actual_build_configuration=false`：这是内嵌defconfig，不是实际构建.config，不能证明运行能力 |
| 6.6实验 | 构建报告核对FS_ENCRYPTION和EXT4等前置项；源defconfig声明F2FS | 完整构建配置未在本地读回，ICE/inline crypto/DM_DEFAULT_KEY、DT与硬件接口未验证；不能把4.19符号名称直接套用 |
| vold.rc | 参数是blkid/fsck的SELinux上下文；core服务 | 参数不选择cipher，也不能证明现代vold/fs_mgr正确解释旧ice或能解密 |
| metadata与服务 | 既有data无明确metadata密钥依赖；供体init仍有metadata/APEX/checkpoint路径 | metadata持久性、checkpoint设计、keymaster/TEE与SELinux整合 |

剩余的这些未知阻止完整一致性和解密结论。此次没有匹配的vold/fs_mgr源码审计或实际vold运行测试，不宣称配置全面自洽、可启动、可解密或ICE硬件可用。

下一步：沿用[上轮只读采集清单](boot-static-audit.md)，取得当前fstab、mountinfo、ro.crypto属性和vold/fs_mgr日志。如果设备已经提供root且导出配置，可只读运行 `zcat /proc/config.gz`；不存在时记录未导出，不把内嵌defconfig当替代。还需当前keymaster/TEE版本、与实际vold匹配的fs_mgr/加密解析源码，以及metadata/APEX/checkpoint的真实挂载证据。具备fscryptctl时可只读查询实际用户目录的policy；不读取原始密钥，不格式化userdata，不凭设备名设置ICE能力。

[带来源摘要及行号的审计证据](../research/fbe-vold-stage/audit.json)、[测试结果](../research/fbe-vold-stage/tests.json)、[最小补丁](../research/fbe-vold-stage/minimal-dependency.patch)、[下一断点](../research/fbe-vold-stage/checkpoint.json)、[逐次时间记录](operations/fbe-vold-audit-2026-10-09.md)。本机复现：`python3 tools/audit_fbe_vold_config.py`、`python3 tools/test_static_fbe_dependency.py -v`。旧配置、4.19/6.6报告和现有实验包保持不变；不生成可刷包，不重编内核。

已保存短阶段断点并暂停。用户报告5小时85%、周44%，各保留约20%；没有可用实时额度工具，不声称精确控制额度。
