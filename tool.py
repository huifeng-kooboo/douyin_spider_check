import cv2
import numpy as np
from tqdm import tqdm
import os
from util.douyin_util import DouYinUtil
from util.config import IS_SAVE, SAVE_FOLDER, USER_SEC_UID, IS_WRITE_TO_CSV, LOGIN_COOKIE, CSV_FILE_NAME
import sys

# 添加项目根目录到Python路径，以便从工具脚本中导入main模块中的数据库模型
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from main import db, Video
except ImportError:
    # 在单独运行tool.py时提供空的模拟对象
    class MockDB:
        def session(self):
            return self
        def add(self, obj):
            pass
        def commit(self):
            pass
    
    class MockVideo:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    db = MockDB()
    Video = MockVideo


def download_user_videos(sec_uid, task_id=None, user_id=None):
    """
    下载抖音用户的所有视频
    
    参数:
        sec_uid (str): 抖音用户的sec_uid
        task_id (int, optional): 下载任务ID，用于数据库记录
        user_id (int, optional): 用户ID，用于数据库记录
        
    返回:
        list: 下载的视频信息列表
    """
    print(f"[ToRecord]开始下载用户{sec_uid}的视频")
    dy_util = DouYinUtil(sec_uid=sec_uid)
    all_video_list = dy_util.get_all_videos()
    downloaded_videos = []
    
    for video_id in all_video_list:
        try:
            video_info = dy_util.get_video_detail_info(video_id)
            
            if video_info['is_video'] is True:
                print(f"视频下载链接:{video_info['link']}")
                file_path = f"{video_id}.mp4"
                
                # 下载视频
                download_success = dy_util.download_video(video_info['link'], file_path)
                
                # 记录视频信息
                video_data = {
                    'video_id': video_id,
                    'title': video_info.get('title', ''),
                    'download_url': video_info['link'],
                    'file_path': file_path,
                    'status': '已下载' if download_success else '下载失败'
                }
                downloaded_videos.append(video_data)
                
                # 如果提供了数据库参数，则保存到数据库
                # if task_id is not None and user_id is not None:
                #     try:
                #         # 创建视频记录
                #         db_video = Video(
                #             video_id=video_id,
                #             user_id=user_id,
                #             task_id=task_id,
                #             title=video_info.get('title', ''),
                #             download_url=video_info['link'],
                #             file_path=file_path,
                #             status='已下载' if download_success else '下载失败'
                #         )
                #         db.session.add(db_video)
                #         db.session.commit()
                #     except Exception as e:
                #         print(f"保存视频记录到数据库时出错: {str(e)}")
        except Exception as e:
            print(f"处理视频 {video_id} 时出错: {str(e)}")
    
    return downloaded_videos


