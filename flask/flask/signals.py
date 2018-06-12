# -*- coding: utf-8 -*-
"""
    flask.signals：实现基于blinker的信号
"""

signals_available = False
try:
    from blinker import Namespace

    signals_available = True
except ImportError:
    class Namespace(object):
        def signal(self, name, doc=None):
            return _FakeSignal(name, doc)


    class _FakeSignal(object):

        """
        如果blinker不可用，创建一个具有相同接口的虚假类，忽略参数，
        在发送信号的时候什么都不做，或者抛出一个异常
        """

        def __init__(self, name, doc=None):
            self.name = name
            self.__doc__ = doc

        def _fail(self, *args, **kwargs):
            raise RuntimeError('信号不可用'
                               'blinker库没有安装 ')

        send = lambda *a, **kw: None
        # 所有的接受操作都设置为抛出异常
        connect = disconnect = has_receivers_for = receivers_for = \
            temporarily_connected_to = connected_to = _fail
        del _fail

# 代码信号的命名空间。如果不是Flask代码，不应该将信号放在这里，
# 需要创建自己的命名空间
_signals = Namespace()

# 核心信号
template_rendered = _signals.signal('template-rendered')  # 模板渲染信号
before_render_template = _signals.signal('before-render-template')  # 模板渲染前信号
request_started = _signals.signal('request-started')  # 请求已经开始信号
request_finished = _signals.signal('request-finished')  # 请求完成信号
request_tearing_down = _signals.signal('request-tearing-down')  # 请求结束信号
got_request_exception = _signals.signal('got-request-exception')  # 获得请求异常信号
appcontext_tearing_down = _signals.signal('appcontext-tearing-down')  # 应用上下文结束信号
appcontext_pushed = _signals.signal('appcontext-pushed')  # 应用上下文创建进栈信号
appcontext_popped = _signals.signal('appcontext-popped')  # 应用上下文弹出栈信号
message_flashed = _signals.signal('message-flashed')  # 消息已经闪现信号
