from flask import session, current_app, g
from info.models import User

# 自定义过滤器
def index_filter(index):
    if index == 0:
        return 'first'
    elif index == 1:
        return 'second'
    elif index == 2:
        return 'third'
    else:
        return ''

# 装饰器：函数嵌套函数，闭包，在不改变函数原有代码的前提下，添加新的功能
import functools

def login_required(f):
    @functools.wraps(f)
    def wrapper(*args,**kwargs):
        # 使用请求上下文对象，获取user_id
        user_id = session.get('user_id')
        user = None
        # 查询mysql，获取用户信息
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)
        # 使用应用上下文对象g,在请求过程中临时记录数据
        g.user = user
        return f(*args,**kwargs)
    # wrapper.__name__ = f.__name__
    return wrapper

