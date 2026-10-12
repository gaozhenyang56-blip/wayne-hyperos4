# 6.6.9长期基线更新资格：拒绝优先关系审计

时间：2026-10-11T19:39:13.545803-07:00；基线09dbede。国行wayne/SDM660静态分区独立实验，保留4.19与所有旧成果；与Miku UI无关。

做了什么：检查status/diff、源码文档、锁与来源记录；当前fork固定https://github.com/sdm660-mainline/linux.git提交6a4e475000ecc7e864911959a1984a0664088464，保存Makefile实际为6.6.9且SHA256符合锁。工作区缺sources/kernel-6.6-probe完整历史，没有核验固定更新候选；未进行远端下载或假称已查到最新6.6。

新增tools/check_source_update.py：严格版本化JSON，未知/缺字段、重复键、NaN/Infinity、非40位小写commit、current锁漂移或URL漂移拒绝。候选/base允许明确null表示缺失，输出blocked；candidate URL只允许当前fork或明确的kernel.org stable URL，不证明候选来自该URL。来源锁仍只描述历史第三方源码，不证明wayne硬件兼容。

在已有完整本地Git仓库上只读核对非浅历史、origin URL、精确commit存在、两版本Makefile、merge-base、双向commit计数、current是否candidate祖先、声明base是否current祖先及base后的commit清单。证据哈希按命令输出原字节计算，预期哈希缺失或篡改均保持blocked。报告采用固定顺序紧凑UTF-8 JSON、唯一末尾换行、禁非有限值，无当前时间或绝对工作区路径（Git命令目录记<repo>）。单次Git调用超时10秒，失败保留明确gap。

本第一小步刻意没有eligible输出路径：即便合成快进且哈希匹配，可信上游成员关系、非上游SDM660/wayne补丁分类及已审携带策略仍未建立。base..current清单只是相对声明base的commit，不冒称全部非上游补丁。patch_policy=preserve_current_ancestry仅检查是否保留current历史，不作为完整移植审阅；分叉拒绝。版本号大小不构成更新资格，更不构成可启动/可刷证明。

| 证据 | 当前实际状态 |
| --- | --- |
| current commit/Makefile | 固定提交与保存文件哈希可验证，版本6.6.9 |
| 精确candidate tag/commit | 缺，request明确null，不猜最新版本 |
| fork/candidate完整历史与merge-base | 缺，本地不存在完整6.6 Git树 |
| 双向commit计数/祖先关系 | 实际源码未核验，不能用合成测试替代 |
| 非上游板级补丁与携带策略 | 未建立；历史jasmine参考不作为wayne适配成果 |
| 真实采集/DTB provenance | 原成果保持，不扩展或伪造物理认证 |

发生了什么：四项合成小Git仓库测试覆盖快进、分叉、current含本地patch、浅历史/缺commit、篡改哈希、未知字段/重复键/NaN、commit/URL拒绝及同输入字节稳定；仅测试内部纯函数使用显式synthetic锁，CLI始终读取项目真实锁，无覆盖开关。三项既有门禁集成测试通过，共七项；两个真实6.6 preflight仍退出2。旧五项成果、源码锁、sources.lock及provenance工具/文档均字节未变。未执行rebase/merge/cherry-pick、修改DTS/defconfig/boot/vendor/固件/init/fstab、编译或打包。

直接复核：

```sh
python3 tools/test_source_update.py
python3 tools/check_source_update.py research/source-update-stage/current-blocked-request.json sources/kernel-6.6-probe
```

第二条真实CLI当前预期退出2并输出blocked，不写源码或报告文件；已保存[机器报告](../research/source-update-stage/blocked-report.json)。relation证据由merge-base/rev-list结果组合，报告标明组合命令而非虚构单条Git命令。取得完整历史后可按锁执行只读git show COMMIT:Makefile、git merge-base CURRENT CANDIDATE、git rev-list --left-right --count CURRENT...CANDIDATE、git rev-list BASE..CURRENT及git merge-base --is-ancestor检查；占位符须替换真实固定commit，不执行源码更新。

下一断点：先获取可核验的精确tag/commit及小规模来源元数据，再安排独立、有界完整历史/补丁成员审计；未审阅可信上游和携带政策前保持blocked，不扩大本轮。若将来增加eligible路径，必须另行审阅完整证据要求，不能仅修改版本字符串或删除缺口。

[断点/保留哈希](../research/source-update-stage/checkpoint.json)，[带时区记录](operations/source-update-2026-10-11.md)。没有真机验证，不宣称任何硬件或启动可用。所有DTB/boot/ABI/固件与构建阻断保留；实时额度不可读取，81%/64%仅用户快照，保存同步后暂停。
