# -*- coding: utf-8 -*-
"""
案例处理主脚本
功能：
1. 解析Word文档提取案例
2. 调用DeepSeek清洗文字稿
3. 调用DeepSeek生成标题、分类、标签、适用人群场景
4. 使用FFmpeg分割视频
5. 生成CSV汇总文件
6. 支持断点续传
"""

import os
import re
import json
import csv
import subprocess
from datetime import datetime
from docx import Document
import requests
import time
from config import *

# ==================== 工具函数 ====================

def load_progress():
    """加载处理进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "failed": []}

def save_progress(progress):
    """保存处理进度"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def parse_time_to_seconds(time_str):
    """
    将时间字符串转换为秒数
    支持格式：MM:SS 或 HH:MM:SS
    """
    parts = time_str.split(':')
    if len(parts) == 2:  # MM:SS 格式
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:  # HH:MM:SS 格式
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

def seconds_to_time_str(seconds):
    """将秒数转换为 HH:MM:SS 格式"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

# ==================== Word文档解析 ====================

def extract_cases_from_docx(docx_path):
    """
    从Word文档中提取所有案例
    返回格式：[{
        'date': '2025-11-06',
        'case_index': 1,
        'case_id': '2025110601',
        'start_time': '11:38',
        'end_time': '26:08',
        'original_text': '...'
    }, ...]
    """
    doc = Document(docx_path)
    cases = []
    current_date = None
    case_index = 0
    current_case = None
    full_text = []
    
    print("开始解析Word文档...")
    
    for para in doc.paragraphs:
        text = para.text.strip()
        
        # 检测日期标题（如：2025-11-06 或 # 2025-11-06）
        date_match = re.match(r'#?\s*(\d{4}-\d{2}-\d{2})', text)
        if date_match:
            current_date = date_match.group(1)
            case_index = 0
            print(f"  发现日期：{current_date}")
            continue
        
        # 检测案例标记
        if text == "案例":# or text == "案例":
            # 保存上一个案例
            if current_case:
                current_case['original_text'] = '\n'.join(full_text).strip()
                cases.append(current_case)
                full_text = []
            
            # 开始新案例
            case_index += 1
            current_case = {
                'date': current_date,
                'case_index': case_index,
                'case_id': current_date.replace('-', '') + f"{case_index:02d}",
                'start_time': None,
                'end_time': None,
                'original_text': ''
            }
            print(f"    发现案例：{current_case['case_id']}")
            continue
        
        # 提取时间戳（格式：MM:SS 说话人X 或 HH:MM:SS 说话人X）
        if current_case and not current_case['start_time']:
            time_match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+说话人', text)
            if time_match:
                current_case['start_time'] = time_match.group(1)
        
        # 收集案例文本内容
        if current_case:
            full_text.append(text)
    
    # 保存最后一个案例
    if current_case:
        current_case['original_text'] = '\n'.join(full_text).strip()
        cases.append(current_case)
    
    # 设置结束时间（下一个案例的开始时间）
    for i in range(len(cases) - 1):
        cases[i]['end_time'] = cases[i + 1]['start_time']
    
    # 最后一个案例的结束时间设为None（表示到视频结尾）
    if cases:
        cases[-1]['end_time'] = None
    
    print(f"解析完成，共提取 {len(cases)} 个案例\n")
    return cases

# ==================== DeepSeek API调用 ====================

def call_deepseek_api(prompt, retry_count=0):
    """
    调用DeepSeek API
    支持重试机制
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    data = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": DEEPSEEK_TEMPERATURE
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        if retry_count < DEEPSEEK_MAX_RETRIES:
            print(f"    API调用失败，{3}秒后重试（{retry_count + 1}/{DEEPSEEK_MAX_RETRIES}）...")
            time.sleep(3)
            return call_deepseek_api(prompt, retry_count + 1)
        else:
            raise Exception(f"API调用失败超过最大重试次数: {str(e)}")

