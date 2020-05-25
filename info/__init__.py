# 导入flask内置的模块
from flask import Flask
# 导入配置
from config import Config,config_dict
# 把session存储在redis数据库中
from flask_session import Session
# 使用标准日志模块
import logging
from logging.handlers import RotatingFileHandler
# 导入flask_sqlalchemy
from flask_sqlalchemy import SQLAlchemy
# 导入redis的模块
from redis import StrictRedis
# 导入flask_wtf扩展提供的csrf保护的功能
from flask_wtf import CSRFProtect,csrf



# 设置日志的记录等级
logging.basicConfig(level=logging.DEBUG) # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)

# 实例化redis对象，用来存储和业务逻辑相关的数据，比如图片验证码
redis_store = StrictRedis(host=Config.REDIS_HOST,port=Config.REDIS_PORT,decode_responses=True)

# 实例化sqlalchemy对象
db = SQLAlchemy()

# 封装函数，用来创建程序实例app，让app根据函数的调用来生产不同环境下的app
# config_name=development会创建一个开发模式的app，debug=True
# config_name=production会创建一个生产模式的app，debug=False
def create_app(config_name):
    app = Flask(__name__)
    # 使用配置类
    app.config.from_object(config_dict[config_name])

    # 实例化Session
    Session(app)
    # 通过使用db的init_app方法，让db和程序实例app进行关联
    db.init_app(app)

    # 开启csrf保护
    CSRFProtect(app)

    # 生成csrf_token，并且写入到客户端浏览器的cookie中
    # 请求钩子，在每次请求后都执行,给客户端写入csrf_token
    @app.after_request
    def after_request(response):
        csrf_token = csrf.generate_csrf()
        response.set_cookie('csrf_token',csrf_token)
        return response

    # 导入自定义的过滤器
    from info.utils.commons import index_filter
    app.add_template_filter(index_filter,'index_filter')

    # 导入蓝图，注册蓝图
    from info.modules.news import news_blue
    app.register_blueprint(news_blue)
    from info.modules.passport import passport_blue
    app.register_blueprint(passport_blue)
    from info.modules.profile import profile_blue
    app.register_blueprint(profile_blue)
    from info.modules.admin import admin_blue
    app.register_blueprint(admin_blue)

    return app


