# weekly-mixtape

为播客 **《家庭自制》** 的制作准备工作而构建的 macOS agent skill：将每期选曲整理为 GarageBand 工程，预留人声录音轨，放入固定 Intro，并自动排列音乐素材，减少重复的手工操作。

收听《家庭自制》：
- [小宇宙](https://www.xiaoyuzhoufm.com/podcast/67dff6130ff066afdbb00285)
- [网易云音乐](https://music.163.com/djradio?id=1230534551)

## 节目歌单

- [每周更新的选曲歌单](https://music.163.com/playlist?id=17400667938)：本工作流的输入，按当次读取到的歌曲顺序准备工程。
- [节目历史歌曲汇总歌单](https://music.163.com/playlist?id=14238458166)：汇总节目中出现过的歌曲，供回顾与收听，不作为默认导入来源。

工作流程：每周选曲歌单 → 音频准备 → GarageBand 工程。公开仓库负责工作流、计划及界面编排；音频准备由私有 submodule 提供。

## 默认排列

1. **Vocal**：空白音频轨，留给后续录音，监听关闭。
2. **IntroTrack**：自带 `assets/Intro.mp3`，从零开始，只放一次。
3. 歌单每首独立一轨，连续放两份完整片段。

Intro 到第一首、不同歌曲之间空白 **60 秒**；同一首两份之间无空白。默认不做响度匹配、导出或上传。

## 模块划分

```text
scripts/audio_contract.py     # 公开接口与 PreparedAudio 类型
scripts/audio_backend.py      # 加载私有实现
scripts/prepare.py            # 歌单/文件清单、编号、重复和间隔计划
scripts/ax.swift              # GarageBand / 网易云界面辅助
modules/audio-preparer/       # 私有 submodule：识别、按需处理、验证音频
```

所有来源都调用 `prepare_audio(source, output_dir)`。返回文件路径、采样率、每声道帧数、声道数；输出为 44.1 kHz / 24-bit / stereo WAV。已兼容的 WAV 直接验证、复制，不重新编码。详见 [接口约定](references/audio-preparation.md)。

## 换机安装

主仓库：[kyn0v/weekly-mixtape](https://github.com/kyn0v/weekly-mixtape)（Public）。
音频模块：[kyn0v/audio-preparer](https://github.com/kyn0v/audio-preparer)（Private）。
先使用有权访问私有仓库的账号配置 GitHub HTTPS 认证，例如 `gh auth login` 后执行 `gh auth setup-git`，然后：

```sh
git clone --recurse-submodules https://github.com/kyn0v/weekly-mixtape.git
cd weekly-mixtape
swiftc scripts/ax.swift -o scripts/ax
```

如果主仓库已克隆：`git submodule update --init --recursive`。
`.gitmodules` 指向 `https://github.com/kyn0v/audio-preparer.git`，Git 使用本机配置的身份认证读取私有模块，不在 URL 中存放凭据。
**没有私有仓库权限也能阅读公开流程和运行公开测试，但不能执行真实音频准备。**

将 `~/.agents/skills/weekly-mixtape` 链接到本仓库即可安装；若该位置已有内容，先比较并备份到 skills 目录之外，不直接覆盖。
Pi 中新开会话或 `/reload` 后说「使用 weekly-mixtape 制作本周推荐」，或使用 `/skill:weekly-mixtape`。

## 环境与配置

完整流程需要 macOS、GarageBand、已登录的网易云客户端、Python 3.10+、Swift、FFmpeg/ffprobe；部分输入另需 OpenSSL。
辅助功能和截图权限须在新电脑重新允许，Git 克隆不会继承账号登录或系统权限。

- 下载目录：`~/Music/网易云音乐`；工程目录：`~/Music/GarageBand`。
- 只扫描数字名称的 `.band` 工程，最大编号加一，不覆盖。
- Intro：`assets/Intro.mp3`，也可通过 `--intro` 指定。
- `--root` / `--downloads` 可覆盖目录；新计划里的 `project`/`wav` 相对于 plan.json 所在目录。
- 目前歌单 ID 仍固定在 `SKILL.md` 和 `scripts/prepare.py`；尚未实现配置文件读取。

## 测试与维护

公开测试不依赖私有模块、真实音乐或 FFmpeg：

```sh
python3 -B scripts/test_public.py
```

初始化 submodule 后测试真实实现：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="scripts:modules/audio-preparer" \
  python3 -B -m unittest discover -s modules/audio-preparer/tests -v
```

修改私有模块后先在其仓库提交、推送，再更新公开仓库的 gitlink 指针并提交。发布时先推 private repo，再推 public repo。
GUI 操作仍由 agent 逐步检查，非无人值守宏；下载/导入期间不要抢占鼠标键盘。

## 隐私与发布

- 公开仓库只记录私有仓库地址和提交 ID，不包含私有文件内容；不要将递归检出的整个工作目录压缩公开。
- 固定歌单 ID、Intro 音频仍会随主仓库提交，公开前确认分享意愿和音频权限。
- 编译产物、缓存、工程、下载音乐及日志被忽略；报错、截图和历史运行产物并不自动脱敏。
- GitHub private/public 权限必须在创建远端时正确设置，不能由本地目录名称提供。
- 下载权限不等于公开传播授权；本仓库尚未选择开源许可证。
