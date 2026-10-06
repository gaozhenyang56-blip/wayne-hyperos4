# 镜像与最终成品

当前没有最终可刷机包。下载缓存和原始镜像保留在工作区，不作为 Git blob 上传。

最终成品产生后，使用仓库 Releases 发布；超过单资产限制时分卷，附重组命令。每次发布记录文件大小、SHA-256、对应源码提交、构建步骤、静态检查结果和“未真机测试”状态。

来源与分区校验见 `research/**/inspection.json`、`*.img.json`、`sources.lock.json`。第三方来源哈希与本地计算哈希应分别说明。

`project-history.bundle` 已公开保存，包含 API 同步前的四次本地提交历史；不包含大型 ROM 镜像。可用 `git clone project-history.bundle restored-history` 恢复。后续变化记录在本仓库 main 的提交历史中。
