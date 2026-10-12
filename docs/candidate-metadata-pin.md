# 固定6.6更新候选：远端元数据第二小步

时间：2026-10-11T20:52:10.803750-07:00；基线8a4ae07。仅国行wayne/SDM660静态分区独立实验，与Miku UI无关。

做了什么：一批受限查询分别对官方stable与当前fork各运行一次git ls-remote，25秒超时、禁交互、禁HTTP重定向，无重试、克隆或fetch packfile。保存完整stdout/stderr字节、命令、exit code、查询时间与SHA256；查询时间仅在非规范*-run.json和本操作记录，不进入candidate lock。没有CAPTCHA/机器人交互，两查询exit=0。

官方来源：https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git；本次查询中严格v6.6.N数值排序最高标签v6.6.158，tag对象70e787efdea3ce266068ff322c6226ff5d6d37dd，peeled commit a91a6aa9253c64936f0bd8273a2a3c11522ec9c3。官方原始输出19218字节，SHA256=014dbfc5174589cbbdc67052d88265f529dc78ff5008e1e958f8367789081535。这是本次ref查询候选，不宣称已经验证本地Git历史或未来全局最新。

fork来源：https://github.com/sdm660-mainline/linux.git；refs/heads/qcom-sdm660-6.6.y直接指向6a4e475000ecc7e864911959a1984a0664088464。原始输出350字节，SHA256=3c28e39f614b08dcf22b465cd0b917b0a68e1bb2317cbf01ab9e37daff315e3e；还有两个sdm660-rc参考tag及peeled refs，详见fork-summary.json，不用这些非严格版本替代官方候选。可见ref不指向某提交也不证明历史提交不存在。

新增tools/candidate_metadata.py与独立wayne.candidate-metadata.v1锁：绑定固定官方URL、精确查询命令、current commit、精确tag、tag对象、peeled commit和原stdout哈希。严格数值排序（9低于10）、拒绝同名重复/冲突、非严格tag、缺终止换行/超1MiB、失败/不完整查询或URL漂移；最高tag缺annotated/peeled配对直接blocked，不静默降级至较低tag。未知字段、重复JSON键、非有限值、schema/hash/tag/commit/URL/类型漂移均拒绝。确定性UTF-8紧凑JSON、固定键/数组顺序和末尾换行；无时间或绝对工作区路径。canon lock不包含运行状态时间。

发生了什么：五项合成ref测试、四项既有合成Git更新关系测试、三项构建门禁测试共十二项通过，另实际核验新锁与真实官方原字节一致。合成输入只在测试函数内生成，明确不是真实源码历史。两个真实6.6 preflight仍退出2；旧源码锁、sources.lock、8a4ae07报告/检查器、provenance与既有成果保留哈希不变。没有修改check_source_update，本阶段独立metadata CLI验证后也始终退出2，不能触发更新资格。

已执行的唯一远端查询批次（以下是历史命令，不建议本轮重跑）：

```sh
git ls-remote --tags https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git 'refs/tags/v6.6.*'
git ls-remote --heads --tags https://github.com/sdm660-mainline/linux.git 'refs/heads/qcom-sdm660-6.6.y' 'refs/tags/v6.6.*'
```

可直接离线复核：

```sh
python3 tools/test_candidate_metadata.py
python3 tools/candidate_metadata.py research/candidate-metadata-stage/candidate-lock.json research/candidate-metadata-stage/official.stdout
```

第二条输出规范锁字节后退出2，update_status=blocked；损坏输入只拒绝，不产生伪候选。原始输出文件不是网页版本文字。未修改历史报告；独立新[候选锁](../research/candidate-metadata-stage/candidate-lock.json)及[断点](../research/candidate-metadata-stage/checkpoint.json)保存本次进展。

下一断点：完整fork与候选Git历史缺失，merge-base/双向计数未实证，可信上游成员关系未本地验证，非上游SDM660/wayne补丁清单和携带策略未审。下一轮单独规划有界完整历史/补丁审计，不因tag存在或版本升高放行，不rebase/merge/cherry-pick。jasmine仅为需核对的历史源码参考，不作为wayne目标。

未改DTS/defconfig/boot/vendor/固件/init/fstab、4.19、DTB provenance及既有包，无编译/打包或真机测试，不宣称可刷、启动或硬件兼容。全部门禁保持。实时额度不可读取，64%/61%仅用户快照；保存同步后立即暂停。
