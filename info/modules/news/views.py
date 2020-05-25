# 导入flask内置的模块
from flask import session, render_template, current_app, jsonify, request, g
# 从news/__init__文件中导入蓝图对象
from info.utils.response_code import RET
from . import news_blue
# 导入User模型类
from info.models import User, Category, News, Comment, CommentLike
# 导入常量文件
from info import constants,db
# 导入登录验证装饰器
from info.utils.commons import login_required


@news_blue.route('/')
@login_required
def index():
    """
    项目首页数据加载
        一、检查用户的登录状态：
        1、如果用户登录了，显示用户名信息，否则提供登录注册入口。
        2、使用session对象，从redis中获取user_id。
        3、根据user_id，查询mysql，获取用户信息
        4、传给模板
        二、新闻分类数据加载
        1、查询mysql，获取新闻分类数据
        三、点击排行
        1、查询mysql，获取新闻点击排行
        按点击量展示6条新闻

    :return:
    """
    # 使用请求上下文对象，获取user_id
    # user_id = session.get('user_id')
    # user = None
    # # 查询mysql，获取用户信息
    # try:
    #     # User.query.filter_by(id=user_id).first()
    #     # User.query.filter(User.id==user_id).first()
    #     user = User.query.get(user_id)
    # except Exception as e:
    #     current_app.logger.error(e)

    user = g.user

    # 新闻分类数据加载
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻分类数据失败')
    # 判断查询结果
    if not categories:
        return jsonify(errno=RET.NODATA,errmsg='无新闻分类数据')
    # 定义列表，用来存储遍历后的新闻分类数据
    category_list = []
    # 遍历查询结果，调用模型类中to_dict函数，获取数据
    for category in categories:
        category_list.append(category.to_dict())

    # 查询新闻点击排行
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻点击排行数据失败')
    # 判断查询结果
    if not news_list:
        return jsonify(errno=RET.NODATA,errmsg='无新闻点击排行数据')
    # 定义列表，存储查询结果
    news_click_list = []
    for news in news_list:
        news_click_list.append(news.to_dict())



    # 定义字典，用来存储返回给模板的数据
    data = {
        'user_info':user.to_dict() if user else None,
        'category_list':category_list,
        'news_click_list':news_click_list
    }
    return render_template('news/index.html',data=data)

@news_blue.route("/news_list")
def get_news_list():
    """
    首页新闻列表
    1、获取参数，ajax发送get请求cid、page、per_page
    request.args.get('page','1')
    2、检查参数，把cid，page/per_page转成int类型
    3、判断分类id
    如果是最新分类：查询所有新闻
    paginate = News.query.filter().order_by(News.create_time.desc()).paginate(1,per_page,False)
    如果不是最新分类，根据分类查询新闻
    paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()).paginate(1,per_page,False)
    4、获取分页后的新闻列表、总页数、当前页数
    5、定义容器，遍历新闻列表
    6、返回总页数、当前页数、新闻列表

    :return:
    """
    # 获取参数，如果有参数获取，没有给默认值
    cid = request.args.get('cid','1')
    page = request.args.get('page','1')
    per_page = request.args.get('per_page','10')
    # 转换数据类型
    try:
        cid,page,per_page = int(cid),int(page),int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数类型错误')
    filters = []
    # 判断新闻分类，如果不是最新，添加到过滤条件的列表中。
    if cid > 1:
        filters.append(News.category_id == cid)
    # 根据filters过滤条件查询mysql
    try:
        # *filters是python语法中的拆包。
        # paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()).paginate(page,per_page,False)
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,per_page,False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻列表数据失败')
    # 获取分页后的数据
    news_list = paginate.items # 新闻数据
    current_page = paginate.page # 当前页数
    total_page = paginate.pages # 总页数
    # 定义容器，存储分页的新闻列表数据
    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_dict())
    # 定义字典
    data = {
        'news_dict_list':news_dict_list,
        'current_page':current_page,
        'total_page':total_page
    }
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK',data=data)


