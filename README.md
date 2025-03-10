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
