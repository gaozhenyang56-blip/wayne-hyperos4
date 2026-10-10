# wayne 相机接口短审计

时间：2026-10-09T23:47:22.888135-07:00。基线5ad1636。目标仅为国行小米6X（wayne/SDM660）原始静态分区；不以jasmine或Miku UI为目标基线。

做了什么：核验现有非Miku wayne比较样本的提取文件哈希，检查build.prop与init.qcom.rc中的相机相关行，补齐材料完整性fail-fast检查。已选清单缺少camera.*.so候选HAL或相机XML候选配置时退出2。文件名仅作材料门禁，不验证ELF、配置语义或实际HAL版本；其他命名/非XML配置须取得真实清单后人工复核。未改相机属性、内核、设备树、节点、路由或固件。

发生了什么：三项最小测试通过，真实参考样本因两个类别均未提取按预期退出2。缺失仅指现有提取清单，不代表完整vendor没有文件或硬件不可用。未找到材料足够支持的具体用户空间/内核接口矛盾。

| 现有证据 | 可证明的内容及边界 |
| --- | --- |
| build.prop有persist.vendor.camera.HAL3.enabled=1、preview.ubwc=0、isp.clock.optmz=0、isp.turbo=1等 | 仅是参考样本属性期望；不能据此推出HAL版本、ISP能力、内存布局或用户当前配置 |
| init.qcom.rc设置persist.camera.gyro.disable并创建/data/vendor/camera | 仅是参考init请求；不能证明传感器、节点存在或服务加载成功 |
| 本次检查文本没有可核验的media/video/v4l-subdev节点映射，选定材料没有相机HAL/配置 | 实际节点要求、私有ioctl、32/64位传递依赖和媒体拓扑仍未知；不能假设只有标准V4L2接口 |
| 4.19历史嵌入配置声明MEDIA_SUPPORT、MEDIA_CAMERA_SUPPORT、MEDIA_CONTROLLER、VIDEO_DEV、VIDEO_V4L2_SUBDEV_API、MSM_CAMERA=y | 已有provenance明确这不是实际生成.config，也不是用户当前ROM基线；声明不能证明驱动、传感器或media graph生效 |
| 已保存6.6报告明确下游相机ABI未验证 | 没有已审计的media/video/subdev映射，不能证明与上述HAL兼容；本轮不补猜测配置 |

证据：[audit.json](../research/camera-contract-stage/audit.json)保留文本行号与哈希；[checkpoint.json](../research/camera-contract-stage/checkpoint.json)保留测试、退出码、历史配置行号和既有材料未变的哈希。原始测试输出见本轮[时间戳操作记录](operations/camera-contract-2026-10-09.md)。

复现：`python3 tools/verify_camera_stage.py`。仅运行三个离线测试、材料门禁和保留检查，不编译内核、不访问设备。门禁单独运行对当前样本预期退出2；验证脚本把该拒绝作为预期通过。

下一步先取得真实当前wayne材料。以下只读采集命令未执行；无权限、节点不存在、工具缺失都应保留原始错误，不填猜测值：

```sh
adb shell 'ls -lZ /dev/media* /dev/video* /dev/v4l-subdev*'
adb shell 'ls -l /sys/class/video4linux /sys/class/media'
adb shell getprop > wayne-camera-properties.txt
adb shell 'find /vendor/etc /odm/etc -type f' > wayne-vendor-config-inventory.txt
adb shell 'find /vendor/lib /vendor/lib64 /vendor/bin/hw -type f' > wayne-vendor-binary-inventory.txt
adb shell lshal > wayne-camera-hal-services.txt
adb shell dumpsys media.camera > wayne-camera-service.txt
adb shell logcat -b all -d > wayne-camera-logcat.txt
adb shell dmesg > wayne-camera-dmesg.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

依据实际清单再pull相机HAL、provider/init/VINTF、相机配置和32/64位传递依赖并计算SHA256；必须保留真实当前vendor来源。若设备已有media-ctl，可对实际枚举的media节点执行只读`media-ctl -p -d <实际节点>`；若已有v4l2-ctl，可执行`v4l2-ctl --list-devices`。本轮不指定节点编号，不安装工具、不设置格式/链路、不抓帧、不启动录像。需取得真实DTB及sensor/ISP/CSID/EEPROM关联证据、私有ioctl与DMA-BUF要求、节点DAC/SELinux和相关AVC、服务日志，再判断接口契约。

4.19方案、6.6独立实验和既有实验包保留；没有大下载、完整内核编译或生成可刷包。SELinux、显示/GPU、音频/通话、相机/录像、加密与启动仍有待核实项，无真机测试，不宣称硬件可用。本轮保存同步后暂停。实时额度无法读取，用户44%/38%仅为快照，不假称精确控制或已重置。
