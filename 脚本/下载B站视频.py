import os
import subprocess

def download_bilibili_video(bvid, download_dir= './datas'):
    """
    使用you-get下载B站视频
    :param bvid: 视频的BV号，例如 "BV1GJ411x7h7"
    """
    # 构造视频的完整URL
    url = f"https://www.bilibili.com/video/{bvid}"
    
    # 如果下载目录不存在，则创建它
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    try:
        # 使用subprocess调用you-get命令
        # -o 参数指定下载目录
        cmd = f"you-get -o {download_dir} {url}"
        subprocess.run(cmd, shell=True, check=True)
        print("下载完成！")
    except subprocess.CalledProcessError as e:
        print(f"下载失败: {e}")

# 示例：下载BV号对应的视频
if __name__ == "__main__":
    bvid = "BV1qR1uBiEph"  # 请替换为你想下载的视频BV号
    bvid = "BV1bZC3BsEr3"
    bvid = "BV1byCABwEaX"
    bvid = "BV1nNWxzEEaC"   # 10.17
    bvid = "BV1EU411d7gd"   # 2024.5.30
    bvid = "BV1VSs5zkEsc"   # 10.23
    bvid = "BV1agsWzcEur"   # 10.24
    bvid = "BV1iVyvBiE6m"   # 10.30
    bvid = "BV1qR1uBiEph"   # 10.31
    bvid = "BV1TY2PBgEvt"   # 11.06
    bvid = "BV16V11BgEQi"   # 11.07
    bvid = "BV1byCABwEaX"   # 11.13
    bvid = "BV1bZC3BsEr3"   # 11.14
    bvid = "BV1VwyPBCEko"   # 11.20
    bvid = "BV1G1U7BxEY8"   # 11.21
    bvid = "BV19E411W7Wm"
    bvid = "BV1yoSgBZEhQ"   # 11.27
    bvid = "BV11hSnBxEk1"   # 11.28
    bvid = "BV1bZC3BsEr3"
    # 指定下载目录，这里设为当前目录下的'datas'文件夹
    download_dir = r"D:\曲曲直播录屏\2025\2025-11"
    download_bilibili_video(bvid, download_dir)