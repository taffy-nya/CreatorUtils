# bilidown

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 的 Bilibili 视频下载命令行工具。支持扫码登录、指定分P下载、指定时间片段裁剪以及指定内容下载

## 安装与依赖

工具依赖 `yt-dlp` 进行下载，且推荐安装 `qrcode` 以便在终端直接显示登录二维码

```bash
pip install yt-dlp qrcode
```

## 使用说明

基本语法：

```bash
python bilidown.py [bvid] [选项]
python bilidown.py --login
```

### 登录

使用前建议先进行登录以获取更高画质（否则可能受限于 480p）：

```bash
python bilidown.py --login
```

根据终端提示，使用手机 B 站客户端扫描二维码。登录状态将自动保存在脚本所在目录下的 `bilibili_cookies.txt` 文件中

### 示例

#### 基础下载

下载默认最高画质的视频：

```bash
python bilidown.py BV1EF3uzeETo
# 或
python bilidown.py https://www.bilibili.com/video/BV1EF3uzeETo
```

#### 指定下载内容

使用 `-m` 参数（默认 `v` 代表视频，`a` 代表音频，`c` 代表封面）：

```bash
# 同时下载视频和音频（分离），以及封面
python bilidown.py BV1EF3uzeETo -m vac

# 仅提取音频
python bilidown.py BV1EF3uzeETo -m a
```

#### 分 P 下载

对于包含多个 P 的视频，可以通过 `-p` 指定下载部分（支持单个或区间）：

```bash
python bilidown.py BV1EF3uzeETo -p 1
python bilidown.py BV1EF3uzeETo -p 1,3,5-7
```

#### 片段截取

直接截取视频中的一段进行下载：

```bash
# 下载 1:30-3:00 的片段
python bilidown.py BV1EF3uzeETo -r 1:30-3:00

# 下载从 1:23 开始的片段，直到视频结尾
python bilidown.py BV1EF3uzeETo --start 1:23

# 下载从视频开始到 18:83 的片段
python bilidown.py BV1EF3uzeETo --end 18:83
```

#### 输出文件设置

```bash
# 保存到 ./download 目录
python bilidown.py BV1EF3uzeETo -d ./download

# 保存到当前目录并命名为 "自定义视频名_BV1EF3uzeETo.mp4"
python bilidown.py BV1EF3uzeETo -n "自定义视频名"

# 保存为 "BV1EF3uzeETo_自定义视频名.mp4"
python bilidown.py BV1EF3uzeETo -t "{bvid}_{title}"

# 直接指定输出文件（将忽略文件夹或模板设定）
python bilidown.py BV1EF3uzeETo -o ./clip.mp4
```

## 参数列表

| 参数 | 说明 |
| --- | --- |
| `url` | 视频链接或 BV 号，支持 b23.tv 短链接 |
| `-o`, `--output` | 完整输出路径（会覆盖 `-d` 和 `-n` 参数） |
| `-d`, `--dir` | 输出目录，默认为当前目录 |
| `-n`, `--name` | 自定义名称（替换模板中的 `{title}`） |
| `-t`, `--template` | 文件名模板，默认为 `{title}_{bvid}` |
| `-m`, `--mode` | 下载模式，`v`=视频, `a`=音频, `c`=封面，可组合，默认为 `v` |
| `-p`, `--parts` | 分P选择（如 `1` 或 `1,3,5-7`） |
| `-r`, `--range` | 时间片段区间（如 `1:30-3:00`） |
| `--start` | 片段起始时间 |
| `--end` | 片段结束时间 |
| `--login` | 仅执行扫码登录流程（不触发下载） |
