# 有界Git历史关系探测

时间：2026-10-11T21:24:19.621295-07:00；基线73e35d6。仅国行wayne/SDM660静态分区独立6.6实验，与Miku UI无关。

做了什么：新增run_bounded_history_probe.py，隔离downloads/history-probe-73e35d6两个裸仓库，无工作树、无子模块/LFS。一批并行获取，每个远端仅一次fetch，depth=64（小于512）、blob:none、精确fork OID及官方refs/tags/v6.6.158，不重试、不加深。单远端20秒、对象/pack磁盘16MiB、诊断1MiB上限，监控越界/过滤不支持/机器人挑战即杀进程组。100ms轮询存在检测延迟，结束后再次核对大小，越界仍blocked，不宣称严格零超调。目录已存在则拒绝再次运行网络批次。

发生了什么：官方kernel.org返回filtering not recognized by server，立即停止，exit=-9、对象0字节，无候选commit图；未回退成完整源码获取。fork成功exit=0，FETCH_HEAD peeled OID为6a4e475000ecc7e864911959a1984a0664088464，取得2904740字节对象/pack/索引元数据，浅边界见fork-fetch.json。没有完整候选图和fork完整历史，不能给merge-base、祖先否定或双向完整计数；关系undetermined、更新blocked。不把无merge-base当没有共同历史。

精确远端URL、完整fetch命令（隔离目录规范化为标记）、exit code、ref取得命令/输出哈希、depth、浅边界、对象文件相对路径/字节/SHA256均保存在*-fetch.json。原始stdout/stderr及时间保存在*-run.json（时间非规范）。官方未成功，不将tag名当已取得peeled对象。对象包仅留隔离实验目录，不上传为源码或刷机包。

新增history_probe.py只读离线基础层：固定格式规范JSON，无当前时间/绝对目录；GIT_NO_LAZY_FETCH=1避免读对象触发promisor下载。精确commit格式检查；任何缺对象或浅历史保持undetermined。仅非浅图且rev-list --missing=error、merge-base、双向计数全部实际成功才记录关系；即使成功也blocked，补丁清单、可信成员与携带策略仍未审。validate_fetch复核版本/URL/命令/depth/对象大小与SHA256，拒绝缺/逃逸路径、篡改及未知顶层/对象字段；字节报告验证不等于获取成功或来源认证。

测试：三项新合成历史测试与四项复用小Git测试、三项既有门禁测试，共十项通过；覆盖已知祖先、分叉、浅边界不判定、缺对象、哈希/URL漂移与字节确定性。合成仓库仅由测试创建，非真实SDM660历史。真实抓取报告的文件大小/哈希另已读回核对。两个真实6.6入口仍退出2，旧保留材料哈希不变。

可直接离线复核：

```sh
python3 tools/test_history_probe.py
```

API probe(repo,current,candidate)返回确定性关系报告bytes；validate_fetch(raw,repo,url,ref)只校验本地已有对象元数据。不要重跑网络runner，本轮批次已用完。对象被清理后须记录缺失，不能将规范报告当本地对象仍存在的证明。

下一断点：当前fork仅depth64；官方候选未取得。所需更深程度无法从本轮确定，不猜一个足够的depth值。先单独审阅官方过滤能力或可核验同一候选的元数据获取路线，并制定后续有界完整性预算；需要完整相关祖先图或另外明确足够的关系证明后才尝试计数。本轮不切换远端、不重试、不自动加深、不下载完整源码。

[实际报告/断点](../research/history-probe-stage/checkpoint.json)，[带时区记录](operations/history-probe-2026-10-11.md)。sources.lock、源码锁、DTS/defconfig/boot/vendor/固件/init/fstab、4.19、DTB provenance及既有包保持；无rebase/merge/cherry-pick、编译/打包或真机测试，不宣称启动、可刷或硬件兼容，所有门禁保留。实时额度不可读取，47%/59%仅用户快照；保存同步后暂停。
