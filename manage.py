# 导入脚本管理器
from flask_script import Manager
# 从info目录下的__init__文件中导入创建app的函数
from info import create_app,db,models
# 使用数据库迁移框架
from flask_migrate import Migrate,MigrateCommand

from info.models import User
# 调用info目录下的__init__文件的函数

app = create_app('development')

# 实例化管理器对象
manage = Manager(app)
# 使用迁移框架
Migrate(app,db)
# 添加迁移命令
manage.add_command('db',MigrateCommand)



# 创建管理员账户
# 在script扩展，自定义脚本命令，以自定义函数的形式实现创建管理员用户
# 以终端启动命令的形式实现；
# 在终端使用命令：python manage.py create_supperuser -n admin -p 123456
@manage.option('-n', '-name', dest='name')
@manage.option('-p', '-password', dest='password')
def create_supperuser(name, password):
    if not all([name, password]):
        print('参数缺失')
    user = User()
    user.nick_name = name
    user.mobile = name
    user.password = password
    user.is_admin = True
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(e)
    print('管理员创建成功')




if __name__ == '__main__':
    # app.run()
    print(app.url_map)
    manage.run()

