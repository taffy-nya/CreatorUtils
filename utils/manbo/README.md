# manbo

基于 [MiloraAPI](https://api.milorapart.top/) 的 Manbo TTS 语音生成与下载命令行工具。

## 安装与依赖

工具依赖 `requests` 库发起网络请求。

```bash
pip install requests
```

## 使用说明

基本语法：

```bash
python manbo.py "要转换为语音的文本" [选项]
```

### 基础生成

默认生成 mp3 格式的文件，并以文本内容命名保存在当前目录：

```bash
python manbo.py "曼波曼波，哦马自立曼波"
```

### 指定格式

使用 `-f` 或 `--format` 参数指定输出的音频格式（默认为 mp3）：

```bash
python manbo.py "哈基米哈基米哈基米" -f wav
```

### 指定输出路径

使用 `-o` 或 `--output` 参数指定保存的具体路径和文件名。如果不包含扩展名，程序会自动追加指定的音频格式后缀：

```bash
# 保存到 ./audio/test.mp3
python manbo.py "南北路多" -o ./audio/test
```

## 参数列表

| 参数 | 说明 |
| --- | --- |
| `text` | 必填。需要转换为语音的文本内容。 |
| `-f`, `--format` | 可选。音频格式，如 mp3, wav, m4a 等。默认为 `mp3`。 |
| `-o`, `--output` | 可选。指定保存的路径和文件名。未指定时默认使用输入的文本命名。 |
