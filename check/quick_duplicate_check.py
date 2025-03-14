#!/usr/bin/env python3
"""
快速检测视频重复工具
简化版的视频重复检测，优化为命令行直接使用
"""

import os
import sys
import time
from pathlib import Path
import argparse
from video_duplicate_detector import find_duplicate_videos, clean_cache

def main():
    parser = argparse.ArgumentParser(description='快速检测视频重复工具')
    parser.add_argument('-d', '--directory', type=str, default='.',
                        help='要检测的视频目录，默认为当前目录')
    parser.add_argument('-t', '--threshold', type=float, default=0.9,
                        help='判定为重复的相似度阈值(0-1)，默认0.9')
    parser.add_argument('-p', '--processes', type=int, default=None,
                        help='使用的进程数量，默认为CPU核心数')
    parser.add_argument('-c', '--clean-cache', action='store_true',
                        help='清理过期的视频签名缓存')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='输出CSV文件路径，默认为当前目录下的repeat_videos_时间戳.csv')
    
    args = parser.parse_args()
    
    # 验证目录是否存在
    if not os.path.isdir(args.directory):
        print(f"错误：目录 '{args.directory}' 不存在")
        return 1
    
    # 切换到指定目录
    original_dir = os.getcwd()
    os.chdir(args.directory)
    print(f"正在检测目录: {os.getcwd()}")
    
    try:
        # 清理缓存
        if args.clean_cache:
            clean_cache()
        
        # 开始检测
        start_time = time.time()
        print(f"开始检测重复视频，相似度阈值: {args.threshold}...")
        
        duplicates = find_duplicate_videos(
            threshold=args.threshold,
            num_processes=args.processes
        )
        
        total_time = time.time() - start_time
        
        # 总结结果
        if duplicates:
            total_videos = sum(len(group) for group in duplicates.values())
            print(f"检测完成! 发现 {len(duplicates)} 组重复视频，共 {total_videos} 个视频文件")
            print(f"总耗时: {total_time:.2f}秒")
            
            # 如果有输出文件参数，显示完整路径
            csv_path = Path(os.getcwd()) / f'repeat_videos_{time.strftime("%Y%m%d_%H%M%S")}.csv'
            print(f"详细结果已保存到: {csv_path}")
        else:
            print("未发现重复视频")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n检测已取消")
        return 130
    except Exception as e:
        print(f"检测过程中出错: {e}")
        return 1
    finally:
        # 切回原目录
        os.chdir(original_dir)

if __name__ == "__main__":
    sys.exit(main()) 