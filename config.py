# 导入redis实例
from redis import StrictRedis
# 自定义配置类
class Config:
    # 开启调试模式
    DEBUG = None
    # session信息存储的位置
    SECRET_KEY = 'rbZCMXxPLbxg0GmNipGjjxnF0oXrzVHGJQRNoJvkatsojjqZ5NjjYF6hTh+F'

    # 连接mysql的配置
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@localhost/info'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 定义redis的主机和端口
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    SESSION_TYPE = 'redis'
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    # 对session信息进行签名
    SESSION_USE_SIGNER = True
    # flask框架自带的配置session有效期
    PERMANENT_SESSION_LIFETIME = 86400

# 自定义开发模式下的配置类
class DevelopmentConfig(Config):
    DEBUG = True

# 自定义生产模式下的配置类
class ProductionConfig(Config):
    DEBUG = False


# 定义字段，来映射不同的的配置类
config_dict = {
    'development':DevelopmentConfig,
    'production':ProductionConfig
}