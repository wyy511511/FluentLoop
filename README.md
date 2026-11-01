# Fluent Lab · 英语训练工作台

一套私人、本地优先的英语训练系统。无需账号、API key 或后端数据库。

## 30 秒启动

1. 解压整个项目，不要只打开 HTML 文件。
2. Mac：双击 `start.command`，如果 macOS 首次阻止运行，右键 → 打开。或者终端执行：
   ```bash
   cd ~/Downloads/fluent-lab
   ./start.command
   ```
3. 浏览器打开 `http://127.0.0.1:8765/`。如果你更喜欢手动启动，可在项目根目录运行：
   ```bash
   python3 -m http.server 8765 --bind 127.0.0.1
   ```
4. 允许浏览器访问麦克风，点击红色圆形按钮开始录音；再点一次结束，**记得点击「保存本次录音」**。

> 默认只监听 `127.0.0.1`，网页和音频不会自动上传。`http://localhost` 属于可使用麦克风的可信上下文。建议 Chrome；Safari 新版也支持录音，编码格式可能不同。不要使用隐身模式保存长期数据。

## 每天怎么用

| 环节 | 建议时间 | 方式 |
|---|---:|---|
| Grammar | 7 分钟 | 从昨天的原始口语里修正 3–5 个真实错误 |
| Chunks | 7 分钟 | 用中文触发句复习英文整句，再新增 3 个 |
| Compression writing | 5 分钟 | 同一观点写成 100 → 50 → 25 词 |
| Speaking | 8 分钟 | 90 秒英文即兴；不自我打断。保存原音频 |
| Reflection | 3 分钟 | 记录做得好、卡点、明天改进哪一件事 |

每次练习后，进入「练习档案」→「查看 / 复盘」：
- 保留**原始转写**（真实口误、重复和语法错误）；
- 粘贴 **Typeless / 人工润色稿**；
- 标记 A / B / C 与具体语法错误；
- 写出一条自然的英语表达；
- 如果有用，创建一个中文→英文的间隔复习卡片；
- 选填六维自评（非自动评分）。

「练习档案」支持按 **日期 / 训练目的** 分组和搜索；同一页底部还有**每日训练日记历史归档**，可回看和修改几天前的语法纠错、100/50/25 词写作和反思。音频随记录保存在浏览器 IndexedDB 中。可单独下载、导入系统录音或完整备份。

## 网页内快捷键

在网页内，按 **⌥(Option) + Shift + R**（Windows/Linux：Alt + Shift + R）开始/停止录音。这个组合避免与浏览器常见的硬刷新快捷键冲突；如果仍被其他软件占用，可以点击页面红色录音按钮。

## macOS：像 Typeless 一样，全局热键录音（可选）

普通网页**无法**注册跨应用的系统全局快捷键。因此项目附带 Hammerspoon + FFmpeg 的录音工作流，录音不要求浏览器保持打开。

### 先用 CLI 测试

你可以从本项目复制脚本，或者保留原路径直接运行：

```bash
brew install ffmpeg
./tools/quick-record.sh speaking    # 开始
./tools/quick-record.sh speaking    # 再执行一次停止并保存
```

默认文件结构：

```text
~/Documents/FluentLab/recordings/
  2026-10-27/
    speaking/
      2026-10-27_182301_speaking.m4a
    grammar/
      2026-10-27_184510_grammar.m4a
```

支持目的：`speaking`、`grammar`、`chunks`、`compression`、`interview`、`reflection`、`other`。可以通过 `FLUENT_LAB_RECORDINGS` 环境变量更改目录。脚本使用 Mac 默认音频输入设备。首次运行可能需要给予 Terminal / Hammerspoon 麦克风权限：系统设置 → 隐私与安全性 → 麦克风。如果命令失败，查看 `~/Documents/FluentLab/recordings/.last-recording.log`。

### 注册全局快捷键

1. 安装 [Hammerspoon](https://www.hammerspoon.org/)（例如 `brew install --cask hammerspoon`）。
2. 把整个解压目录移动到 **`~/FluentLab/`**，因此脚本路径变为 `~/FluentLab/tools/quick-record.sh`。或者手动修改下面 Lua 配置里的路径。
3. 把 `tools/hammerspoon-init.lua` 内容**追加**到 `~/.hammerspoon/init.lua`（已有配置时不要直接覆盖）。
4. 启动 Hammerspoon → Open Config → Reload Config；在系统设置中允许 Accessibility 权限。如果录音因为权限失败，也允许麦克风访问。

| 全局热键 | 作用 |
|---|---|
| ⌘⌥⇧R | 开始 / 停止 Speaking 录音 |
| ⌘⌥⇧G | 开始 / 停止 Grammar 录音 |
| ⌘⌥⇧C | 开始 / 停止 Compression 录音 |
| ⌘⌥⇧I | 开始 / 停止 Interview 录音 |

按下同一个快捷键两次就会停止并保存。停止时文件的绝对路径会复制到剪贴板。**注意**：全局快捷键会录音到 macOS 文件夹，网页不会在后台监控文件夹；需要通过网页的「导入外部录音」选择对应 `.m4a` 文件。文件名会自动提取日期与目的。也可以点击网页中的导入按钮，然后在 macOS 文件选择器按 **⌘ + Shift + G**，粘贴目录路径直达文件夹。

### 可选：使用现有 whisper.cpp 本地转录

如果你已经配置好了 `whisper-cli` 与模型：

```bash
./tools/transcribe-local.sh ~/Documents/FluentLab/recordings/2026-10-27/speaking/example.m4a
```

它会在音频旁边生成同名 `.txt`，可以把未经润色的文本粘贴进练习档案。默认模型在 `~/whisper.cpp/models/ggml-medium.en.bin`，也可设置 `WHISPER_MODEL` 指向现有模型。**这是可选的，网页本身不调用 Whisper，也不会自动转录。**

## 数据存储、备份、隐私

- 训练日志、短语卡片、录音 Blob 都保存在**当前浏览器配置文件**的 IndexedDB。
- 没有用户账号，也没有云同步，切换浏览器/设备后不自动迁移。
- 建议每周在「数据和设置」导出一次**含录音的完整 JSON 备份**。这个文件可能很大，且包含私人录音内容，请安全保管。
- 「轻量 JSON」不包含录音。用它恢复时不会恢复音频，也不会假装音频仍然存在。
- CSV 可导出文本、日期、目的、错误标签、评分等，但不包含音频。
- 重新导入备份会替换现有记录，请先备份。关闭网页不会删除数据；清除浏览器站点数据会。
- 软件不含 AI 评分，所有分数都是**手动自评**；不会根据 Typeless 润色稿推断口语水平。
- 如果忘记保存浏览器录音，刷新页面将丢失该段未保存的临时音频。

## 文件构成

```text
fluent-lab/
  index.html                 # 完整的前端，CSS/JS 内置；无 CDN 依赖
  start.command              # 一键启动 127.0.0.1 本地服务器
  tools/
    quick-record.sh          # FFmpeg 录音开关、日期/目的归档
    hammerspoon-init.lua     # 全局快捷键映射
    transcribe-local.sh      # 可选 whisper.cpp 离线转录
  README.md
```
