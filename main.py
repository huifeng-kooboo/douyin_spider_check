from flask import Flask, render_template, request, jsonify
import threading
import uuid
from tool import download_user_videos

app = Flask(__name__)

# 存储线程信息的字典
threads_info = {}

@app.route('/')
def home():
    return '欢迎来到Flask应用！'

@app.route('/hello')
def hello():
    return '你好，世界！'

@app.route('/download_videos', methods=['POST'])
def create_download_thread():
    try:
        data = request.json
        if not data or 'sec_id_list' not in data:
            return jsonify({"error": "请提供sec_id_list参数"}), 400
        
        sec_id_list = data['sec_id_list']
        if not isinstance(sec_id_list, list):
            return jsonify({"error": "sec_id_list必须是列表"}), 400
        
        thread_ids = []
        
        # 为每个sec_id创建一个下载线程
        for sec_id in sec_id_list:
            thread_id = str(uuid.uuid4())
            thread = threading.Thread(target=download_task, args=(thread_id, sec_id))
            thread.daemon = True
            
            # 初始化线程信息
            threads_info[thread_id] = {
                "sec_id": sec_id,
                "status": "准备中",
                "created_at": threading.current_thread().name,
                "thread": thread,
                "videos_downloaded": 0,
                "error": None
            }
            
            # 启动线程
            thread.start()
            thread_ids.append(thread_id)
        
        return jsonify({
            "message": "下载任务已创建",
            "thread_ids": thread_ids
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/thread_status/<thread_id>', methods=['GET'])
def get_thread_status(thread_id):
    if thread_id not in threads_info:
        return jsonify({"error": "未找到指定的线程ID"}), 404
    
    thread_info = threads_info[thread_id].copy()
    thread_info.pop('thread', None)  # 移除线程对象，无法序列化
    
    return jsonify(thread_info)

@app.route('/all_threads', methods=['GET'])
def get_all_threads():
    result = {}
    for thread_id, info in threads_info.items():
        thread_info = info.copy()
        thread_info.pop('thread', None)  # 移除线程对象，无法序列化
        result[thread_id] = thread_info
    
    return jsonify(result)

def download_task(thread_id, sec_id):
    try:
        # 更新线程状态为运行中
        threads_info[thread_id]["status"] = "运行中"
        
        # 调用下载函数
        download_user_videos(sec_id)
        
        # 更新线程状态为已完成
        threads_info[thread_id]["status"] = "已完成"
    
    except Exception as e:
        # 更新线程状态为出错
        threads_info[thread_id]["status"] = "出错"
        threads_info[thread_id]["error"] = str(e)

if __name__ == '__main__':
    # 启用调试模式实现热更新
    app.debug = True
    # 绑定到8000端口
    app.run(host='0.0.0.0', port=8000) 