def clean_transcript(original_text):
    """
    第一次调用：清洗文字稿
    """
    prompt = f"""请对以下语音识别文字稿进行清洗和优化：

要求：
1. 修正识别错误和口语问题
2. 去除重复、卡壳、病句和不通顺的表达
3. 规范标点符号，必须使用中文标点符号
4. 去除过多的语气词（如：嗯、啊、哎等），但保留适当的语气词以维持说话风格
5. 将"雌性"统一改为"雌竞"，"雄性"统一改为"雄竞"
6. 说话人标记：将咨询用户改为"当事人"，咨询师改为"琪琪"
7. 必须保持原意、风格和语气，不要改变说话者的核心观点
8. 保留具体的人物、数据、场景描述

原始文字稿：
{original_text}

请直接输出清洗后的文字稿，不要添加任何说明或注释。"""

    return call_deepseek_api(prompt)

def generate_metadata(cleaned_text):
    """
    第二次调用：生成标题、分类、标签、适用人群和场景
    """
    prompt = f"""请分析以下案例内容，生成结构化的元数据信息：

案例内容：
{cleaned_text}

请按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "title": "案例标题（30字以内，概括核心问题，吸引读者关注）",
    "primary_category": "一级分类",
    "secondary_category": "二级分类",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
    "target_audience": "适用人群描述",
    "applicable_scenarios": "适用场景描述"
}}

分类要求：
- 一级分类：情感婚恋、职业发展、家庭关系、财富管理、个人成长等（总类目不超过8个）
- 一级分类现有类目：情感婚恋、职业发展、家庭关系、财富管理、个人成长
- 二级分类：基于一级分类细化，如"年龄差恋爱、职业规划、家族企业"等（总类目不超过50个）
- 二级分类现有类目：年龄差恋爱、职业规划、家族企业
- 标签：提供5-8个关键标签，如"高净值、年龄差、创业、留学生"等
- 适用人群：简洁描述哪些人群会对此案例感兴趣
- 适用场景：描述在什么情况下这个案例有参考价值

注意：标题要能击中用户痛点、引起共情或好奇心。"""

    response = call_deepseek_api(prompt)
    # 提取JSON（去除可能的markdown代码块标记）
    json_text = response.strip()
    if json_text.startswith('```'):
        json_text = re.sub(r'^```(?:json)?\n', '', json_text)
        json_text = re.sub(r'\n```$', '', json_text)
    
    return json.loads(json_text)

# ==================== 视频分割 ====================

def split_video(case_info):
    """
    使用FFmpeg分割视频
    """
    date = case_info['date']
    case_id = case_info['case_id']
    start_time = case_info['start_time']
    end_time = case_info['end_time']
    
    # 构建输入输出路径
    input_video = os.path.join(VIDEO_BASE_PATH, f"{date}.mp4")
    output_dir = os.path.join(SPLITS_BASE_PATH, date)
    os.makedirs(output_dir, exist_ok=True)
    output_video = os.path.join(output_dir, f"{case_id}.mp4")
    
    # 转换时间格式
    start_seconds = parse_time_to_seconds(start_time)
    start_time_str = seconds_to_time_str(start_seconds)
    
    # 构建FFmpeg命令
    if end_time:
        end_seconds = parse_time_to_seconds(end_time)
        duration = end_seconds - start_seconds
        cmd = [
            FFMPEG_PATH,
            '-i', input_video,
            '-ss', start_time_str,
            '-t', str(duration),
            '-c', 'copy',
            '-y',
            output_video
        ]
    else:
        # 如果没有结束时间，截取到视频末尾
        cmd = [
            FFMPEG_PATH,
            '-i', input_video,
            '-ss', start_time_str,
            '-c', 'copy',
            '-y',
            output_video
        ]
    
    print(f"  正在分割视频: {case_id}.mp4")
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_video

# ==================== CSV处理 ====================

