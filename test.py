# test
from util.douyin_util import DouYinUtil
import requests
import json
import time

# 测试下载单个用户视频的原始方法
def test_download_single_user():
    dy_util = DouYinUtil(sec_uid="MS4wLjABAAAAah62GbBN8fQXHTYIT18z6BV3HB5wt4_H5tYyYn_3Npy56HxUx3uEOk5a5VIL5_Bn")
    all_video_list = dy_util.get_all_videos()
    for video_id in all_video_list:
        video_info = dy_util.get_video_detail_info(video_id)
        if video_info['is_video'] is True:
            print(f"视频下载链接:{video_info['link']}")
            dy_util.download_video(video_info['link'], f"{video_id}.mp4")

# 测试通过API接口下载多个用户视频
def test_api_download():
    # 定义要下载的用户sec_id列表
    sec_ids = [
        "MS4wLjABAAAAah62GbBN8fQXHTYIT18z6BV3HB5wt4_H5tYyYn_3Npy56HxUx3uEOk5a5VIL5_Bn",
        # 可以添加更多sec_id
    ]
    
    # 调用下载接口
    response = requests.post(
        "http://localhost:8000/download",
        json={"sec_id_list": sec_ids},
        headers={"Content-Type": "application/json"}
    )
    
    # 检查响应
    if response.status_code == 200:
        result = response.json()
        print("下载任务已创建:", result)
        
        # 获取线程ID
        thread_ids = result.get("thread_ids", [])
        
        # 监控下载进度
        if thread_ids:
            monitor_download_progress(thread_ids[0])
    else:
        print("调用接口失败:", response.text)

# 监控下载进度
def monitor_download_progress(thread_id, interval=5):
    print(f"开始监控线程 {thread_id} 的状态...")
    
    # 循环检查线程状态
    while True:
        response = requests.get(f"http://localhost:8000/task/{thread_id}")
        
        if response.status_code == 200:
            status = response.json()
            print(f"线程状态: {json.dumps(status, ensure_ascii=False, indent=2)}")
            
            # 如果任务已完成或出错，退出循环
            if status.get("status") in ["已完成", "出错"]:
                print("任务已结束")
                break
        else:
            print(f"获取状态失败: {response.text}")
            break
        
        # 等待一段时间再次检查
        time.sleep(interval)

# 获取所有线程状态
def get_all_threads_status():
    response = requests.get("http://localhost:8000/task/all")
    if response.status_code == 200:
        all_threads = response.json()
        print("所有线程状态:")
        print(json.dumps(all_threads, ensure_ascii=False, indent=2))
    else:
        print("获取所有线程状态失败:", response.text)

# 获取用户视频列表
def get_user_videos(sec_id):
    response = requests.get(f"http://localhost:8000/video/user/{sec_id}")
    if response.status_code == 200:
        user_videos = response.json()
        print(f"用户 {sec_id} 的视频列表:")
        print(json.dumps(user_videos, ensure_ascii=False, indent=2))
    else:
        print("获取用户视频列表失败:", response.text)

# 打开Swagger文档
def open_swagger_doc():
    import webbrowser
    webbrowser.open("http://localhost:8000/swagger")
    print("已在浏览器打开Swagger文档")

if __name__ == "__main__":
    # 取消下面的注释来运行相应的测试
    # test_download_single_user()  # 使用原始方法下载单个用户视频
    # test_api_download()  # 使用API接口下载多个用户视频
    # get_all_threads_status()  # 获取所有线程状态
    # get_user_videos("MS4wLjABAAAAah62GbBN8fQXHTYIT18z6BV3HB5wt4_H5tYyYn_3Npy56HxUx3uEOk5a5VIL5_Bn")  # 获取用户视频列表
    # open_swagger_doc()  # 打开Swagger文档
    
    print("请取消注释选择要运行的测试函数")



