# wayne Power/Thermal材料短审计

时间：2026-10-10T04:37:02.594529-07:00；基线b954749。目标国行小米6X（wayne/SDM660）、原始静态分区；jasmine及Miku UI不作为目标基线。

做了什么：检查工作区、diff和最近结果，核验已保存非Miku比较样本文件哈希，新增Power/Thermal HAL、powerhint/thermal配置与实际sysfs绑定材料门禁。缺任一类别拒绝判断，绑定声明必须为布尔值。文件名仅是候选材料分类，自定义命名须真实清单复核，不验证HAL版本或配置语义。

发生了什么：两项正反例通过，实际样本按预期退出2。参考提取清单没有上述HAL/配置；对已选build.prop/init.qcom.rc的thermal/cpufreq/devfreq/powerhint检查没有匹配行。未提取或未匹配不代表完整vendor无文件/属性，也不是内核缺能力的证据。现有4.19历史嵌入配置不是实际生成.config或用户当前基线，6.6报告不提供已审计的Power/Thermal节点映射，无法证明具体接口矛盾。正例只开放材料门禁，性能/温控/续航/硬件及契约验证始终为false。

[证据](../research/power-thermal-stage/audit.json)保存清单与文本哈希；[断点](../research/power-thermal-stage/checkpoint.json)保存测试、预期拒绝及四项既有内核材料未变哈希；[时间戳记录](operations/power-thermal-2026-10-10.md)保存做了什么、结果与下一步。测试复现`python3 -m unittest discover -s tools -p test_power_thermal_contract.py -v`；`python3 tools/audit_power_thermal_contract.py`对当前样本预期退出2。

下一步先采集真实当前wayne材料。下列只读命令未执行，权限不足、无节点或命令缺失须保留原始错误：

```sh
adb shell getprop > wayne-power-thermal-properties.txt
adb shell 'ls -lZ /sys/class/thermal /sys/devices/system/cpu/cpufreq /sys/class/devfreq' > wayne-power-thermal-nodes.txt
adb shell 'find /vendor /odm -type f' > wayne-power-thermal-vendor-inventory.txt
adb shell lshal > wayne-power-thermal-hal-services.txt
adb shell dumpsys power > wayne-power-service.txt
adb shell dumpsys thermalservice > wayne-thermal-service.txt
adb shell logcat -b all -d > wayne-power-thermal-logcat.txt
adb shell dmesg > wayne-power-thermal-dmesg.txt
adb pull /sys/firmware/fdt wayne-current-fdt.dtb
```

依据实际清单再pull HAL、32/64位依赖、powerhint/thermal实际配置、init/VINTF并计算SHA256；按实际枚举路径核对zone type、CPU policy和devfreq driver绑定、配置所引用节点及DAC/SELinux/AVC。节点目录清单本身不证明频点或阈值，不猜编号、不写sysfs、不改变调度、不做负载测试。

4.19、6.6独立实验及现有实验包保留；未下载大供体、重编内核或生成刷机包。SELinux和实际驱动/DTB/运行日志仍缺证据，无真机测试，不宣称性能、温控、续航、启动或硬件验证。实时额度无法读取，61%/31%仅为用户快照，不声称精确控制。本轮同步后立即暂停。