@news_blue.route('/<int:news_id>')
@login_required
def get_news_detail(news_id):
    """
    新闻详情
    :param news_id:
    :return:
    """
    user = g.user
    # 使用请求上下文对象，获取user_id
    # user_id = session.get('user_id')
    # user = None
    # # 查询mysql，获取用户信息
    # try:
    #     # User.query.filter_by(id=user_id).first()
    #     # User.query.filter(User.id==user_id).first()
    #     user = User.query.get(user_id)
    # except Exception as e:
    #     current_app.logger.error(e)

    # 查询新闻点击排行
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询新闻点击排行数据失败')
    # 判断查询结果
    if not news_list:
        return jsonify(errno=RET.NODATA, errmsg='无新闻点击排行数据')
    # 定义列表，存储查询结果
    news_click_list = []
    for news in news_list:
        news_click_list.append(news.to_dict())

    # 根据新闻id查询具体的新闻
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻详情数据失败')
    # 判断查询结果
    if not news:
        return jsonify(errno=RET.NODATA,errmsg='无新闻详情数据')

    # 新闻点击次数加1
    news.clicks += 1
    # 提交数据
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')


    # 评论
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
    comment_like_ids = []
    # 获取当前登录用户的所有评论的id，
    if user:
        try:
            comment_ids = [comment.id for comment in comments]
            # 再查询点赞了哪些评论
            comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                     CommentLike.user_id == g.user.id).all()
            # 遍历点赞的评论数据,获取
            comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]
        except Exception as e:
            current_app.logger.error(e)
    comment_dict_li = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 如果未点赞
        comment_dict['is_like'] = False
        # 如果点赞
        if comment.id in comment_like_ids:
            comment_dict['is_list'] = True
        comment_dict_li.append(comment_dict)



    # 是否收藏的标记
    is_collected = False
    if user and news in user.collection_news:
        is_collected = True

    data = {
        'user_info': user.to_dict() if user else None,
        'news_click_list': news_click_list,
        'news_detail':news.to_dict(),
        'is_collected':is_collected
    }

    # 渲染模板
    return render_template('news/detail.html',data=data)

