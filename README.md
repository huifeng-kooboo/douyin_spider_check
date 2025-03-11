# Flask 简易服务器

这是一个简单的Flask应用程序，绑定在8000端口并支持热更新。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行应用

```bash
python main.py
```

服务器将在 http://localhost:8000 上启动。

## 可用路由

- `/` - 主页
- `/hello` - 问候页面
- `/download_videos` - 接收sec_id_list创建下载线程（POST）
- `/thread_status/<thread_id>` - 获取特定线程状态（GET）
- `/all_threads` - 获取所有线程状态（GET）
- `/user_videos/<sec_id>` - 获取用户所有视频信息（GET）

## 特性

- 支持热更新（在开发模式下，修改代码后自动重启服务器）
- 绑定到8000端口
- 多线程下载抖音视频
- 线程状态跟踪
- SQLite数据库存储用户和视频信息

## 数据库结构

应用使用SQLite数据库存储信息，包含以下表：

### 用户表 (User)
- `id`: 主键
- `sec_id`: 抖音用户的sec_id
- `created_at`: 创建时间

### 下载任务表 (DownloadTask)
- `id`: 主键
- `thread_id`: 线程ID
- `user_id`: 关联到User表的外键
- `status`: 任务状态(准备中/运行中/已完成/出错)
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `error`: 错误信息(如果有的话)

### 视频表 (Video)
- `id`: 主键
- `video_id`: 抖音视频ID
- `user_id`: 关联到User表的外键
- `task_id`: 关联到DownloadTask表的外键
- `title`: 视频标题
- `download_url`: 下载链接
- `file_path`: 本地文件路径
- `status`: 下载状态(待下载/下载中/已下载/出错)
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 工具函数

### 视频比较功能

在`tool.py`中提供了视频比较功能：

```python
from tool import compare_video

# 比较两个视频文件
result = compare_video("视频1.mp4", "视频2.mp4", 95)
if result:
    print("这两个视频非常相似")
else:
    print("这两个视频不相似")
```

参数说明：
- 第一个参数：第一个视频文件路径
- 第二个参数：第二个视频文件路径
- 第三个参数：相似度阈值（默认95%）

比较逻辑：
当两个视频中有超过指定阈值（默认95%）的帧图像相似时，返回True，否则返回False。

### 视频下载接口

#### 创建下载任务

POST `/download_videos`

请求体:
```json
{
  "sec_id_list": ["用户sec_id1", "用户sec_id2", ...]
}
```

响应:
```json
{
  "message": "下载任务已创建",
  "thread_ids": ["线程ID1", "线程ID2", ...]
}
```

#### 获取线程状态

GET `/thread_status/<thread_id>`

响应:
```json
{
  "sec_id": "用户sec_id",
  "status": "准备中|运行中|已完成|出错",
  "created_at": "线程创建时间",
  "videos_downloaded": 0,
  "error": null
}
```

#### 获取所有线程状态

GET `/all_threads`

响应:
```json
{
  "线程ID1": {
    "sec_id": "用户sec_id",
    "status": "状态",
    "created_at": "线程创建时间",
    "videos_downloaded": 0,
    "error": null
  },
  "线程ID2": {
    ...
  }
}
```

#### 获取用户视频列表

GET `/user_videos/<sec_id>`

响应:
```json
{
  "user": {
    "id": 1,
    "sec_id": "用户sec_id",
    "created_at": "创建时间"
  },
  "videos": [
    {
      "id": 1,
      "video_id": "视频ID",
      "title": "视频标题",
      "download_url": "下载链接",
      "file_path": "本地文件路径",
      "status": "下载状态",
      "created_at": "创建时间",
      "updated_at": "更新时间"
    },
    ...
  ]
}
```

## 使用示例

在`test.py`中提供了使用示例：

```python
# 使用API下载视频
test_api_download()

# 监控线程状态
monitor_download_progress(thread_id)

# 获取所有线程状态
get_all_threads_status()
```
