from flask import Flask, render_template, request, jsonify
import threading
import uuid
import os
from datetime import datetime
from tool import download_user_videos
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 配置SQLite数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'douyin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 定义数据模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sec_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    tasks = db.relationship('DownloadTask', backref='user', lazy=True)
    videos = db.relationship('Video', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.sec_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sec_id': self.sec_id,
            'created_at': self.created_at.isoformat()
        }

class DownloadTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='准备中')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    error = db.Column(db.Text, nullable=True)
    
    videos = db.relationship('Video', backref='task', lazy=True)
    
    def __repr__(self):
        return f'<DownloadTask {self.thread_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'error': self.error,
            'videos_count': len(self.videos)
        }

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('download_task.id'), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    download_url = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='待下载')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Video {self.video_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'title': self.title,
            'download_url': self.download_url,
            'file_path': self.file_path,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# 创建数据库表
with app.app_context():
    db.create_all()

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
            # 查找或创建用户记录
            user = User.query.filter_by(sec_id=sec_id).first()
            if not user:
                user = User(sec_id=sec_id)
                db.session.add(user)
                db.session.commit()
            
            # 创建下载任务记录
            thread_id = str(uuid.uuid4())
            db_task = DownloadTask(thread_id=thread_id, user_id=user.id)
            db.session.add(db_task)
            db.session.commit()
            
            # 创建线程
            thread = threading.Thread(target=download_task, args=(thread_id, sec_id, user.id, db_task.id))
            thread.daemon = True
            
            # 初始化线程信息
            threads_info[thread_id] = {
                "sec_id": sec_id,
                "status": "准备中",
                "created_at": threading.current_thread().name,
                "thread": thread,
                "videos_downloaded": 0,
                "error": None,
                "db_task_id": db_task.id
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
        # 尝试从数据库查询
        task = DownloadTask.query.filter_by(thread_id=thread_id).first()
        if not task:
            return jsonify({"error": "未找到指定的线程ID"}), 404
        
        # 返回数据库中的任务状态
        task_dict = task.to_dict()
        user = User.query.get(task.user_id)
        task_dict['sec_id'] = user.sec_id if user else None
        return jsonify(task_dict)
    
    thread_info = threads_info[thread_id].copy()
    thread_info.pop('thread', None)  # 移除线程对象，无法序列化
    
    # 添加数据库中的视频计数
    task = DownloadTask.query.filter_by(thread_id=thread_id).first()
    if task:
        thread_info['videos_count'] = len(task.videos)
    
    return jsonify(thread_info)

@app.route('/all_threads', methods=['GET'])
def get_all_threads():
    result = {}
    
    # 从内存中获取活跃线程
    for thread_id, info in threads_info.items():
        thread_info = info.copy()
        thread_info.pop('thread', None)  # 移除线程对象，无法序列化
        result[thread_id] = thread_info
    
    # 从数据库获取所有任务状态
    tasks = DownloadTask.query.all()
    for task in tasks:
        if task.thread_id not in result:  # 避免重复添加活跃线程
            task_dict = task.to_dict()
            user = User.query.get(task.user_id)
            task_dict['sec_id'] = user.sec_id if user else None
            result[task.thread_id] = task_dict
    
    return jsonify(result)

@app.route('/user_videos/<sec_id>', methods=['GET'])
def get_user_videos(sec_id):
    user = User.query.filter_by(sec_id=sec_id).first()
    if not user:
        return jsonify({"error": "未找到该用户"}), 404
    
    videos = Video.query.filter_by(user_id=user.id).all()
    return jsonify({
        "user": user.to_dict(),
        "videos": [video.to_dict() for video in videos]
    })

def download_task(thread_id, sec_id, user_id, task_id):
    try:
        # 更新线程状态为运行中
        threads_info[thread_id]["status"] = "运行中"
        
        # 更新数据库任务状态
        task = DownloadTask.query.get(task_id)
        if task:
            task.status = "运行中"
            db.session.commit()
        
        # 调用下载函数并获取视频信息
        videos_info = download_user_videos(sec_id, task_id, user_id)
        
        # 更新视频下载计数
        if videos_info and isinstance(videos_info, list):
            threads_info[thread_id]["videos_downloaded"] = len(videos_info)
        
        # 更新线程状态为已完成
        threads_info[thread_id]["status"] = "已完成"
        
        # 更新数据库任务状态
        if task:
            task.status = "已完成"
            db.session.commit()
    
    except Exception as e:
        # 更新线程状态为出错
        threads_info[thread_id]["status"] = "出错"
        threads_info[thread_id]["error"] = str(e)
        
        # 更新数据库任务状态
        task = DownloadTask.query.get(task_id)
        if task:
            task.status = "出错"
            task.error = str(e)
            db.session.commit()

if __name__ == '__main__':
    # 启用调试模式实现热更新
    app.debug = True
    # 绑定到8000端口
    app.run(host='0.0.0.0', port=8000) 
