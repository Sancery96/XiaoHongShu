# -*- coding: utf-8 -*-
"""
配置文件
存放所有可配置的参数
"""

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-8514f54e6924437c8408daa03c32e0d3"  # 替换为你的API密钥
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TEMPERATURE = 0.3
DEEPSEEK_MAX_RETRIES = 3  # API调用失败重试次数

# 文件路径配置
VIDEO_BASE_PATH = r"D:\曲曲直播录屏\2025\2025-11"  # 视频文件根目录
DOCX_PATH = r"D:\曲曲直播录屏\2025\2025-11\2025-11.docx"  # Word文档路径
CSV_OUTPUT_PATH = r"D:\曲曲直播录屏\2025\2025-11\案例汇总.csv"  # CSV输出路径
PROGRESS_FILE = r"D:\曲曲直播录屏\2025\2025-11\progress.json"  # 进度记录文件
SPLITS_BASE_PATH = r"D:\曲曲直播录屏\2025\2025-11\Splits"  # 分割视频保存根目录

# FFmpeg配置
FFMPEG_PATH = "ffmpeg"  # 如果ffmpeg在系统PATH中，直接写"ffmpeg"；否则写完整路径

# 处理配置
TAG_COUNT_MIN = 5  # 每个案例最少标签数
TAG_COUNT_MAX = 8  # 每个案例最多标签数
PRIMARY_CATEGORY_MAX = 8  # 一级分类最大数量
SECONDARY_CATEGORY_MAX = 50  # 二级分类最大数量
