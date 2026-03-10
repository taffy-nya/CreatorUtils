#!/usr/bin/env python3
import argparse
import requests
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="基于 MiloraAPI 的 Manbo TTS 语音生成与下载脚本")
    parser.add_argument("text", type=str, help="需要转换为语音的文本")
    parser.add_argument("-f", "--format", type=str, default="mp3", help="音频格式 (默认: mp3，如 wav, m4a 等)")
    parser.add_argument("-o", "--output", type=str, help="指定保存的路径和文件名（可省略扩展名）")
    
    args = parser.parse_args()
    
    api_url = "https://api.milorapart.top/apis/mbAIsc"
    params = {
        "text": args.text,
        "format": args.format
    }
    
    print(f"正在请求生成语音: text='{args.text}', format='{args.format}'...")
    
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求 API 失败: {e}")
        sys.exit(1)
    except ValueError:
        print("解析 JSON 失败，API 返回的内容可能不是合法的 JSON")
        sys.exit(1)
        
    code = data.get("code")
    msg = data.get("msg", "无返回信息")
    
    if code == 200:
        download_url = data.get("url")
        if not download_url:
            print("错误: 接口返回成功，但没有找到音频下载 url")
            sys.exit(1)
            
        if args.output:
            base, ext = os.path.splitext(args.output)
            if not ext:
                filename = f"{args.output}.{args.format}"
            else:
                filename = args.output
        else:
            # 没有指定 -o 时，默认使用文本作为文件名，并替换掉可能导致文件名无效的字符
            safe_text = args.text.replace("/", "_").replace("\\", "_")
            filename = f"{safe_text}.{args.format}"

        output_dir = os.path.dirname(filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        print(f"{msg}")
        print(f"正在下载音频到: {filename} ...")
        
        try:
            audio_resp = requests.get(download_url, stream=True)
            audio_resp.raise_for_status()
            
            with open(filename, "wb") as f:
                for chunk in audio_resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print("下载完成")
        except requests.exceptions.RequestException as e:
            print(f"下载音频文件失败: {e}")
            sys.exit(1)
        except OSError as e:
            print(f"保存文件失败: {e}")
            sys.exit(1)
    else:
        print(f"请求失败 (Code: {code}): {msg}")

if __name__ == "__main__":
    main()