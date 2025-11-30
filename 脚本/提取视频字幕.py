import subprocess
import shutil
from pathlib import Path
from datetime import timedelta
import torch
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import argparse
import sys

SUPPORTED_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.ts']


def check_ffmpeg():
    """检查 ffmpeg 是否可用"""
    # 尝试运行 ffmpeg 命令验证
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              check=True,
                              timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def load_model(model_path, compute_type="int8"):
    from faster_whisper import WhisperModel
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return WhisperModel(
        model_path,
        device=device,
        compute_type=compute_type,
        download_root=None,
        local_files_only=True
    )


def find_video_files(root_dir):
    video_files = []
    root_path = Path(root_dir)
    for fmt in SUPPORTED_FORMATS:
        video_files.extend(root_path.rglob(f"*{fmt}"))
        video_files.extend(root_path.rglob(f"*{fmt.upper()}"))
    return sorted(list(set(video_files)))


def format_timestamp(seconds):
    td = timedelta(seconds=seconds)
    hours = int(td.seconds // 3600)
    minutes = int((td.seconds % 3600) // 60)
    seconds = int(td.seconds % 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def extract_audio(video_path, audio_path):
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-ac', '1',
        '-ar', '16000',
        '-acodec', 'pcm_s16le',
        '-af', "aresample=async=1",
        '-y',
        '-hide_banner', '-loglevel', 'error',
        '-threads', '2',
        str(audio_path)
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        return True
    except:
        return False


def transcribe(model, audio_path, txt_path):
    with open(txt_path, 'w', encoding='utf-8') as f:
        segments, _ = model.transcribe(
            str(audio_path),
            language="zh",
            task="transcribe",
            beam_size=1,
            best_of=1,
            patience=1.0,
            temperature=0.0,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            word_timestamps=True,
        )
        for segment in segments:
            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)
            f.write(f"[{start} --> {end}] {segment.text.strip()}\n")
    return True


def process_video(video_path, output_dir, model):
    print(f"Processing video: {video_path}")
    video_path = Path(video_path)
    
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}.txt"
    else:
        output_path = video_path.parent / f"{video_path.stem}.txt"
    
    if output_path.exists():
        print(f"Skipping video: {video_path} (already processed)")
        return
    
    temp_dir = video_path.parent / "temp_audio"
    temp_dir.mkdir(exist_ok=True)
    temp_audio = temp_dir / f"temp_{video_path.stem}.wav"
    
    try:
        if not extract_audio(video_path, temp_audio):
            return
        transcribe(model, temp_audio, output_path)
    finally:
        if temp_audio.exists():
            temp_audio.unlink()
        try:
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except:
            pass


def batch_convert(input_dir, model_path, output_dir=None, max_workers=2, compute_type="int8"):
    if not check_ffmpeg():
        print("错误: FFmpeg 不可用")
        return
    try:
        model = load_model(model_path, compute_type)
    except:
        print("错误: 模型加载失败")
        return
    
    video_files = find_video_files(input_dir)
    if not video_files:
        print("未找到任何视频文件")
        return
    
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), 4)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_video, vf, output_dir, model) for vf in video_files]
        for future in as_completed(futures):
            future.result()


def main():
    input_dir=r'D:\曲曲直播录屏\金贵的关系2' #'输入视频目录路径'
    model_path=r'C:\Users\Sance\Downloads\faster-whisper-medium' #'本地模型路径'
    output_dir=r'C:\Users\自媒体创作\datas\金贵的关系2视频字幕' #'输出目录路径（可选）'
    workers=2 #'并行工作线程数'
    compute_type='int8' #'计算类型'
    batch_convert(input_dir, model_path, output_dir, workers, compute_type)

if __name__ == "__main__":
    main()