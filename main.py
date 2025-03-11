from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return '欢迎来到Flask应用！'

@app.route('/hello')
def hello():
    return '你好，世界！'

if __name__ == '__main__':
    # 启用调试模式实现热更新
    app.debug = True
    # 绑定到8000端口
    app.run(host='0.0.0.0', port=8000) 
