# 导入蓝图对象
from . import profile_blue
# 导入render_template
from flask import render_template, g, redirect, request, jsonify, current_app, session
# 导入登录验证装饰器
from info.utils.commons import login_required
# 导入自定义的状态码
from info.utils.response_code import RET
# 导入数据库实例db
from info import db,constants
# 导入七牛云扩展
from info.utils.image_storage import storage
# 导入模型类
from info.models import Category,News



@profile_blue.route('/info')
@login_required
def user_info():
    """
    用户中心基本页面信息展示
    1、模板加载页面数据
    2、如果用户未登录，重定向到项目首页
    3、展示用户的基本信息
    4、加载模板页面

    :return:
    """
    user = g.user
    if not user:
        return redirect('/')
    data = {
        'user':user.to_dict()
    }

    return render_template('news/user.html',data=data)

@profile_blue.route('/base_info',methods=['GET','POST'])
@login_required
def base_info():
    """
    用户基本信息页面
    既支持get请求，也支持post请求
    1、如果是post请求，获取参数，nick_name,signature,gender[MAN,WOMAN]
    2、检查参数的完整性
    3、检查gender参数在范围内
    4、保存用户信息
    5、提交数据
    6、返回结果
    :return:
    """
    user = g.user
    # 如果是get请求，加载模板页面
    if request.method == 'GET':

        data = {
            'user': user.to_dict()
        }
        return render_template('news/user_base_info.html',data=data)
    # 获取参数
    nick_name = request.json.get('nick_name')
    signature = request.json.get('signature')
    gender = request.json.get('gender')
    # 检查参数的完整性
    if not all([nick_name,signature,gender]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 检查性别参数
    if gender not in ['MAN','WOMAN']:
        return jsonify(errno=RET.PARAMERR,errmsg='参数类型错误')
    # 保存用户信息
    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender
    # 提交数据
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 修改redis中缓存的用户信息
    session['nick_name'] = user.nick_name

    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')

@profile_blue.route('/pic_info',methods=['GET','POST'])
@login_required
def save_avatar():
    """
    上传头像
    如果是get请求加载模板页面
    1、如果是post请求，获取图片文件，表单的name名称avatar
    avatar = request.files.get('avatar')
    2、判断参数存在
    3、把文件对象转成二进制数据，调用read方法
    4、调用七牛云，上传图片文件
    5、在mysql中存储七牛云返回的图片的key(图片名称)
    6、拼接图片的绝对地址：
    avatar_url = 七牛云空间的外链域名 + 七牛云返回的图片名称
    7、返回图片avatar_url

    :return:
    """
    user = g.user
    # 如果是get请求，加载模板页面
    if request.method == 'GET':
        data = {
            'user': user.to_dict()
        }
        return render_template('news/user_pic_info.html', data=data)
    # 获取图片参数
    avatar = request.files.get('avatar')
    # 判断参数存在
    if not avatar:
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 读取图片数据，转换成二进制bytes类型
    try:
        image_data = avatar.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数格式错误')
    # 调用七牛云，上传图片,七牛云会返回图片名称
    try:
        image_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='上传图片失败')
    # 保存图片名称到mysql
    user.avatar_url = image_name
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 拼接图片的绝对路径，返回前端
    avatar_url = constants.QINIU_DOMIN_PREFIX + image_name
    data = {
        'avatar_url':avatar_url
    }
    return jsonify(errno=RET.OK,errmsg='OK',data=data)

@profile_blue.route('/news_release',methods=['GET','POST'])
@login_required
def news_release():
    """
    新闻发布
    如果是get请求，加载新闻分类数据,需要移除'最新'分类
    1、如果是post请求，获取参数，title，category_id,digest,index_image,content
    2、检查参数的完整性
    3、转换分类id的数据类型
    4、读取图片数据
    5、调用七牛云，上传图片
    6、保存新闻数据，构造模型类News对象
    user_id/source/status
    7、返回结果


    :return:
    """
    user = g.user
    if request.method == 'GET':
        # 查询新闻分类
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg='查询新闻分类数据失败')
        # 判断查询结果
        if not categories:
            return jsonify(errno=RET.NODATA,errmsg='无新闻分类数据')
        # 定义容器存储查询结果
        category_list = []
        for category in categories:
            category_list.append(category.to_dict())
        # 移除最新分类
        category_list.pop(0)
        data = {
            'categories':category_list
        }
        return render_template('news/user_news_release.html',data=data)

    # 获取参数
    title = request.form.get('title')
    digest = request.form.get('digest')
    category_id = request.form.get('category_id')
    index_image = request.files.get('index_image')
    content = request.form.get('content')
    # 检查参数的完整性
    if not all([title,digest,category_id,index_image,content]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不完整')
    # 转换数据类型
    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数类型错误')
    # 读取图片数据
    try:
        image_data = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数格式错误')
    # 调用七牛云上传图片
    try:
        image_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='上传图片失败')
    # 构造模型类对象，准备存储新闻数据
    news = News()
    news.category_id = category_id
    news.user_id = user.id
    news.title = title
    news.source = '个人发布'
    news.digest = digest
    # 新闻图片对于新闻来说是个整体，存储的是绝对路径。
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    news.status = 1
    news.content = content
    # 提交数据到mysql中
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')