@news_blue.route('/news_collect',methods=['POST'])
@login_required
def news_collection():
    """
        用户收藏或取消收藏
        1、判断用户是否登录
        2、获取参数，news_id，action['cancel_collect','collect']
        3、检查参数，news_id转成int类型
        4、判断action在参数范围内
        5、查询数据库，确认新闻存在
        6、判断用户选择的是收藏还是取消收藏
        7、返回结果


        get_json方法，作用是获取前端传入的完整的json字符串
        params = request.get_json()
        params.get('news_id')
        params.get('action')

        :return:
        """
    user = g.user
    # 如果用户未登录
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
    # 获取参数
    news_id = request.json.get('news_id')
    action = request.json.get('action')
    # 检查参数的完整性
    if not all([news_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数类型错误')
    # 检查action必须在范围内
    if action not in ['collect','cancel_collect']:
        return jsonify(errno=RET.PARAMERR,errmsg='参数范围错误')
    # 查询新闻
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻数据失败')
    # 判断查询结果
    if not news:
        return jsonify(errno=RET.NODATA,errmsg='无新闻数据')
    # 如果参数是收藏
    if action == 'collect':
        # 判断用户是否收藏过
        if news not in user.collection_news:
            user.collection_news.append(news)
    else:
        user.collection_news.remove(news)
    # 提交数据
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')

    return jsonify(errno=RET.OK,errmsg='OK')
    
        






@news_blue.route('/news_comment',methods=['POST'])
@login_required
def comments_news():
    """
    评论新闻
    1、判断用户是否登录
    2、获取参数，news_id,comment,parent_id
    3、检查参数的完整
    4、校验news_id,parent_id转成整型
    5、根据news_id查询数据库
    6、实例化评论表对象，保存评论id、新闻id，新闻内容，如果有父评论id
    7、提交数据返回data = comment.to_dict()

    :return:
    """
    # 确定用户已登录
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
    # 获取参数，新闻id、父评论id、评论内容
    news_id = request.json.get('news_id')
    parent_id = request.json.get('parent_id')
    content = request.json.get('comment')
    if not all([news_id,content]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    try:
        news_id = int(news_id)
        if parent_id:
            parent_id = int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数格式错误')
    # 根据新闻id查询数据库
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据失败')
    # 判断查询结果
    if not news:
        return jsonify(errno=RET.NODATA,errmsg='数据不存在')
    # 构造模型类对象，准备存储数据
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = content
    # 如果有父评论id
    if parent_id:
        comment.parent_id = parent_id
    # 提交数据
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')

    return jsonify(errno=RET.OK,errmsg='OK',data=comment.to_dict())


@news_blue.route('/comment_like',methods=['POST'])
@login_required
def comment_like():
    """
    点赞或取消点赞
    1、获取用户登录信息
    2、获取参数，comment_id,action
    3、检查参数的完整性
    4、判断action是否为add，remove
    5、把comment_id转成整型
    6、根据comment_id查询数据库
    7、判断查询结果
    8、判断行为是点赞还是取消点赞
    9、如果为点赞，查询改评论，点赞次数加1，否则减1
    10、提交数据
    11、返回结果

    :return:
    """
    user = g.user
    comment_id = request.json.get('comment_id')
    action = request.json.get('action')
    if not all([comment_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不完整')
    if action not in ['add','remove']:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    try:
        comment_id = int(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='参数错误')
    try:
        comments = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    if not comments:
        return jsonify(errno=RET.NODATA,errmsg='评论不存在')
    # 如果选择的是点赞
    if action == 'add':
        comment_like_model = CommentLike.query.filter(CommentLike.user_id==user.id,CommentLike.comment_id==comment_id).first()
        # 判断查询结果，如果没有点赞过
        if not comment_like_model:
            comment_like_model = CommentLike()
            comment_like_model.user_id = user.id
            comment_like_model.comment_id = comment_id
            # 把数据提交给数据库会话对象，点赞次数加1
            db.session.add(comment_like_model)
            comments.like_count += 1
    # 如果取消点赞
    else:
        comment_like_model = CommentLike.query.filter(CommentLike.user_id==user.id,CommentLike.comment_id==comment_id).first()
        if comment_like_model:
            db.session.delete(comment_like_model)
            comments.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')

    return jsonify(errno=RET.OK,errmsg='OK')


@news_blue.route('/followed_user',methods=['POST'])
@login_required
def followed_user():
    """
    关注与取消关注
    1、获取用户信息,如果未登录直接返回
    2、获取参数，user_id和action
    3、检查参数的完整性
    4、校验参数，action是否为followed，unfollow
    5、根据用户id获取被关注的用户
    6、判断获取结果
    7、根据对应的action执行操作，关注或取消关注
    8、返回结果
    :return:
    """
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
    user_id = request.json.get('user_id')
    action = request.json.get('action')
    if not all([user_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不完整')
    if action not in ['follow','unfollow']:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据失败')
    if not other:
        return jsonify(errno=RET.NODATA,errmsg='无用户数据')
    # 如果选择关注
    if action == 'follow':
        if other not in user.followed:
            user.followed.append(other)
        else:
            return jsonify(errno=RET.DATAEXIST,errmsg='当前用户已被关注')
    # 取消关注
    else:
        if other in user.followed:
            user.followed.remove(other)

    return jsonify(errno=RET.OK,errmsg='OK')

        
        
        

















# 加载项目logo图标，favicon.ico,浏览器会默认请求项目根路径下的favicon文件
# http://127.0.0.1:5000/favicon.ico
@news_blue.route('/favicon.ico')
def favicon():
    # 发送文件给浏览器,
    # send_static_file是Flask框架自带的函数，Flask框架静态路由的实现就是通过这个函数
    return current_app.send_static_file('news/favicon.ico')


