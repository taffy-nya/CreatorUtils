#!/usr/bin/env python3
"""
基于 yt-dlp 的 bilibili 视频下载工具, 支持扫码登录

登录状态 (bilibili_cookies.txt) 保存在脚本所在目录

用法:
    bilidown.py URL [-o PATH] [-d DIR] [-n NAME] [-t TPL] [-m MODE]
                    [-p PARTS] [-r RANGE] [--start TIME] [--end TIME]
    bilidown.py --login
"""

import argparse
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES = os.path.join(SCRIPT_DIR, "bilibili_cookies.txt")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
BILI_HEADERS = {"User-Agent": UA, "Referer": "https://www.bilibili.com"}


# ─── HTTP ────────────────────────────────────────────────────────────────────


def _get_json(url, jar=None):
    """发送 GET 请求, 返回解析后的 JSON."""
    handlers = [urllib.request.HTTPCookieProcessor(jar)] if jar else []
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers=BILI_HEADERS)
    with opener.open(req) as r:
        return json.loads(r.read().decode())


# ─── Cookies ─────────────────────────────────────────────────────────────────


def _new_jar():
    return http.cookiejar.MozillaCookieJar(COOKIES)


def _load_jar():
    jar = _new_jar()
    if os.path.exists(COOKIES):
        jar.load(ignore_discard=True, ignore_expires=True)
    return jar


def _set_cookie(jar, name, value):
    """向 cookie jar 中写入一条 .bilibili.com 的 cookie"""
    jar.set_cookie(http.cookiejar.Cookie(
        0, name, value, None, False,
        ".bilibili.com", True, True,
        "/", True, False,
        int(time.time()) + 86400 * 180, False,
        None, None, {}, False,
    ))


# ─── 登录 ────────────────────────────────────────────────────────────────────


def check_login(jar=None):
    """检查登录状态, 返回 (是否已登录, 用户名)."""
    jar = jar or _load_jar()
    try:
        d = _get_json("https://api.bilibili.com/x/web-interface/nav", jar)
        if d["code"] == 0:
            return True, d["data"]["uname"]
    except Exception:
        pass
    return False, None


def qr_login():
    """交互式扫码登录, 成功返回 cookie jar, 失败返回 None"""
    d = _get_json(
        "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    )
    if d["code"] != 0:
        print(f"获取二维码失败: {d['message']}")
        return None

    qr_url, qr_key = d["data"]["url"], d["data"]["qrcode_key"]

    # 在终端显示二维码
    try:
        import qrcode

        q = qrcode.QRCode(box_size=1, border=1)
        q.add_data(qr_url)
        q.make(fit=True)
        q.print_ascii(invert=True)
    except ImportError:
        print("[提示] pip install qrcode 可在终端直接显示二维码")
        print(f"二维码链接: {qr_url}")

    print("请使用 bilibili 客户端扫码 ...")

    jar = _new_jar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    while True:
        time.sleep(2)
        req = urllib.request.Request(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
            f"?qrcode_key={qr_key}",
            headers=BILI_HEADERS,
        )
        with opener.open(req) as r:
            res = json.loads(r.read().decode())

        status = res["data"]["code"]
        if status == 0:
            # 保存 cookies
            jar.save(ignore_discard=True, ignore_expires=True)
            ok, uname = check_login(jar)
            if ok:
                print(f"登录成功: {uname}")
                return jar
            # 兜底: 从重定向 URL 中提取 cookies
            redir = res["data"].get("url", "")
            if redir:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(redir).query)
                for k in ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5"):
                    if k in qs:
                        _set_cookie(jar, k, qs[k][0])
                jar.save(ignore_discard=True, ignore_expires=True)
                ok, uname = check_login(jar)
                if ok:
                    print(f"登录成功: {uname}")
                    return jar
            print("登录响应正常但未能保存 cookies")
            return None
        elif status == 86038:
            print("二维码已过期")
            return None
        elif status == 86090:
            print("已扫码, 请在手机上确认 ...")


def ensure_login():
    """下载前检查登录状态, 返回 cookie jar"""
    jar = _load_jar()
    ok, uname = check_login(jar)
    if ok:
        print(f"[已登录] {uname}")
        return jar

    print("未登录或登录已过期.")
    while True:
        try:
            s = input("[Enter] 扫码登录 | [s] 跳过登录 | Ctrl+C 退出: ").strip().lower()
        except KeyboardInterrupt:
            print()
            sys.exit(0)
        if s == "":
            result = qr_login()
            if result is not None:
                return result
        elif s == "s":
            print("跳过登录, 画质可能受限 (480p)")
            return jar