def compare_video(video_path1, video_path2, similarity_threshold=95):
    """
    比较两个视频的相似度
    
    参数:
        video_path1 (str): 第一个视频文件路径
        video_path2 (str): 第二个视频文件路径
        similarity_threshold (float): 相似度阈值，默认95%
    
    返回:
        bool: 如果两个视频相似度高于阈值则返回True，否则返回False
    """
    # 检查文件是否存在
    if not os.path.exists(video_path1) or not os.path.exists(video_path2):
        print("错误：一个或多个视频文件不存在")
        return False
    
    # 打开视频文件
    cap1 = cv2.VideoCapture(video_path1)
    cap2 = cv2.VideoCapture(video_path2)
    
    # 检查是否成功打开
    if not cap1.isOpened() or not cap2.isOpened():
        print("错误：无法打开视频文件")
        return False
    
    # 获取视频帧数
    frame_count1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 取两个视频中较短的
    sample_count = min(frame_count1, frame_count2)
    
    # 计算采样间隔（为了提高效率，我们可以每隔几帧比较一次）
    # 如果视频很长，可以适当增加step_size
    step_size = max(1, sample_count // 100)  # 至少采样100帧
    
    # 初始化相似帧计数
    similar_frames = 0
    total_compared = 0
    
    print(f"开始比较视频，采样间隔：{step_size}帧")
    
    # 使用进度条
    for i in tqdm(range(0, sample_count, step_size)):
        # 设置视频的当前帧位置
        cap1.set(cv2.CAP_PROP_POS_FRAMES, i)
        cap2.set(cv2.CAP_PROP_POS_FRAMES, i)
        
        # 读取帧
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        # 检查帧是否成功读取
        if not ret1 or not ret2:
            continue
        
        # 调整大小以加速比较（可选）
        frame1_resized = cv2.resize(frame1, (320, 240))
        frame2_resized = cv2.resize(frame2, (320, 240))
        
        # 计算直方图相似度（这是一种简单的比较方法）
        hist1 = cv2.calcHist([frame1_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([frame2_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        
        # 归一化直方图
        cv2.normalize(hist1, hist1, 0, 1.0, cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, 0, 1.0, cv2.NORM_MINMAX)
        
        # 比较直方图
        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        # 如果相似度大于0.8（这个值可以调整），认为帧相似
        if score > 0.8:
            similar_frames += 1
        
        total_compared += 1
    
    # 释放视频资源
    cap1.release()
    cap2.release()
    
    # 计算相似度百分比
    if total_compared == 0:
        return False
    
    similarity_percentage = (similar_frames / total_compared) * 100
    print(f"视频相似度: {similarity_percentage:.2f}%")
    
    # 判断是否超过阈值
    return similarity_percentage >= similarity_threshold


def compare_videos_batch(videos_dir, similarity_threshold=95, output_csv=None):
    """
    批量比较多个视频之间的相似度，找出相似视频对
    
    参数:
        videos_dir (str): 包含视频文件的目录
        similarity_threshold (float): 相似度阈值，默认95%
        output_csv (str): 输出CSV文件路径，默认为None
        
    返回:
        list: 相似视频对的列表，每个元素为(video1, video2, similarity)元组
    """
    import itertools
    import csv
    from datetime import datetime
    
    # 确保目录存在
    if not os.path.exists(videos_dir):
        print(f"错误：视频目录 {videos_dir} 不存在")
        return []
    
    # 查找目录中的所有MP4文件
    video_files = []
    for root, _, files in os.walk(videos_dir):
        for file in files:
            if file.lower().endswith('.mp4'):
                video_files.append(os.path.join(root, file))
    
    if not video_files:
        print(f"警告：在 {videos_dir} 中未找到MP4视频文件")
        return []
    
    print(f"找到 {len(video_files)} 个视频文件，开始比较...")
    
    # 存储相似视频对
    similar_pairs = []
    
    # 比较所有可能的视频对
    total_comparisons = len(list(itertools.combinations(video_files, 2)))
    completed = 0
    
    for i, video1 in enumerate(video_files):
        for video2 in video_files[i+1:]:
            completed += 1
            print(f"正在比较 ({completed}/{total_comparisons}): {os.path.basename(video1)} 与 {os.path.basename(video2)}")
            
            try:
                # 使用compare_video函数比较两个视频
                is_similar = compare_video(video1, video2, similarity_threshold)
                
                if is_similar:
                    # 提取视频ID（假设文件名就是视频ID加扩展名）
                    video1_id = os.path.basename(video1).replace('.mp4', '')
                    video2_id = os.path.basename(video2).replace('.mp4', '')
                    
                    print(f"发现相似视频: {video1_id} 和 {video2_id}")
                    similar_pairs.append((video1_id, video2_id))
            except Exception as e:
                print(f"比较视频时出错: {str(e)}")
    
    # 如果指定了输出CSV文件，则保存结果
    if output_csv and similar_pairs:
        try:
            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入标题行
                writer.writerow(['视频ID1', '视频ID2', '比较时间'])
                
                # 写入数据行
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for video1_id, video2_id in similar_pairs:
                    writer.writerow([video1_id, video2_id, current_time])
                
                print(f"已将 {len(similar_pairs)} 对相似视频记录到 {output_csv}")
        except Exception as e:
            print(f"保存CSV文件时出错: {str(e)}")
    
    return similar_pairs


def batch_download_and_compare(sec_id_list, similarity_threshold=95, output_csv=None):
    """
    批量下载多个用户的视频并进行相似度比较
    
    参数:
        sec_id_list (list): 抖音用户sec_id列表
        similarity_threshold (float): 相似度阈值，默认95%
        output_csv (str): 输出CSV文件路径，默认为None
        
    返回:
        dict: 包含下载和比较结果的字典
    """
    import os
    from datetime import datetime
    
    result = {
        'download_count': 0,
        'similar_pairs': [],
        'error': None
    }
    
    # 开始时间
    start_time = datetime.now()
    print(f"开始批量下载和比较任务，时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 下载所有用户的视频
    all_downloaded_videos = []
    
    for sec_id in sec_id_list:
        try:
            print(f"下载用户 {sec_id} 的视频...")
            videos = download_user_videos(sec_id)
            if videos:
                all_downloaded_videos.extend(videos)
                result['download_count'] += len(videos)
                print(f"成功下载用户 {sec_id} 的 {len(videos)} 个视频")
            else:
                print(f"用户 {sec_id} 没有可下载的视频")
        except Exception as e:
            print(f"下载用户 {sec_id} 的视频时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 如果没有下载到视频，则提前结束
    if not all_downloaded_videos:
        result['error'] = "未成功下载任何视频"
        return result
    
    # 确定视频存储的目录
    video_dir = os.path.join(SAVE_FOLDER)
    
    # 比较视频相似度
    try:
        print(f"开始比较 {result['download_count']} 个视频的相似度...")
        similar_pairs = compare_videos_batch(video_dir, similarity_threshold, output_csv)
        result['similar_pairs'] = similar_pairs
        print(f"相似度比较完成，发现 {len(similar_pairs)} 对相似视频")
    except Exception as e:
        print(f"比较视频相似度时出错: {str(e)}")
        result['error'] = str(e)
        import traceback
        traceback.print_exc()
    
    # 结束时间
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"批量下载和比较任务结束，总用时: {duration:.2f} 秒")
    
    return result
