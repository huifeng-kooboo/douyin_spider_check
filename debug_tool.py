#!/usr/bin/env python3
"""
调试脚本，用于测试 tool.py 中的数据库操作
"""
import sys
import os
import traceback
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_standalone_db():
    """测试独立数据库模式"""
    print("\n" + "="*50)
    print("测试 tool.py 独立数据库模式")
    print("="*50)
    
    try:
        # 导入工具模块
        from tool import app, db, User, DownloadTask, Video
        
        # 测试应用上下文
        with app.app_context():
            print("\n1. 测试数据库连接")
            print(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print(f"数据库会话状态: {'活跃' if db.session.is_active else '非活跃'}")
            
            # 测试创建用户
            print("\n2. 测试创建用户")
            test_user_id = f"debug_user_{datetime.now().timestamp()}"
            print(f"创建测试用户: {test_user_id}")
            
            user = User(sec_id=test_user_id)
            db.session.add(user)
            db.session.commit()
            print(f"用户创建成功，ID: {user.id}")
            
            # 测试创建任务
            print("\n3. 测试创建任务")
            test_thread_id = f"debug_thread_{datetime.now().timestamp()}"
            print(f"创建测试任务，thread_id: {test_thread_id}")
            
            task = DownloadTask(thread_id=test_thread_id, user_id=user.id, status="测试中")
            db.session.add(task)
            db.session.commit()
            print(f"任务创建成功，ID: {task.id}")
            
            # 测试创建视频记录
            print("\n4. 测试创建视频记录")
            test_video_id = f"debug_video_{datetime.now().timestamp()}"
            print(f"创建测试视频记录，video_id: {test_video_id}")
            
            try:
                video = Video(
                    video_id=test_video_id,
                    user_id=user.id,
                    task_id=task.id,
                    title="测试视频",
                    download_url="http://example.com/test.mp4",
                    file_path="/tmp/test.mp4",
                    status="测试"
                )
                print(f"Video 对象创建成功: {video}")
                print(f"参数检查 - video_id: {video.video_id}(类型: {type(video.video_id)})")
                print(f"参数检查 - user_id: {video.user_id}(类型: {type(video.user_id)})")
                print(f"参数检查 - task_id: {video.task_id}(类型: {type(video.task_id)})")
                
                db.session.add(video)
                db.session.commit()
                print(f"视频记录创建成功，ID: {video.id}")
            except Exception as e:
                db.session.rollback()
                print(f"创建视频记录时出错: {str(e)}")
                print(f"错误类型: {type(e).__name__}")
                traceback.print_exc()
            
            # 查询数据库
            print("\n5. 查询数据库")
            users = User.query.all()
            print(f"用户数量: {len(users)}")
            
            tasks = DownloadTask.query.all()
            print(f"任务数量: {len(tasks)}")
            
            videos = Video.query.all()
            print(f"视频记录数量: {len(videos)}")
    
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        traceback.print_exc()

def test_main_db():
    """测试主应用数据库模式"""
    print("\n" + "="*50)
    print("测试 main.py 数据库模式")
    print("="*50)
    
    try:
        # 导入主应用模块
        from main import app, db, User, DownloadTask, Video
        
        # 测试应用上下文
        with app.app_context():
            print("\n1. 测试数据库连接")
            print(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print(f"数据库会话状态: {'活跃' if db.session.is_active else '非活跃'}")
            
            # 测试创建用户
            print("\n2. 测试创建用户")
            test_user_id = f"debug_main_user_{datetime.now().timestamp()}"
            print(f"创建测试用户: {test_user_id}")
            
            user = User(sec_id=test_user_id)
            db.session.add(user)
            db.session.commit()
            print(f"用户创建成功，ID: {user.id}")
            
            # 测试从主应用调用工具函数
            print("\n3. 测试从主应用调用工具函数")
            from tool import download_user_videos
            
            print(f"调用 download_user_videos 函数测试...")
            try:
                download_user_videos(test_user_id, user_id=user.id)
                print("调用成功")
            except Exception as e:
                print(f"调用工具函数时出错: {str(e)}")
                traceback.print_exc()
    
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='调试工具，用于测试数据库操作')
    parser.add_argument('mode', choices=['standalone', 'main', 'both'], 
                        help='测试模式: standalone=测试工具独立模式, main=测试主应用模式, both=两者都测试')
    
    args = parser.parse_args()
    
    if args.mode == 'standalone' or args.mode == 'both':
        test_standalone_db()
    
    if args.mode == 'main' or args.mode == 'both':
        test_main_db() 