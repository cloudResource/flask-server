# 导入蓝图对象
from . import passport_blue
# 导入flask内置的对象
from flask import request, jsonify, current_app, make_response, session
# 导入自定义的状态码
from info.utils.response_code import RET
# 导入captcha工具
from info.utils.captcha.captcha import captcha
# 导入redis对象
from info import redis_store,constants,db
# 导入正则
import re,random
# 导入云通讯
from info.libs.yuntongxun import sms
# 导入模型类
from info.models import User
# 导入日期模块
from datetime import datetime

@passport_blue.route("/image_code")
def generate_image_code():
    """
    生成图片验证码
    1、获取前端传入的参数，uuid
    2、检查参数是否存在，如果没传uuid，直接return
    3、调用captcha工具包，来生成图片验证码
    4、name，text，image来存储图片验证码到redis数据库中
    5、在info/__init__文件中实例化redis对象
    6、在redis中存储图片验证码的内容
    7、返回前端图片，使用make_response(image)
    :return:
    """
    # 获取参数,uuid
    image_code_id = request.args.get("image_code_id")
    # 如果参数不存在,直接结束程序运行
    if not image_code_id:
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 调用工具生成图片验证码,生成图片验证码的名称，文本、图片
    name,text,image = captcha.generate_captcha()
    # 把图片验证码的text文本，存储在redis中
    try:
        # redis_store.setex('ImageCode_' + image_code_id,300,text)
        redis_store.setex('ImageCode_' + image_code_id,constants.IMAGE_CODE_REDIS_EXPIRES,text)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='保存图片验证码失败')
    else:
        # 使用响应对象来返回图片
        response = make_response(image)
        # 设置响应类型为image/jpg
        response.headers['Content-Type'] = 'image/jpg'
        return response

