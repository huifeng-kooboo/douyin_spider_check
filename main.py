from flask import Flask, render_template, request, jsonify
import threading
import uuid
import os
from datetime import datetime
from tool import download_user_videos
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api, Resource, fields, Namespace
from flask_cors import CORS

app = Flask(__name__)

# 配置跨域请求支持
CORS(app, resources={r"/*": {"origins": "*"}})

# 配置SQLite数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'douyin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 初始化Flask-RestX API
api = Api(
    app,
    version='1.0',
    title='抖音视频下载与比较API',
    description='用于下载抖音视频、管理下载任务和比较视频相似度的API',
    doc='/swagger',  # 访问Swagger UI的路径
    default='API',
    default_label='抖音视频下载与比较API接口'
)

# 创建命名空间
ns_download = api.namespace('download', description='下载视频相关操作')
ns_task = api.namespace('task', description='任务状态相关操作')
ns_video = api.namespace('video', description='视频信息相关操作')

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

# 定义Swagger API模型
sec_id_list_model = api.model('SecIdList', {
    'sec_id_list': fields.List(fields.String, required=True, description='抖音用户sec_id列表')
})

download_response_model = api.model('DownloadResponse', {
    'message': fields.String(description='操作结果消息'),
    'thread_ids': fields.List(fields.String, description='下载任务线程ID列表')
})

thread_status_model = api.model('ThreadStatus', {
    'sec_id': fields.String(description='抖音用户sec_id'),
    'status': fields.String(description='任务状态(准备中/运行中/已完成/出错)'),
    'created_at': fields.String(description='任务创建时间'),
    'videos_downloaded': fields.Integer(description='已下载视频数量'),
    'error': fields.String(description='错误信息(如果有的话)')
})

video_info_model = api.model('VideoInfo', {
    'id': fields.Integer(description='视频记录ID'),
    'video_id': fields.String(description='抖音视频ID'),
    'title': fields.String(description='视频标题'),
    'download_url': fields.String(description='下载链接'),
    'file_path': fields.String(description='本地文件路径'),
    'status': fields.String(description='下载状态'),
    'created_at': fields.String(description='创建时间'),
    'updated_at': fields.String(description='更新时间')
})

user_videos_model = api.model('UserVideos', {
    'user': fields.Nested(api.model('User', {
        'id': fields.Integer(description='用户ID'),
        'sec_id': fields.String(description='抖音用户sec_id'),
        'created_at': fields.String(description='创建时间')
    })),
    'videos': fields.List(fields.Nested(video_info_model))
})

# 主页接口
@app.route('/')
def home():
    return '欢迎来到Flask应用！'

# 测试接口
@app.route('/hello')
def hello():
    return '你好，世界！'

# 视频下载接口
@ns_download.route('')
class DownloadVideos(Resource):
    @ns_download.expect(sec_id_list_model)
    @ns_download.response(200, '成功创建下载任务', download_response_model)
    @ns_download.response(400, '请求参数错误')
    @ns_download.response(500, '服务器内部错误')
    def post(self):
        """
        创建视频下载任务
        
        根据提供的sec_id_list列表，为每个用户创建一个下载线程，并返回线程ID列表
        """
        try:
            data = request.json
            if not data or 'sec_id_list' not in data:
                return {'error': '请提供sec_id_list参数'}, 400
            
            sec_id_list = data['sec_id_list']
            if not isinstance(sec_id_list, list):
                return {'error': 'sec_id_list必须是列表'}, 400
            
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
            
            return {
                "message": "下载任务已创建",
                "thread_ids": thread_ids
            }
        
        except Exception as e:
            return {'error': str(e)}, 500

# 获取特定线程状态接口
@ns_task.route('/<string:thread_id>')
@ns_task.param('thread_id', '任务线程ID')
class ThreadStatus(Resource):
    @ns_task.response(200, '成功获取线程状态', thread_status_model)
    @ns_task.response(404, '未找到指定的线程ID')
    def get(self, thread_id):
        """
        获取特定下载任务的状态
        
        根据线程ID返回任务状态、进度等信息
        """
        if thread_id not in threads_info:
            # 尝试从数据库查询
            task = DownloadTask.query.filter_by(thread_id=thread_id).first()
            if not task:
                return {'error': '未找到指定的线程ID'}, 404
            
            # 返回数据库中的任务状态
            task_dict = task.to_dict()
            user = User.query.get(task.user_id)
            task_dict['sec_id'] = user.sec_id if user else None
            return task_dict
        
        thread_info = threads_info[thread_id].copy()
        thread_info.pop('thread', None)  # 移除线程对象，无法序列化
        
        # 添加数据库中的视频计数
        task = DownloadTask.query.filter_by(thread_id=thread_id).first()
        if task:
            thread_info['videos_count'] = len(task.videos)
        
        return thread_info

# 获取所有线程状态接口
@ns_task.route('/all')
class AllThreads(Resource):
    @ns_task.response(200, '成功获取所有线程状态')
    def get(self):
        """
        获取所有下载任务的状态
        
        返回所有下载任务的状态信息列表
        """
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
        
        return result

# 获取用户视频列表接口
@ns_video.route('/user/<string:sec_id>')
@ns_video.param('sec_id', '抖音用户sec_id')
class UserVideos(Resource):
    @ns_video.response(200, '成功获取用户视频', user_videos_model)
    @ns_video.response(404, '未找到该用户')
    def get(self, sec_id):
        """
        获取特定用户的所有视频信息
        
        根据用户sec_id返回该用户的所有视频信息列表
        """
        user = User.query.filter_by(sec_id=sec_id).first()
        if not user:
            return {'error': '未找到该用户'}, 404
        
        videos = Video.query.filter_by(user_id=user.id).all()
        return {
            "user": user.to_dict(),
            "videos": [video.to_dict() for video in videos]
        }

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
