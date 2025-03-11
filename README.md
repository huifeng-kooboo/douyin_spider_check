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

## 特性

- 支持热更新（在开发模式下，修改代码后自动重启服务器）
- 绑定到8000端口

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