def save_to_csv(case_data, csv_path):
    """
    保存案例数据到CSV文件
    如果文件不存在则创建，如果存在则追加
    """
    file_exists = os.path.exists(csv_path)
    
    fieldnames = [
        '案例编号', '日期', '案例标题', '一级分类', '二级分类', '标签',
        '起始时间', '结束时间', '适用人群', '适用场景',
        '原始文字稿', '清洗后文字稿', '视频文件路径'
    ]
    
    with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(case_data)

# ==================== 主处理流程 ====================

def process_case(case_info, progress):
    """
    处理单个案例的完整流程
    """
    case_id = case_info['case_id']
    
    # 检查是否已处理
    if case_id in progress['completed']:
        print(f"跳过已完成的案例: {case_id}")
        return
    
    print(f"\n{'='*60}")
    print(f"处理案例: {case_id}")
    print(f"{'='*60}")
    
    try:
        # 步骤1: 清洗文字稿
        print("步骤1: 清洗文字稿...")
        cleaned_text = clean_transcript(case_info['original_text'])
        print("  文字稿清洗完成")
        
        # 步骤2: 生成元数据
        print("步骤2: 生成标题和分类...")
        metadata = generate_metadata(cleaned_text)
        print(f"  标题: {metadata['title']}")
        print(f"  分类: {metadata['primary_category']} > {metadata['secondary_category']}")
        
        # 步骤3: 分割视频
        print("步骤3: 分割视频...")
        video_path = split_video(case_info)
        print(f"  视频保存至: {video_path}")
        
        # 步骤4: 保存到CSV
        print("步骤4: 保存到CSV...")
        csv_data = {
            '案例编号': case_id,
            '日期': case_info['date'],
            '案例标题': metadata['title'],
            '一级分类': metadata['primary_category'],
            '二级分类': metadata['secondary_category'],
            '标签': '、'.join(metadata['tags']),
            '起始时间': case_info['start_time'],
            '结束时间': case_info['end_time'] or '视频结尾',
            '适用人群': metadata['target_audience'],
            '适用场景': metadata['applicable_scenarios'],
            '原始文字稿': case_info['original_text'],
            '清洗后文字稿': cleaned_text,
            '视频文件路径': video_path
        }
        save_to_csv(csv_data, CSV_OUTPUT_PATH)
        
        # 标记为已完成
        progress['completed'].append(case_id)
        save_progress(progress)
        
        print(f"✓ 案例 {case_id} 处理完成！\n")
        
    except Exception as e:
        print(f"✗ 案例 {case_id} 处理失败: {str(e)}")
        progress['failed'].append(case_id)
        save_progress(progress)
        raise  # 重新抛出异常以停止程序

def main():
    """
    主函数
    """
    print("\n" + "="*60)
    print("案例处理系统启动")
    print("="*60 + "\n")
    
    # 创建必要的目录
    os.makedirs(os.path.dirname(CSV_OUTPUT_PATH), exist_ok=True)
    os.makedirs(SPLITS_BASE_PATH, exist_ok=True)
    
    # 加载进度
    progress = load_progress()
    print(f"已完成: {len(progress['completed'])} 个案例")
    print(f"失败: {len(progress['failed'])} 个案例\n")
    
    # 解析Word文档
    cases = extract_cases_from_docx(DOCX_PATH)
    
    # 过滤出未处理的案例
    pending_cases = [c for c in cases if c['case_id'] not in progress['completed']]
    print(f"待处理: {len(pending_cases)} 个案例\n")
    
    # 处理每个案例
    for i, case in enumerate(pending_cases, 1):
        print(f"[{i}/{len(pending_cases)}] ", end='')
        process_case(case, progress)
    
    print("\n" + "="*60)
    print("所有案例处理完成！")
    print(f"总计: {len(cases)} 个案例")
    print(f"成功: {len(progress['completed'])} 个")
    print(f"失败: {len(progress['failed'])} 个")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()