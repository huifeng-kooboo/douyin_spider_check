import os
import csv
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import hashlib
import argparse
import time
from collections import defaultdict

# 定义视频哈希函数，用于计算视频的特征指纹
def compute_video_hash(video_path, frames_to_sample=10):
    """
    计算视频的特征哈希，通过采样一定数量的帧并计算它们的内容哈希
    """
    try:
        # 首先检查文件大小，如果过小可能是损坏的文件
        file_size = os.path.getsize(video_path)
        if file_size < 10000:  # 如果小于10KB，可能是损坏的文件
            print(f"警告: 文件过小，可能损坏 {video_path}")
            return None
            
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"警告: 无法打开视频 {video_path}")
            return None
        
        # 获取视频的总帧数和基本信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        if total_frames <= 0 or width <= 0 or height <= 0 or fps <= 0:
            print(f"警告: 视频 {video_path} 参数无效")
            return None
        
        # 视频基本信息也作为特征的一部分
        video_info = f"{width}x{height}@{fps:.2f}fps-{total_frames}frames"
        
        # 计算采样间隔
        if total_frames < frames_to_sample:
            # 如果视频帧数太少，就采样所有帧
            frame_indices = list(range(total_frames))
        else:
            # 均匀采样，确保采样到关键帧
            frame_indices = [int(i * total_frames / frames_to_sample) for i in range(frames_to_sample)]
        
        # 收集所有采样帧的哈希值
        frame_hashes = []
        raw_frame_hashes = []  # 保存原始的二进制哈希值，用于计算相似度
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
                
            # 转为灰度图并降低分辨率
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # 使用适中的大小来确保准确性
            resized = cv2.resize(gray, (64, 64))
            
            # 使用更精确的感知哈希
            # 1. 计算平均哈希
            avg = np.mean(resized)
            binary_hash1 = (resized > avg).flatten()
            
            # 2. 计算DCT感知哈希
            dct = cv2.dct(np.float32(resized))
            # 取左上角的8x8低频区域
            dct_low = dct[:8, :8]
            # 排除第一个直流分量
            dct_avg = np.mean(dct_low[1:])
            binary_hash2 = (dct_low > dct_avg).flatten()
            
            # 合并两种哈希
            binary_hash = np.concatenate([binary_hash1, binary_hash2])
            raw_frame_hashes.append(binary_hash)  # 保存原始二进制哈希值
            
            binary_hash_packed = np.packbits(binary_hash)
            frame_hashes.extend(binary_hash_packed)
        
        cap.release()
        
        # 计算最终哈希值，加入视频基本信息
        if not frame_hashes:
            return None
        
        # 构建一个哈希对象，包含原始的二进制哈希值用于比较相似度
        hash_obj = hashlib.sha256()
        hash_obj.update(bytes(frame_hashes))
        hash_obj.update(video_info.encode())
        
        # 返回哈希值和原始哈希数据的元组
        return {
            'hash': hash_obj.hexdigest(),
            'raw_hashes': raw_frame_hashes,  # 原始的二进制哈希值
            'video_info': video_info  # 视频基本信息
        }
    
    except Exception as e:
        print(f"处理视频时发生错误 {video_path}: {str(e)}")
        return None

# 计算两个视频的相似度
def calculate_similarity(hash_data1, hash_data2):
    """
    计算两个视频哈希数据的相似度（0-100%）
    使用汉明距离来计算二进制哈希值的相似度
    """
    if hash_data1 is None or hash_data2 is None:
        return 0.0
    
    # 首先比较视频基本信息，如果基本参数差异太大，直接判定为不相似
    info1 = hash_data1['video_info'].split('@')[0]  # 分辨率部分
    info2 = hash_data2['video_info'].split('@')[0]
    if info1 != info2:  # 分辨率不同的视频直接认为不相似
        return 0.0
    
    # 计算每一帧的相似度
    raw_hashes1 = hash_data1['raw_hashes']
    raw_hashes2 = hash_data2['raw_hashes']
    
    # 确保两个列表长度一致（取较短的那个）
    min_len = min(len(raw_hashes1), len(raw_hashes2))
    
    if min_len == 0:
        return 0.0
    
    # 计算每一帧的汉明距离
    frame_similarities = []
    for i in range(min_len):
        # 计算汉明距离：相同位数 / 总位数
        hash1 = raw_hashes1[i]
        hash2 = raw_hashes2[i]
        
        # 确保两个哈希向量长度一致
        min_hash_len = min(len(hash1), len(hash2))
        if min_hash_len == 0:
            continue
            
        # 汉明距离 = 不同位的数量
        hamming_distance = np.sum(hash1[:min_hash_len] != hash2[:min_hash_len])
        # 相似度 = 1 - 不同位的比例
        similarity = 1.0 - (hamming_distance / min_hash_len)
        frame_similarities.append(similarity)
    
    # 如果没有有效的帧相似度，返回0
    if not frame_similarities:
        return 0.0
    
    # 返回所有帧的平均相似度（百分比）
    return (sum(frame_similarities) / len(frame_similarities)) * 100.0

