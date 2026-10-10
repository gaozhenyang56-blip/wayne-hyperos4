# wayne 音频接口短审计

时间：2026-10-09 21:58 America/Los_Angeles（2026-10-10 04:58 UTC）。基线0630572。目标：国行小米6X（wayne/SDM660）、原始静态分区；不是jasmine，与Miku UI无关。

做了什么：检查已有非Miku wayne比较样本的提取清单、build.prop和init.qcom.rc，校验提取文件SHA256；增加音频材料完整性fail-fast审计。已选文件缺少 primary audio HAL、mixer_paths 或 audio_platform_info 任一类别时，审计返回2。文件名分类只检查已选材料是否齐备，不验证HAL版本、ELF/XML语义或ALSA映射；自定义文件命名需要在取得真实清单后复核。未改任何内核、设备树、音频属性、节点或路由。

发生了什么：三项最小测试通过（完整模拟清单只开放材料门禁、不宣称兼容；属性/服务不能代替HAL与路由；缺少任一类别即拒绝）。实际已选样本三个类别均缺失，按预期返回2。这是“尚未提取”的证据，不是完整vendor缺文件或设备无音频的证据。

| 已有材料 | 可以得出的结论与边界 |
| --- | --- |
| 非Miku比较样本build.prop声明vendor.audio_hal.period_size=240、vendor.audio.feature.afe_proxy.enable=true、vendor.audio.feature.compr_voip.enable=true等 | 仅是样本用户空间期望；不能推出PCM端口、声卡编号、DSP/codec能力或用户当前属性 |
| init.qcom.rc有vendor.audio-hal服务，路径/vendor/bin/hw/android.hardware.audio.service，用户audioserver，以及audio等组和onrestart restart audioserver | 可以记录参考服务契约；服务二进制未提取，不能推出HAL版本或真实用户当前服务配置 |
| 同一init文本请求/sys/kernel/wdsp0/boot和/sys/kernel/wcd_cpe0/fw_name的权限，并创建/data/vendor/audio目录 | 仅为参考init请求，不能证明这些节点存在、必需或对应目标codec；未增加节点、权限或固件猜测 |
| 原4.19历史嵌入配置有CONFIG_SOUND/SND/SND_PCM/SND_SOC=y | provenance已明确不是实际构建.config，历史来源不是用户当前系统或项目基线；通用选项不能证明下游声卡/PCM/路由 |
| 已保存6.6构建报告明确下游音频ABI未验证，未记录经审计的声卡/PCM/codec映射 | 当前无法完成契约比对；未发现能由现有材料证明的具体映射矛盾，不推断支持或不支持 |

复现命令：

```sh
python3 -m unittest discover -s tools -p test_audio_contract.py -v
python3 tools/audit_audio_contract.py research/gpu-allocator-stage/lineage-wayne/selected-vendor research/gpu-allocator-stage/lineage-wayne/selected-files.json research/audio-contract-stage/audit.json
```

第二条对目前样本预期退出2。[审计证据](../research/audio-contract-stage/audit.json)保存属性/init行号与哈希；[内核证据](../research/audio-contract-stage/kernel-evidence.json)保留通用配置行及来源边界；[断点](../research/audio-contract-stage/checkpoint.json)保存结果和既有文件未改变的哈希。

下一步只先取证。下列只读命令未执行；不存在、无权限或工具缺失须保留原始错误，不填写推测值：

```sh
adb shell 'cat /proc/asound/cards; cat /proc/asound/pcm'
adb shell 'ls -lZ /dev/snd; ls -l /sys/class/sound'
adb shell getprop > wayne-current-properties.txt
adb shell 'find /vendor/etc /odm/etc -type f | grep -E "mixer_paths|audio_platform_info|audio_policy|audio.*rc|vintf"' > wayne-audio-config-paths.txt
adb shell 'find /vendor/lib /vendor/lib64 /vendor/bin/hw -type f | grep -E "audio|tinyalsa|acdb"' > wayne-audio-binary-paths.txt
adb shell lshal > wayne-current-hal-services.txt
adb shell dumpsys media.audio_flinger > wayne-audioflinger.txt
adb shell dumpsys media.audio_policy > wayne-audiopolicy.txt
adb shell logcat -b all -d > wayne-audio-logcat.txt
adb shell dmesg > wayne-audio-dmesg.txt
```

取得实际路径后再adb pull对应HAL、配置及传递依赖，保存SHA256、32/64位依赖、真实DTB与实际内核.config（如可读）。先依据/proc/asound和配置确定设备映射，再选只读mixer查询；本轮不猜card编号，不执行tinymix写入、播放、录音或通话测试。还需核对ALSA control/PCM/compress接口、DAC/SELinux和相关AVC、DSP启动与服务日志。

4.19方案、6.6实验和原有实验包保留；没有重编内核或生成刷机包。SELinux、显示/GPU、音频/通话、相机、加密和启动仍待验证，无真机测试，不宣称音频或硬件可用。无法读取实时额度，用户50%/39%仅为会话快照，不声称精确控制。本轮同步后暂停。