# ─── 视频信息 ─────────────────────────────────────────────────────────────────


def _resolve_short_url(url):
    """跟随短链接重定向 (如 b23.tv)"""
    try:
        req = urllib.request.Request(url, headers=BILI_HEADERS)
        with urllib.request.urlopen(req) as r:
            return r.url
    except Exception:
        return url


def parse_input(raw):
    """从 URL 或 BV 号字符串中提取 (bvid, 分P号 | None)"""
    m = re.search(r"(BV[\w]+)", raw)
    if not m and raw.startswith("http"):
        raw = _resolve_short_url(raw)
        m = re.search(r"(BV[\w]+)", raw)
    if not m:
        return None, None
    bvid = m.group(1)
    pm = re.search(r"[?&]p=(\d+)", raw)
    return bvid, int(pm.group(1)) if pm else None


def fetch_info(bvid, jar):
    """从 bilibili API 获取视频信息"""
    d = _get_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", jar)
    if d["code"] != 0:
        sys.exit(f"API 错误: {d['message']}")
    return d["data"]


# ─── 命名 ────────────────────────────────────────────────────────────────────


_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize(s):
    return _UNSAFE.sub("_", s).strip()


def resolve_path(args, info, part=None):
    """
    生成输出文件基础路径 (不含扩展名)
    优先级: -o > -d + 模板 (-n / -t)
    yt-dlp 会自动追加正确的扩展名
    """
    if args.output:
        return os.path.splitext(args.output)[0]

    title = args.name or info["title"]
    tpl = args.template

    # 多分P下载时自动追加分P号
    if part is not None and "{p}" not in tpl:
        tpl += "_P{p}"

    name = tpl.replace("{title}", title).replace("{bvid}", info["bvid"])
    if part is not None:
        name = name.replace("{p}", str(part))
    else:
        name = re.sub(r"_?P?\{p\}", "", name)

    return os.path.join(args.dir, _sanitize(name))


# ─── 解析辅助 ────────────────────────────────────────────────────────────────


def parse_time(s):
    """将时间字符串 (SS / MM:SS / HH:MM:SS) 解析为秒数"""
    if not s:
        return None
    parts = list(map(float, s.strip().split(":")))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def parse_parts(s):
    """将分P规格 (如 '1,3,5-7') 解析为排序后的整数列表"""
    result = []
    for seg in s.split(","):
        seg = seg.strip()
        if "-" in seg:
            a, b = seg.split("-", 1)
            result.extend(range(int(a), int(b) + 1))
        else:
            result.append(int(seg))
    return sorted(set(result))


# ─── 下载 ────────────────────────────────────────────────────────────────────


def dl_media(url, base_path, mode, start=None, end=None):
    """
    通过 yt-dlp 下载视频或音频
    base_path: 不含扩展名的输出路径
    mode: 'v' 视频 (mp4), 'a' 音频 (m4a)
    """
    if yt_dlp is None:
        sys.exit("需要 yt-dlp: pip install yt-dlp")

    opts = {
        "outtmpl": base_path + ".%(ext)s",
        "force_keyframes_at_cuts": True,
        "noplaylist": True,
    }
    if os.path.exists(COOKIES):
        opts["cookiefile"] = COOKIES

    if mode == "a":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}
        ]
        ext_hint = "m4a"
    else:
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"
        ext_hint = "mp4"

    if start is not None or end is not None:
        rng = {}
        if start is not None:
            rng["start_time"] = start
        if end is not None:
            rng["end_time"] = end
        opts["download_ranges"] = lambda info, ydl, r=rng: [r]

    print(f"  正在下载: {os.path.basename(base_path)}.{ext_hint}")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"  下载失败: {e}")
        return 1
    return 0


def dl_cover(info, base_path):
    """下载视频封面. base_path 为不含扩展名的路径"""
    pic = info.get("pic", "")
    if not pic:
        print("  无封面可下载")
        return
    if pic.startswith("//"):
        pic = "https:" + pic

    url_path = urllib.parse.urlparse(pic).path
    ext = os.path.splitext(url_path)[1] or ".jpg"
    path = base_path + ext

    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)

    req = urllib.request.Request(pic, headers=BILI_HEADERS)
    with urllib.request.urlopen(req) as r, open(path, "wb") as f:
        f.write(r.read())
    print(f"  封面已保存: {os.path.basename(path)}")


