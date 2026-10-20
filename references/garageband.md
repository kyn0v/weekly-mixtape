# GarageBand 操作要点

本 skill 是 agent 驱动的流程，不是无人值守的 GUI 宏。已实测创建新工程、导入 Intro、同轨两份歌曲及重新打开验证；每次仍须逐步检查当前界面。

## 准备
- 读取计划时，将 `project`/`wav` 的相对路径以 plan.json 所在目录为基准解析；`~/…` 先展开。不要把相对路径按当前工作目录解释，也不要把展开后的主目录写回计划。
- `swiftc scripts/ax.swift -o scripts/ax`（相对 skill 目录）；该 helper 支持局部树查询、属性/动作、点击、垂直移轨和剪贴板。无权限会报错，不自行修改系统权限。
- 先保存用户当前工程；通过 File → New 选择 Empty Project，将最初的 Mic or Line 音频轨命名 `Vocal` 并保持空白/监听关闭，Save As 到计划的绝对路径。Intro 和歌曲放在后续音轨，不把这个空轨当成临时轨删掉。拒绝任何覆盖提示。不要手写 GarageBand 私有工程格式。
- 在导入前设好工程长度；默认结束标记可能仅64秒，会把播放头定位钳制在结尾！可对 End Marker 用 `repeatAction PATH AXIncrement COUNT` 扩展，并读 `AXValueDescription` 验证；实测120 BPM时每次增加2秒。长项目可在空工程降低 BPM。关闭节拍器/循环，使用时间显示。
- 选择不带效果的立体声音频轨，监听关闭；音轨/主输出单位增益，声像居中，检查已有插件/发送。不要把 AX 滑杆的原始整数（例如130）误认为 dB。

## 窄范围检查
`ax dump '' 1` 找主窗口，再逐层找到 Tracks header、Tracks contents、Playhead Position。`ax dump PATH 2` 只读需要的子树；路径每次据当前界面重找，不能硬编码 `0.6…`，开关面板会改变它。轨道区域的 AXHelp 通常含开始/结束时分秒和毫秒，可用于验证。

每次鼠标操作前重新前置并等候：
```applescript
tell application "GarageBand" to activate
delay 0.7
```
过去观察到未前置时拖动可能没有效果；无论调用是否成功，都要读实际结果。

## 导入及排列
- 播放头时间显示的 AXValue 写入未必真正生效。可 doubleclick 当前 Playhead Position/时间字段，输入 `HHMMSSmmm`，回车，再读取四个时间字段核对。它可能量化到视频帧，不可仅凭输入值宣布精确。
- `ax fileClipboard /绝对路径/audio.wav` 然后在 GarageBand 粘贴可导入文件，通常自动新建轨道。helper 将文件URL和文件名列表直接写进剪贴板，避免进程退出后内容失效。必要时前置 Finder 再回 GarageBand 让文件剪贴板被识别。切勿在 Finder 中粘贴。设置时间后先点音轨标题空白处退出 LCD 输入焦点，再粘贴；逐次验证位置。
- 导入后检查片段的轨道和时间，而非默认粘贴到了选中轨。需要移轨时先让源/目标可见，用 `dragToTrack` 保持横坐标；移动后对比开始/结束时间。只删除已核实为空、由本次操作产生的临时轨道。
- Track → Rename Track 后，用 `setFocusedText` 和回车命名；若不是文本输入焦点就停止。
- 每首要两个独立**片段**，不能以 Loop 开关代替。实测可靠方法：再次导入同一 WAV 到临时音轨 → 打开 Edit → Alignment Guides → 将第二份拖到目标轨、吸附第一份结尾 → 核对两份时长和相邻边界完全一致 → 删除空临时轨。`dragBy PATH DX DY` 可按当前几何拖动，吸附后仍须读时间验证，不能仅凭像素位置。Intro 不复制。
- 普通区域复制/粘贴可能受文件剪贴板或当前选择影响，出现重新导入/原位覆盖；若尝试必须清除旧的文件URL并立即核对结果。不要反复盲试。两份可共用媒体，或由 GarageBand 复制两份相同 PCM 文件，无需重新压缩。
- 默认音轨及主输出的 Channel EQ 可能亮着，即使均衡曲线平直也应旁路。Smart Controls 的 `Bypass Channel EQ` AXValue=1 实测代表开关亮/效果启用，点灭到0；压缩/限幅/噪声门应关闭，Reverb/Ambience为0。新音频轨单位增益在本机滑杆原始值是173，不代表173dB。
- 保存后检查工程 `Media/Audio Files` 引用和实际文件；新旧音频若 GarageBand 改了封装，可比较解码 PCM，而非仅比较文件字节哈希。验证通过后记录到 `verification.json`。

遇到界面异常、时间错误或多出片段，停下来检查/撤销最近一步，勿无验证地重试整个批次。用户接管鼠标时暂停自动操作。