@passport_blue.route('/sms_code',methods=['POST'])
def send_sms_code():
    """
    发送短信
    获取参数---检查参数---业务处理---返回结果
    1、获取参数，mobile，image_code(用户输入的图片验证码内容)，image_code_id(UUID)
    2、判断参数的完整性
    3、检查手机号的格式
    4、尝试从redis中获取真实的图片验证码
    5、都要删除redis中存储的图片验证码，因为图片验证码只能比较一次，比较一次的本质是只能对redis数据库get一次
    6、判断获取结果，如果图片验证码已过期，直接结束程序
    7、比较图片验证码是否正确
    8、生成短信验证码
    9、存储在redis数据库中，ImageCode_UUID,SMSCode_mobile
    10、调用云通讯，发送短信
    11、保存发送结果，判断发送是否成功
    12、返回结果

    :return:
    """
    # 获取参数
    mobile = request.json.get('mobile')
    image_code = request.json.get('image_code')
    image_code_id = request.json.get('image_code_id')
    # 检查参数的完整性
    if not all([mobile,image_code,image_code_id]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 检查手机号格式
    if not re.match(r'1[3456789]\d{9}$',mobile):
        return jsonify(errno=RET.PARAMERR,errmsg='手机号格式错误')

    # 从redis中获取图片验证码
    try:
        real_image_code = redis_store.get('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据失败')
    # 判断获取结果
    if not real_image_code:
        return jsonify(errno=RET.NODATA,errmsg='数据已过期')
    # 删除redis中存储的图片验证码
    try:
        redis_store.delete('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 比较图片验证码是否正确
    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR,errmsg='图片验证码不一致')
    # 根据手机号查询数据库，确认用户未注册，如果用户未注册，才发送短信
    try:
        user = User.query.filter(User.mobile==mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询用户数据失败')
    else:
        # 如果用户已存在
        if user:
            return jsonify(errno=RET.DATAEXIST,errmsg='手机号已注册')

    # 生成六位数的短信验证码
    sms_code = '%06d' % random.randint(0, 999999)
    print(sms_code)
    # 存储短信验证码到redis数据库
    try:
        redis_store.setex('SMSCode_' + mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 调用云通讯发送短信
    try:
        ccp = sms.CCP()
        result = ccp.send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIS_EXPIRES/60],1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='发送短信异常')
    # 判断发送的结果
    if result == 0:
        return jsonify(errno=RET.OK,errmsg='发送成功')
    else:
        return jsonify(errno=RET.THIRDERR,errmsg='发送失败')


@passport_blue.route("/register",methods=['POST'])
def register():
    """
    用户注册：
    获取参数---检查参数---业务处理---返回结果
    1、获取前端post请求的三个参数，mobile，sms_code,password
    2、检查参数的完整性
    3、检查手机号的格式
    4、尝试从redis数据库中获取真实的短信验证码
    5、判断真实的短信验证码是否存在
    6、比较短信验证码是否正确
    7、删除redis中存储的真实短信验证码，因为短信验证码可以比较多次，图片验证码只能比较一次
    8、使用模型类对象,准备存储数据
    user = User()
    user.password = password
    9、检查用户是否已注册
    10、如果未注册，提交用户信息到mysql数据库
    11、缓存用户信息到redis数据库中
    12、返回结果

    :return:
    """
    # 获取参数
    mobile = request.json.get('mobile')
    sms_code = request.json.get('sms_code')
    password = request.json.get('password')
    # 检查参数的完整性
    if not all([mobile,sms_code,password]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不完整')
    # 检查手机号格式
    if not re.match(r'1[3456789]\d{9}$',mobile):
        return jsonify(errno=RET.PARAMERR,errmsg='手机号格式错误')
    # 从redis数据库中获取真实的短信验证码
    try:
        real_sms_code = redis_store.get('SMSCode_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='获取短信验证码失败')
    # 判断获取结果
    if not real_sms_code:
        return jsonify(errno=RET.NODATA,errmsg='短信验证码已过期')
    # 比较短信验证码是否正确
    if real_sms_code != str(sms_code):
        return jsonify(errno=RET.DATAERR,errmsg='验证码不一致')
    # 删除redis中存储的短信验证码
    try:
        redis_store.delete('SMSCode_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
    # 根据手机号查询数据库，确认用户未注册
    try:
        user = User.query.filter(User.mobile==mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询用户数据失败')
    else:
        # 如果用户已存在
        if user:
            return jsonify(errno=RET.DATAEXIST,errmsg='手机号已注册')
    # 保存用户数据
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    # 实际上调用了模型类中的密码加密方法，实现了密码的密文存储
    user.password = password
    # 提交数据到mysql数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 如果提交数据失败，需要进行回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存用户数据失败')
    # 缓存用户信息到redis数据库中nick_name:18912341234
    session['user_id'] = user.id
    session['nick_name'] = mobile
    session['mobile'] = mobile
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')


@passport_blue.route("/login",methods=['POST'])
def login():
    """
    用户登录
    获取参数---检查参数---业务处理---返回结果
    1、获取前端post请求的参数，mobile，password
    2、检查参数的完整性
    3、检查手机号格式
    4、检查用户是否注册
    5、判断用户已注册
    6、判断密码正确
    7、保存用户的最后登录时间，提交用户登录时间到mysql数据库
    8、重新缓存用户信息，有可能修改用户昵称！？
    session['nick_name'] = user.nick_name
    9、返回结果
    :return:
    """
    # 获取post请求的参数
    mobile = request.json.get('mobile')
    password = request.json.get('password')
    # 检查参数完整性
    if not all([mobile,password]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 检查手机号格式
    if not re.match(r'1[3456789]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式错误')
    # 根据手机号查询mysql，确认用户已注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询用户数据失败')
    # 判断查询结果
    # if not user:
    #     return jsonify(errno=RET.NODATA,errmsg='用户未注册')
    # 加密模块
    # import hashlib
    # hashlib.sha256
    # 判断密码是否正确
    # if not user.check_password(password):
    #     return jsonify(errno=RET.PWDERR,errmsg='密码错误')

    # 判断用户不存在，密码是错误的
    if user is None or not user.check_password(password):
        return jsonify(errno=RET.DATAERR,errmsg='用户名或密码错误')
    # 保存用户的登录时间
    user.last_login = datetime.now()
    # 提交数据到mysql
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存用户数据失败')
    # 缓存用户信息
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')


@passport_blue.route("/logout")
def logout():
    """
    用户退出
    1、本质是清除redis中缓存的用户信息
    :return:
    """
    session.pop('user_id',None)
    session.pop('nick_name',None)
    session.pop('mobile',None)
    # 添加退出管理员操作
    session.pop('is_admin',None)
    return jsonify(errno=RET.OK,errmsg='OK')










    pass









