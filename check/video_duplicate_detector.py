import os
import cv2
import csv
import glob
import hashlib
import numpy as np
import pickle
import time
from collections import defaultdict
import concurrent.futures
import multiprocessing
from pathlib import Path

# 缓存目录
CACHE_DIR = ".video_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_video_frames(video_path, sample_rate=30):
    """
    从视频中提取帧，以降低处理量我们每隔sample_rate帧提取一帧
    增加采样间隔到30以提高速度
    """
    frames = []
    video = cv2.VideoCapture(video_path)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 如果视频太短，调整采样率
    if total_frames < 300:
        sample_rate = max(1, total_frames // 10)
    
    # 计算要采样的帧数量，最多采样20帧
    max_frames = 20
    frames_to_sample = min(max_frames, total_frames // sample_rate)
    
    # 计算均匀分布的采样点
    if frames_to_sample > 0:
        sample_points = [int(i * total_frames / frames_to_sample) for i in range(frames_to_sample)]
    else:
        sample_points = []
    
    for i in sample_points:
        video.set(cv2.CAP_PROP_POS_FRAMES, i)
        success, frame = video.read()
        if success:
            # 调整大小以减少计算量，降低到32x32
            frame = cv2.resize(frame, (32, 32))
            # 转为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append(gray)
        else:
            break
    
    video.release()
    return frames

def compute_frame_hash(frame):
    """
    计算帧的感知哈希值
    """
    # 降低分辨率用于哈希计算
    resized = cv2.resize(frame, (8, 8))
    # 计算平均值
    avg = np.mean(resized)
    # 生成哈希
    diff = resized > avg
    # 将布尔值转换为0和1
    hash_value = ''.join('1' if b else '0' for b in diff.flatten())
    return hash_value

def get_cache_path(video_path):
    """获取视频签名的缓存文件路径"""
    # 使用视频路径的哈希作为缓存文件名
    video_hash = hashlib.md5(video_path.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{video_hash}.pkl")

def compute_video_signature(video_path):
    """
    计算视频的签名（一组帧哈希），优先从缓存读取
    """
    # 检查缓存是否存在
    cache_path = get_cache_path(video_path)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
                # 检查文件修改时间是否匹配，避免使用过期缓存
                if cached_data.get('mtime') == os.path.getmtime(video_path):
                    return cached_data.get('signatures', [])
        except Exception as e:
            print(f"读取缓存出错: {e}")
    
    # 缓存不存在或已过期，重新计算
    frames = get_video_frames(video_path)
    if not frames:
        return []
    
    signatures = []
    for frame in frames:
        hash_value = compute_frame_hash(frame)
        signatures.append(hash_value)
    
    # 保存到缓存
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump({
                'mtime': os.path.getmtime(video_path),
                'signatures': signatures
            }, f)
    except Exception as e:
        print(f"保存缓存出错: {e}")
    
    return signatures

def quick_compare(sig1, sig2, threshold=0.85):
    """
    快速比较两个视频签名，只比较少量帧
    """
    if not sig1 or not sig2:
        return 0.0
    
    # 获取较短的签名长度
    min_len = min(len(sig1), len(sig2))
    if min_len < 3:  # 至少需要3个帧
        return 0.0
    
    # 只比较少量帧（最多5个）
    compare_frames = min(5, min_len)
    step = max(1, min_len // compare_frames)
    
    matches = 0
    samples = 0
    for i in range(0, min_len, step):
        if i >= min_len or samples >= compare_frames:
            break
        
        h1 = sig1[i]
        h2 = sig2[i]
        # 计算哈希相似度（汉明距离）
        similarity = 1 - sum(c1 != c2 for c1, c2 in zip(h1, h2)) / len(h1)
        if similarity > 0.85:  # 使用较低的阈值进行快速过滤
            matches += 1
        samples += 1
    
    return matches / samples

def process_video(args):
    """
    处理单个视频并返回其签名，用于多进程处理
    """
    video_file, index, total = args
    try:
        print(f"处理视频 {index+1}/{total}: {video_file}")
        signature = compute_video_signature(video_file)
        return video_file, signature
    except Exception as e:
        print(f"处理视频 {video_file} 时出错: {e}")
        return video_file, []

def compare_signatures(sig1, sig2, threshold=0.9):
    """
    比较两个视频签名的相似度
    返回重复百分比（0-1之间）
    """
    if not sig1 or not sig2:
        return 0.0
    
    # 获取较短的签名长度
    min_len = min(len(sig1), len(sig2))
    # 至少需要比较3个帧
    if min_len < 3:
        return 0.0
    
    # 取较短视频的长度
    sig1 = sig1[:min_len]
    sig2 = sig2[:min_len]
    
    matches = 0
    for h1, h2 in zip(sig1, sig2):
        # 计算哈希相似度（汉明距离）
        similarity = 1 - sum(c1 != c2 for c1, c2 in zip(h1, h2)) / len(h1)
        # 如果帧相似度大于阈值，认为匹配
        if similarity > threshold:
            matches += 1
    
    return matches / min_len

def find_duplicate_videos(threshold=0.9, num_processes=None):
    """
    查找重复视频并将结果写入CSV
    threshold: 判定为重复的相似度阈值
    num_processes: 进程数量，默认为CPU核心数
    """
    start_time = time.time()
    
    if num_processes is None:
        # 使用CPU核心数，但最多使用16个进程
        num_processes = min(16, multiprocessing.cpu_count())
    
    print(f"使用 {num_processes} 个进程进行处理")
    print("正在查找项目中的MP4文件...")
    video_files = glob.glob("**/*.mp4", recursive=True)
    print(f"找到 {len(video_files)} 个MP4文件")
    
    if not video_files:
        print("未找到任何MP4文件")
        return
    
    # 使用多进程计算每个视频的签名
    signatures = {}
    
    # 准备进程池参数
    args_list = [(video_file, i, len(video_files)) for i, video_file in enumerate(video_files)]
    
    # 使用进程池并行处理视频
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(process_video, args_list)
        
    # 处理结果
    signatures = dict(results)
    
    print("所有视频签名计算完成，开始比对...")
    print(f"签名计算耗时: {time.time() - start_time:.2f}秒")
    compare_start_time = time.time()
    
    # 查找重复视频（两阶段比较）
    duplicates = defaultdict(list)
    similarity_info = {}  # 存储视频间的相似度信息
    processed = set()
    
    # 建立视频索引以加速比较
    video_index = list(signatures.items())
    
    for i, (video1, sig1) in enumerate(video_index):
        if video1 in processed:
            continue
        
        if i % 100 == 0:
            print(f"处理进度: {i}/{len(video_index)}")
        
        current_group = [video1]
        processed.add(video1)
        
        # 记录当前组内视频之间的相似度
        current_group_similarities = {}
        
        for j in range(i+1, len(video_index)):
            video2, sig2 = video_index[j]
            
            if video2 in processed:
                continue
            
            # 第一阶段：快速比较（粗筛）
            quick_sim = quick_compare(sig1, sig2)
            
            # 如果快速比较通过阈值，进行详细比较
            if quick_sim >= 0.7:  # 较低的阈值以减少漏报
                similarity = compare_signatures(sig1, sig2, threshold)
                if similarity >= threshold:
                    current_group.append(video2)
                    processed.add(video2)
                    
                    # 记录相似度信息
                    video_pair = (video1, video2)
                    current_group_similarities[video_pair] = similarity
        
        if len(current_group) > 1:
            group_id = len(duplicates) + 1
            duplicates[group_id] = current_group
            
            # 存储相似度信息
            for pair, sim in current_group_similarities.items():
                similarity_info[pair] = sim
    
    print(f"视频比对耗时: {time.time() - compare_start_time:.2f}秒")
    
    # 准备文件大小信息
    file_sizes = {}
    for video in video_files:
        try:
            file_sizes[video] = os.path.getsize(video) / (1024 * 1024)  # 转换为MB
        except Exception:
            file_sizes[video] = 0
    
    # 将结果写入CSV
    csv_filename = f'repeat_videos_{time.strftime("%Y%m%d_%H%M%S")}.csv'
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            '重复组ID', 
            '视频名称', 
            '视频下载链接', 
            '文件路径',
            '文件大小(MB)',
            '相似度(%)'
        ])
        
        for group_id, group in duplicates.items():
            # 首先按文件名排序，使输出更整齐
            sorted_group = sorted(group, key=lambda x: os.path.basename(x))
            
            # 对于每个组内的第一个视频，它是参考视频
            reference_video = sorted_group[0]
            
            for video in sorted_group:
                video_name = os.path.basename(video)
                download_link = f"https://douyin.com/?modal_id={video_name.replace('.mp4', '')}"
                file_size = f"{file_sizes.get(video, 0):.2f}"
                
                # 计算相似度
                if video == reference_video:
                    # 参考视频自身相似度是100%
                    similarity_percent = "100.0"
                else:
                    # 查找与参考视频的相似度
                    pair = (reference_video, video)
                    if pair not in similarity_info:
                        pair = (video, reference_video)  # 尝试反向对
                    
                    similarity = similarity_info.get(pair, threshold)
                    similarity_percent = f"{similarity * 100:.1f}"
                
                writer.writerow([
                    f"组-{group_id}", 
                    video_name, 
                    download_link,
                    video,
                    file_size,
                    similarity_percent
                ])
            
            # 在不同组之间添加空行，增强可读性
            writer.writerow([])
    
    total_time = time.time() - start_time
    print(f"发现 {len(duplicates)} 组重复视频，结果已保存到 {csv_filename}")
    print(f"总耗时: {total_time:.2f}秒")
    return duplicates

def clean_cache():
    """清理过期的缓存文件"""
    print("清理过期缓存...")
    cache_files = os.listdir(CACHE_DIR)
    cleaned = 0
    
    for cache_file in cache_files:
        cache_path = os.path.join(CACHE_DIR, cache_file)
        try:
            # 如果缓存文件超过7天未使用，删除它
            if time.time() - os.path.getmtime(cache_path) > 7 * 24 * 3600:
                os.remove(cache_path)
                cleaned += 1
        except Exception:
            pass
    
    print(f"清理了 {cleaned} 个缓存文件")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='检测重复视频并生成报告')
    parser.add_argument('--threshold', type=float, default=0.9, help='判定为重复的相似度阈值(0-1)，默认0.9')
    parser.add_argument('--processes', type=int, default=None, help='使用的进程数量，默认为CPU核心数')
    parser.add_argument('--clean-cache', action='store_true', help='清理过期的视频签名缓存')
    
    args = parser.parse_args()
    
    if args.clean_cache:
        clean_cache()
    
    find_duplicate_videos(threshold=args.threshold, num_processes=args.processes) 