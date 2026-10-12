# DTB采集声明与规范导出哈希绑定

时间：2026-10-11T18:52:46.842852-07:00；基线93bf21a。国行wayne/SDM660静态分区6.6实验；与Miku UI无关，不把sources.lock历史第三方来源作为用户当前设备认证。

做了什么：审阅sources.lock、既有板级导入、根身份及规范导出；新增tools/bind_dtb_provenance.py独立层。manifest schema为wayne.provenance-manifest.v1，固定十四个字段，全部必填且不得有其他字段：schema_version、evidence_role、capture_type、device、soc、collected_at、capture_command、capture_tool_version、container_name、container_sha256、dtb_offset、dtb_length、dtb_sha256、consumer_export_sha256。重复JSON键、NaN/Infinity、缺失/未知字段均拒绝；字符串须非空有效UTF-8且≤4096字节，unknown/n/a等占位拒绝；时间须ISO带明确时区。所有哈希严格64字符小写hex。

设备/SoC声明只接受wayne/sdm660。evidence_role为synthetic_not_device_evidence或actual_capture_claim，capture_type为synthetic_fixture/live_fdt/boot_slice/dtbo_slice；合成角色仅匹配合成类型。实际类型只是声明，不能证明硬件来源。原始容器/分区名称必须明确填写，不猜名称；live FDT可将实际采集文件作为容器、offset=0，必须记录真实对象而非套用示例。

整数严格拒绝bool/浮点，限制0..2^63-1；length还须1..8MiB并等于实际DTB字节长度，offset+length按上界检查溢出。manifest≤64KiB，提供的consumer export≤128MiB，可选容器≤256MiB，本小步过大的完整容器明确拒绝，不下载或猜测。所有API输入为不可变bytes，CLI有界读取。实际DTB/提供的导出哈希均核对，导出字节还须与93bf21a canonical_bytes(DTB)完全相同，原consumer schema/规范字节未改。

容器提供时核对整个原件SHA256、offset+length实际范围和切片与DTB的字节相等（同时由DTB哈希绑定），状态container_slice_verified；没有容器时仅manifest_claim_validated，容器哈希与offset保持声明，不能称为已核对。两种状态均固定physical_source_authenticated/build_gate_authorization/hardware_tested=false；不引入签名、证书、密钥或信任锚。没有实际国行采集物、不可变日志和可信来源链，不能宣称认证。

独立envelope schema为wayne.provenance-envelope.v1，包含原始manifest自身SHA256（包括原格式字节）、DTB/导出哈希、状态、有序manifest声明与固定false。相同全部输入产生相同UTF-8字节，固定键顺序与末尾换行、禁止非有限值；采集时间是manifest已有声明，不加入运行当前时间或绝对路径。格式改变会改变manifest哈希，这是精确原件绑定。文件发布复用原导出的同目录临时文件、fsync和Linux原子不覆盖rename；已有不同字节拒绝，同字节幂等接受，失败清理。原规范导出只重构公共写入内部函数，无schema改变。

发生了什么：四项新实际测试与原四十二项回归，共四十六项通过。覆盖完整合成容器切片、声明降级与字节稳定、DTB/export/container哈希篡改、canonical内容不符、offset/length范围与溢出、非法整数、未知字段/重复键/NaN/Infinity、jasmine/SoC错误、无时区、未知容器名称、已有不匹配拒绝和失败不写/清理。IO失败仅注入fsync异常，不mock解析结果。两个真实6.6 preflight仍退出2，五项旧材料哈希不变。

唯一新增manifest fixture provenance-synthetic.json及容器provenance-synthetic-container.bin均明确synthetic/not device evidence，由测试inputs()生成，不是虚构真机manifest。示例只读命令：

```sh
python3 tools/test_dtb_provenance.py
python3 tools/export_dtb_consumers.py tests/fixtures/wayne-evidence/consumer-positive.dtb --output /tmp/consumer-canonical.json
python3 tools/bind_dtb_provenance.py tests/fixtures/wayne-evidence/provenance-synthetic.json tests/fixtures/wayne-evidence/consumer-positive.dtb /tmp/consumer-canonical.json --container tests/fixtures/wayne-evidence/provenance-synthetic-container.bin
```

不提供容器则省略--container，只得声明验证状态。实际采集仍需保存真实命令/工具版本/带时区时间及原件/日志，核实真实容器对象再填offset/length和哈希；本轮没有采集或可信认证。旧来源清单和旧导入不充当信任锚。

[测试和断点](../research/dtb-provenance-stage/checkpoint.json)，[带时区记录](operations/dtb-provenance-2026-10-11.md)。下一步先取得真实采集物及不可变日志再单独审阅绑定范围；不构造认证链，不接构建放行或硬件分类。4.19、6.6与既有包保留，boot/ABI/固件缺口与DTB阻断不变；无固件/DTS/config/init/fstab修改、sysfs写入/remoteproc触发、下载、长编译或打包。无真机测试，不宣称来源认证、启动或硬件可用。实时额度不可读取，97%/66%仅用户快照；同步后立即暂停。
