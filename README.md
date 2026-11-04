# Fluent Lab · 英语训练工作台

[English documentation](README.en.md) · 中文

一套私人、本地优先的英语训练系统。无需账号、API key、SQLite 或云端数据库；每次练习都保存成可以直接打开的本地文件。

## 30 秒启动

1. 解压整个项目，不要只打开 HTML 文件。
2. Mac：双击 `start.command`，如果 macOS 首次阻止运行，右键 → 打开。或者终端执行：
   ```bash
   cd ~/Downloads/fluent-lab
   ./start.command
   ```
3. 浏览器打开 `http://127.0.0.1:8765/`。如果你更喜欢手动启动，可在项目根目录运行：
   ```bash
   python3 server.py
   ```
4. 允许浏览器访问麦克风，点击红色圆形按钮开始录音；再点一次结束，**记得点击「保存本次录音」**。保存成功后，页面会显示“文件已归档”。

> 必须通过 `start.command` 或 `python3 server.py` 启动。直接双击 `index.html` 或使用普通 `python3 -m http.server` 时，浏览器不能把文件写进 `recordings/`。默认只监听 `127.0.0.1`，网页和音频不会自动上传。

## recordings 就是数据库

网页保存的每条练习都会落到项目里的 `recordings/`，例如：

```text
recordings/
  index.json
  2026-11-01/
    1793560000000-abcd1234/
      media.webm          # 也可能是 media.m4a / media.mp4 / media.wav
      before.txt          # Muse / Whisper 原始 ASR
      after.txt           # Typeless / 人工纠正稿
      prompt.txt
      corrections.md      # 错误标签、主要问题、自然表达、下一步、自评
      session.json        # 完整结构化元数据
```

这些文件就是长期主档案，可以直接打开、搜索、复制或用 Time Machine 备份。浏览器 IndexedDB 仍会保留一份快速缓存；清掉浏览器缓存后，重新启动 Fluent Lab 会从 `recordings/` 恢复练习列表和文本。删除一条练习时，磁盘目录会先移到 `recordings/.trash/`，不会马上永久抹掉。

## 无限层级重复练习

在「练习档案」的任何一条记录下面点击 **↻ 再练一次**：

1. 系统会把原题目、训练目的和标题带回录音区，并标记“第 2 次 / 第 3 次 / …”。
2. 录音或导入媒体并保存后，新记录会显示在上一条练习下面。
3. 可以继续对任意子记录点击“再练一次”，层级和次数都没有上限。
4. 每一次都有独立的媒体、`before.txt`、`after.txt`、`corrections.md` 和 `session.json`。

父子关系保存在 `session.json` 的 `parentId`、`rootId`、`takeNumber` 和 `repeatDepth` 中；`recordings/index.json` 和 CSV 导出也包含这些关系。旧记录不需要迁移，默认视为第 1 次。删除父记录会把整棵子练习树一起移到 `.trash/`，避免留下断开的记录。

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

「练习档案」支持按 **日期 / 训练目的** 分组和搜索；同一页底部还有**每日训练日记历史归档**。录音和每次练习的 Before / After / 纠正复盘保存在 `recordings/`，并同时缓存到浏览器。

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

默认写入当前项目的 `recordings/`，文件结构与网页录音一致：

```text
fluent-lab/recordings/
  2026-10-27/
    2026-10-27_182301_speaking/
      media.m4a
      before.txt
      after.txt
      corrections.md
      session.json
```

支持目的：`speaking`、`grammar`、`chunks`、`compression`、`interview`、`reflection`、`other`。可以通过 `FLUENT_LAB_RECORDINGS` 环境变量更改目录。脚本使用 Mac 默认音频输入设备。首次运行可能需要给予 Terminal / Hammerspoon 麦克风权限：系统设置 → 隐私与安全性 → 麦克风。如果命令失败，查看 `recordings/.last-recording.log`。

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

按下同一个快捷键两次就会停止并保存。停止时文件的绝对路径会复制到剪贴板。全局快捷键和网页现在使用同一种档案结构；停止后刷新 / 重新打开网页，就会自动看到这条录音，不需要再手动导入。

### 可选：使用现有 whisper.cpp 本地转录

如果你已经配置好了 `whisper-cli` 与模型：

```bash
./tools/transcribe-local.sh ./recordings/2026-10-27/2026-10-27_182301_speaking/media.m4a
```

默认模型是你本机已有的 `~/whisper.cpp/models/ggml-medium.en.bin`，并调用 PATH 里的 `whisper-cli`。如果输入是某个练习目录里的 `media.*`，结果会直接写入同目录的 `before.txt`；刷新网页即可看到。其他文件仍生成同名 `.txt`。也可设置 `WHISPER_MODEL` 指向别的模型。**这是可选的，网页本身不会自动调用 Whisper；用 Muse 拖入媒体获得 ASR 后，直接粘贴到 Before 也可以。**

## 数据存储、备份、隐私

- 每次练习的媒体、Before、After 和纠正复盘保存在项目的 `recordings/`；浏览器 IndexedDB 是快速缓存。
- 没有用户账号，也没有云同步。复制整个项目（尤其是 `recordings/`）即可迁移。
- `recordings/` 已被 `.gitignore` 忽略，不会随 Git commit 备份。建议用 Time Machine、加密硬盘或可信网盘备份。
- 也可以在「数据和设置」导出**含浏览器内录音的完整 JSON 备份**。这个文件可能很大且含私人录音，请安全保管。
- 「轻量 JSON」不包含录音。用它恢复时不会恢复音频，也不会假装音频仍然存在。
- CSV 可导出文本、日期、目的、错误标签、评分等，但不包含音频。
- 重新导入 JSON 会替换浏览器缓存；不会自动删除已有的 `recordings/` 文件。
- 软件不含 AI 评分，所有分数都是**手动自评**；不会根据 Typeless 润色稿推断口语水平。
- 如果忘记保存浏览器录音，刷新页面将丢失该段未保存的临时音频。

## 文件构成

```text
fluent-lab/
  index.html                 # 完整的前端，CSS/JS 内置；无 CDN 依赖
  server.py                  # 本地网页 + recordings 文件档案 API
  start.command              # 一键启动 127.0.0.1 本地服务
  recordings/                # 实际录音与每次练习的文本档案（Git 忽略）
  tools/
    quick-record.sh          # FFmpeg 录音开关、日期/目的归档
    hammerspoon-init.lua     # 全局快捷键映射
    transcribe-local.sh      # 可选 whisper.cpp 离线转录
  README.md
  README.en.md               # English documentation
```