# ─── CLI ───────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(
        description="基于 yt-dlp 的 bilibili 下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "模板变量:\n"
            "  {title}  视频标题 (或 -n 指定的自定义名称)\n"
            "  {bvid}   BV 号\n"
            "  {p}      分P号 (多分P时自动追加)\n"
            "\n"
            "示例:\n"
            "  %(prog)s BV1xx4y1x7xx\n"
            "  %(prog)s https://bilibili.com/video/BV1xx -m va\n"
            '  %(prog)s BV1xx -p 1,3-5 -t "{title}_{bvid}"\n'
            "  %(prog)s BV1xx -r 1:00-3:00\n"
            "  %(prog)s BV1xx -d ./download -m vac\n"
            "  %(prog)s BV1xx -o ./clip\n"
            "  %(prog)s --login\n"
        ),
    )
    ap.add_argument("url", nargs="?", help="视频链接或 BV 号")
    ap.add_argument("-o", "--output", help="完整输出路径 (会覆盖 -d -n)")
    ap.add_argument("-d", "--dir", default=".", help="输出目录 (默认: 当前目录)")
    ap.add_argument("-n", "--name", help="自定义名称 (替换模板中的 {title})")
    ap.add_argument(
        "-t", "--template", default="{title}_{bvid}",
        help='文件名模板 (默认: "{title}_{bvid}")',
    )
    ap.add_argument(
        "-m", "--mode", default="v",
        help="下载模式: v=视频 a=音频 c=封面, 可组合 (默认: v)",
    )
    ap.add_argument("-p", "--parts", help="分P选择 (如 1 或 1,3,5-7)")
    ap.add_argument("-r", "--range", help="时间区间 (如 1:30-3:00 或 12:23-01:23:34)")
    ap.add_argument("--start", help="起始时间, 省略则从头开始 (如 1:30)")
    ap.add_argument("--end", help="结束时间, 省略则到末尾 (如 3:00)")
    ap.add_argument("--login", action="store_true", help="仅扫码登录 (不下载)")

    args = ap.parse_args()

    # 仅扫码登录
    if args.login:
        qr_login()
        return

    if not args.url:
        ap.print_help()
        sys.exit(1)

    # 下载前检查登录
    jar = ensure_login()

    # 解析视频
    bvid, url_page = parse_input(args.url)
    if not bvid:
        sys.exit(f"无法从输入中提取 BV 号: {args.url}")

    info = fetch_info(bvid, jar)
    pages = info.get("pages", [])
    total = len(pages)
    print(f"[{bvid}] {info['title']} ({total}P)")

    # 确定分P列表
    if args.parts:
        plist = parse_parts(args.parts)
    elif url_page:
        plist = [url_page]
    elif total > 1:
        print("  多分P视频, 默认下载 P1. 使用 -p 选择分P")
        plist = [1]
    else:
        plist = [None]  # 单P不追加后缀

    # 校验分P号
    for p in plist:
        if p is not None and (p < 1 or p > total):
            sys.exit(f"分P {p} 超出范围 (1-{total})")

    has_time = args.range or args.start or args.end
    if len(plist) > 1 and has_time:
        sys.exit("下载多个分P时不能指定时间区间")

    if args.output and len(plist) > 1:
        sys.exit("-o 不能用于多分P下载, 请使用 -d/-n/-t 代替")

    # 解析选项
    # -r 优先; --start/--end 可单独使用 (省略的一端不限制)
    if args.range:
        if "-" not in args.range:
            sys.exit("-r 格式错误, 应为 '起始-结束' (如 1:30-3:00)")
        s_str, e_str = args.range.split("-", 1)
        t0 = parse_time(s_str.strip())
        t1 = parse_time(e_str.strip())
        if t0 is None or t1 is None:
            sys.exit("-r 格式错误, 应为 '起始-结束' (如 1:30-3:00)")
    else:
        t0 = parse_time(args.start)
        t1 = parse_time(args.end)

    mode = args.mode.lower()
    want_v, want_a, want_c = "v" in mode, "a" in mode, "c" in mode
    if not (want_v or want_a or want_c):
        want_v = True

    if yt_dlp is None and (want_v or want_a):
        sys.exit("下载媒体需要 yt-dlp: pip install yt-dlp")

    os.makedirs(args.dir, exist_ok=True)

    if want_c:
        base = resolve_path(args, info)
        dl_cover(info, base)

    url_base = f"https://www.bilibili.com/video/{bvid}"
    for pn in plist:
        url = f"{url_base}?p={pn}" if pn else url_base
        if pn and pages:
            print(f"\n[P{pn}] {pages[pn - 1].get('part', '')}")
        base = resolve_path(args, info, pn)
        if want_v:
            dl_media(url, base, "v", t0, t1)
        if want_a:
            dl_media(url, base, "a", t0, t1)

    print("\n下载完成")


if __name__ == "__main__":
    main()
