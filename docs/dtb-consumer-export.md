# DTB消费者证据确定性JSON导出

时间：2026-10-11T17:31:10.231581-07:00；基线d50c23a。仅国行wayne/SDM660静态分区6.6实验，与Miku UI无关；输入身份字符串不是实际设备来源认证。

做了什么：新增tools/export_dtb_consumers.py。canonical_bytes(bytes)先复用根身份API验证同一不可变快照：model规范化后必须Mi 6X或Xiaomi Mi 6X，compatible严格为xiaomi,wayne与qcom,sdm660两项且无重复/额外项。缺失、畸形、jasmine或其他根身份拒绝，消费者全部成功才序列化。所有重复树读取均来自同一bytes，不重新读取路径，不修改原身份API。

规范负载固定schema_version=wayne.consumer-evidence.v1、tool_version=export-dtb-consumers/1，保留输入SHA256、根model/compatible原始小写hex、token/value绝对偏移/长度及解码值，冻结consumer字段与有序target/edge/reg证据。使用UTF-8、固定插入键顺序、原数组顺序、紧凑分隔符、唯一末尾换行，bytes均编码小写hex，allow_nan=false；没有时间戳、绝对输入路径、随机值或状态判断。可选缺失保持presence=absent、raw/offset=null、strings=[]。函数返回不可变bytes，全部嵌套集合成为规范JSON数组；schema变化须升版本。

physical_source_authenticated/build_gate_authorization/hardware_tested固定false。根标签可以人为伪造；没有真实国行采集链与板级证据就不能宣称源自实物或解锁构建。没有分类remoteproc、推断启用状态、固件可用性、GLINK/RPMSG/SMEM或其他provider引用。

文件输出先在内存完成全部验证和序列化。同目录临时文件写入、flush/fsync后使用Linux renameat2(RENAME_NOREPLACE)原子发布，避免并发出现目标时静默覆盖；工具/系统不支持明确失败，不回退到覆盖rename。既有输出仅当字节完全一致时接受，不同SHA或任何其他字节不匹配均拒绝，比只检查SHA更严格。异常清理临时文件；不会修改已有不匹配或symlink文件。保证的是原子可见与不覆盖，不宣称目录元数据已fsync或掉电耐久。stdout模式只在成功后写同一规范字节。

为防止重复引用把reg展开成无界巨大JSON，追加262144个累计展开reg元组上限，序列化前拒绝。实际二进制额外检查用65536条重复引用与每目标5个reg元组触发该保护；不mock限额或解析结果。

发生了什么：五项新导出测试与原三十七项回归，共四十二项通过。覆盖合法wayne/字节重复稳定/固定schema键和值、消费者顺序、多个reg/absent、stdout与文件相同、幂等、jasmine/其他身份/缺失或畸形身份拒绝、消费者失败无新输出且既有文件保留、不匹配文件拒绝、并发目标存在时真实原子拒绝。临时写入fsync和发布失败测试仅注入IO异常，验证清理，不mock身份或解析结果。两个真实6.6 preflight仍退出2，五项保留材料哈希不变。

可直接执行（fixture明确是合成输入，不是实际wayne证据）：

```sh
python3 tools/test_dtb_export.py
python3 tools/export_dtb_consumers.py tests/fixtures/wayne-evidence/consumer-positive.dtb
python3 tools/export_dtb_consumers.py tests/fixtures/wayne-evidence/consumer-positive.dtb --output /tmp/consumer-evidence.json
python3 tools/ci_kernel_66_probe.py --preflight
python3 tools/ci_allocator_implementation.py --preflight
```

规范schema采用项目明确的稳定序列化格式，不声称实现RFC 8785。API/file导出仅绑定输入哈希和标签一致性，未接入现有清单来源认证；实际采集来源、带时区时间、采集命令可另存非规范运行记录，不能以清单声明代替实物核实。

[实际结果与断点](../research/dtb-export-stage/checkpoint.json)，[带时区记录](operations/dtb-export-2026-10-11.md)。下一步单独审阅真实采集清单/来源链与导出哈希绑定，不接构建放行。4.19、6.6成果和实验包保留，不改固件/DTS/config/init/fstab、不写sysfs或触发remoteproc，无下载、长编译、打包或真机测试。boot/ABI/固件缺口与DTB阻断保持，不宣称硬件或启动验证。实时额度不可读，50%/68%仅用户快照；同步后立即暂停。
