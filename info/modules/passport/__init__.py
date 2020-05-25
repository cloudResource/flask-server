# 创建蓝图对象
from flask import Blueprint

passport_blue = Blueprint('passport_blue',__name__)

from . import views