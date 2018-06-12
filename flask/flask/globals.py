# -*- coding: utf-8 -*-
"""
    flask.globals.py：定义所有的代理到当前激活的上下文的全局对象
"""

from functools import partial
from werkzeug.local import LocalStack, LocalProxy

# 请求上下文错误消息
_request_ctx_err_msg = '''\
不在请求上下文之中。
一般这种情况意味着你尝试使用一个需要激活HTTP请求的功能
'''

# 应用上下文消息
_app_ctx_err_msg = '''\
不再应用上下文中。
一般这种情况意味着你尝试使用一个需要同当前应用进行交互的功能。
请先通过app.app_context()构建应用上下文
'''


def _lookup_req_object(name):
    """根据名称查看请求对象"""
    top = _request_ctx_stack.top  # 从请求上下文栈顶弹出
    if top is None:
        # 如果为空，抛出运行时异常（请求上下文错误消息）
        raise RuntimeError(_request_ctx_err_msg)
    return getattr(top, name)


def _lookup_app_object(name):
    """根据名称查看应用对象"""
    top = _app_ctx_stack.top  # 从应用上下文堆栈弹出
    if top is None:
        # 如果为空，抛出运行时异常（应用上下文错误消息）
        raise RuntimeError(_app_ctx_err_msg)
    return getattr(top, name)


def _find_app():
    """寻找应用对象"""
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError(_app_ctx_err_msg)
    return top.app


# context locals
_request_ctx_stack = LocalStack()  # 请求上下文堆栈
_app_ctx_stack = LocalStack()  # 应用上下文堆栈
current_app = LocalProxy(_find_app)  # 当前应用应用对象
request = LocalProxy(partial(_lookup_req_object, 'request'))  # request请求对象
session = LocalProxy(partial(_lookup_req_object, 'session'))  # session请求对象
g = LocalProxy(partial(_lookup_app_object, 'g'))  # g应用对象