def find_similar_videos(similarity_threshold=90.0):
    """查找相似度超过阈值的视频文件"""
    # 存储所有视频文件的路径
    all_videos = []
    # 遍历当前目录下的所有文件夹
    for dirpath, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            if filename.endswith('.mp4'):
                all_videos.append(os.path.join(dirpath, filename))
    
    total_videos = len(all_videos)
    print(f"找到 {total_videos} 个MP4文件")
    
    # 计算所有视频的哈希值
    video_hash_data = {}
    print("计算视频哈希值（将处理所有视频）...")
    
    # 使用多线程加速处理
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # 使用tqdm显示进度条
        hash_results = list(tqdm(
            executor.map(compute_video_hash, all_videos),
            total=total_videos
        ))
    
    # 将结果存入字典
    for video_path, hash_data in zip(all_videos, hash_results):
        if hash_data is not None:
            video_hash_data[video_path] = hash_data
    
    print(f"成功计算了 {len(video_hash_data)} 个视频的哈希值")
    
    # 找出相似的视频（相似度超过阈值）
    print(f"查找相似度 >= {similarity_threshold}% 的视频...")
    similar_groups = []
    processed_videos = set()
    
    # 首先处理完全相同的视频 (相同哈希值)
    hash_to_videos = defaultdict(list)
    for video_path, hash_data in video_hash_data.items():
        hash_val = hash_data['hash']
        hash_to_videos[hash_val].append(video_path)
    
    # 处理完全相同的视频，并按照文件创建时间排序
    for hash_val, videos in hash_to_videos.items():
        if len(videos) > 1:
            # 按文件创建时间排序，最早创建的视频排在前面（被视为原视频）
            videos_with_time = [(v, os.path.getctime(v)) for v in videos]
            videos_with_time.sort(key=lambda x: x[1])  # 按创建时间排序
            sorted_videos = [v[0] for v in videos_with_time]  # 提取排序后的路径
            
            similar_groups.append(sorted_videos)
            processed_videos.update(videos)
    
    # 然后处理相似但不完全相同的视频
    video_paths = list(video_hash_data.keys())
    for i, video1 in enumerate(video_paths):
        if video1 in processed_videos:
            continue
        
        current_group = [video1]
        hash_data1 = video_hash_data[video1]
        
        for j in range(i+1, len(video_paths)):
            video2 = video_paths[j]
            if video2 in processed_videos:
                continue
                
            hash_data2 = video_hash_data[video2]
            similarity = calculate_similarity(hash_data1, hash_data2)
            
            if similarity >= similarity_threshold:
                current_group.append(video2)
                processed_videos.add(video2)
        
        if len(current_group) > 1:
            # 按文件创建时间排序
            current_group_with_time = [(v, os.path.getctime(v)) for v in current_group]
            current_group_with_time.sort(key=lambda x: x[1])  # 按创建时间排序
            sorted_group = [v[0] for v in current_group_with_time]  # 提取排序后的路径
            
            similar_groups.append(sorted_group)
        
        processed_videos.add(video1)
    
    # 构建用于CSV输出的简化哈希数据
    simplified_hashes = {}
    for video_path, hash_data in video_hash_data.items():
        simplified_hashes[video_path] = hash_data['hash']
    
    return similar_groups, simplified_hashes

def extract_video_id(video_path):
    """从文件路径中提取视频ID"""
    base_name = os.path.basename(video_path)
    video_id = os.path.splitext(base_name)[0]
    return video_id

def save_to_csv(similar_groups, video_hashes, csv_filename="similar_videos.csv"):
    """将相似视频组保存到CSV文件"""
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        # 写入表头
        csv_writer.writerow(['组ID', '视频类型', '文件名', '视频ID', '视频链接', '哈希值'])
        
        # 写入数据
        for group_id, group in enumerate(similar_groups, 1):
            # 将第一个视频标记为原视频，其余为重复视频
            for i, video_path in enumerate(group):
                video_id = extract_video_id(video_path)
                video_url = f"https://douyin.com/?modal_id={video_id}"
                video_hash = video_hashes.get(video_path, "未计算")
                video_type = "原视频" if i == 0 else "重复视频"
                
                csv_writer.writerow([
                    f"组{group_id}",
                    video_type,
                    os.path.basename(video_path),
                    video_id,
                    video_url,
                    video_hash
                ])
    
    print(f"已将结果保存到 {csv_filename}")
    print(f"每组视频中，按创建时间最早的视频被标记为'原视频'，其余视频被标记为'重复视频'")

if __name__ == "__main__":
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description="查找相似的抖音视频")
    parser.add_argument("--similarity", type=float, default=90.0, help="相似度阈值，单位为百分比，默认90.0%")
    parser.add_argument("--output", type=str, default="similar_videos.csv", help="输出CSV文件名")
    
    args = parser.parse_args()
    
    # 记录开始时间
    start_time = time.time()
    
    print(f"开始查找相似度>={args.similarity}%的视频...")
    similar_groups, video_hashes = find_similar_videos(similarity_threshold=args.similarity)
    
    # 打印结果统计
    total_matched_videos = sum(len(group) for group in similar_groups)
    similar_video_count = total_matched_videos - len(similar_groups)
    
    print(f"找到 {len(similar_groups)} 组相似视频，共涉及 {total_matched_videos} 个视频文件")
    print(f"其中有 {similar_video_count} 个视频与其他视频相似")
    
    # 保存到CSV
    save_to_csv(similar_groups, video_hashes, args.output)
    
    # 计算总运行时间
    elapsed_time = time.time() - start_time
    print(f"处理完成！总耗时: {elapsed_time:.2f} 秒") 