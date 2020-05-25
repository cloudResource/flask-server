from flask import Blueprint
# 创建蓝图对象

profile_blue = Blueprint('profile_blue',__name__,url_prefix='/user')


from . import views
