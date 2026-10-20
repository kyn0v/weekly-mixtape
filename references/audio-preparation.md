# 音频准备模块边界

实现位于私有 submodule `modules/audio-preparer`，不是仅处理 NCM 的补丁。**所有输入**（包括 Intro、普通音频、已准备好的 WAV）均通过同一接口；公开层不识别或转换音频格式。

```python
prepare_audio(source: Path, output_dir: Path) -> PreparedAudio
```

公开类型在 `scripts/audio_contract.py`：`path`、`sample_rate`、`frame_count`、`channels`。私有模块导入这个类型，上层验证返回值；具体格式/位深及完整解码校验由私有实现负责。

- 输出：44.1 kHz、双声道、24-bit PCM WAV，准确时长为 `frame_count / sample_rate`。
- 兼容 WAV：验证后直接复制到任务输出目录，不重新编码。
- 其他来源：由实现按需提取/转换，不改变原文件、不做响度处理。
- 输出已存在：报错，不覆盖。失败不能发布未验证的正式文件。
- 没有私有模块时，仍可阅读公开流程、运行计划逻辑测试和检查歌单，但**不能执行真实音频准备**，普通 WAV 也不走旁路。

有权限的用户在公开仓库根目录运行：

```sh
git submodule update --init --recursive
```

或者第一次 `git clone --recurse-submodules <公开仓库地址>`。GitHub 上需要访问私有仓库的账号/SSH 权限，不把凭据写进代码或 URL。

`.gitmodules` 使用 `https://github.com/kyn0v/audio-preparer.git`。换机时配置本机 GitHub HTTPS 认证，例如 `gh auth login` 和 `gh auth setup-git`；不要把 Token 放进 URL。地址和固定提交 ID 是公开信息，源码仍由 private remote 的权限保护。

不要在私有模块缺失时自动下载替代解码器或现场重写实现。不要将 `modules/audio-preparer` 的内容复制进主仓库、文档或公开构建附件。
