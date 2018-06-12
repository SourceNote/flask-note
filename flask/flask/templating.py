# -*- coding: utf-8 -*-
"""
    flask.templating:实现与Jinja2的桥接.
"""

from jinja2 import BaseLoader, Environment as BaseEnvironment, \
    TemplateNotFound

from .globals import _request_ctx_stack, _app_ctx_stack
from .signals import template_rendered, before_render_template


def _default_template_ctx_processor():
    """
    缺省模板上下文处理器
    注入到request、session、g
    :return:
    """
    reqctx = _request_ctx_stack.top  # 获取请求上下文
    appctx = _app_ctx_stack.top  # 获取应用上下文
    rv = {}
    if appctx is not None:
        rv['g'] = appctx.g
    if reqctx is not None:
        rv['request'] = reqctx.request
        rv['session'] = reqctx.session
    return rv


class Environment(BaseEnvironment):
    """主要是为了照顾Flask中的蓝图"""

    def __init__(self, app, **options):
        if 'loader' not in options:
            options['loader'] = app.create_global_jinja_loader()
        BaseEnvironment.__init__(self, **options)
        self.app = app


class DispatchingJinjaLoader(BaseLoader):
    """加载器：在应用和所有蓝图文件夹下寻找模板"""

    def __init__(self, app):
        self.app = app

    def get_source(self, environment, template):
        if self.app.config['EXPLAIN_TEMPLATE_LOADING']:
            return self._get_source_explained(environment, template)
        return self._get_source_fast(environment, template)

    def _get_source_explained(self, environment, template):
        attempts = []
        trv = None

        for srcobj, loader in self._iter_loaders(template):
            try:
                rv = loader.get_source(environment, template)
                if trv is None:
                    trv = rv
            except TemplateNotFound:
                rv = None
            attempts.append((loader, srcobj, rv))

        from .debughelpers import explain_template_loading_attempts
        explain_template_loading_attempts(self.app, template, attempts)

        if trv is not None:
            return trv
        raise TemplateNotFound(template)

    def _get_source_fast(self, environment, template):
        for srcobj, loader in self._iter_loaders(template):
            try:
                return loader.get_source(environment, template)
            except TemplateNotFound:
                continue
        raise TemplateNotFound(template)

    def _iter_loaders(self, template):
        loader = self.app.jinja_loader
        if loader is not None:
            yield self.app, loader

        for blueprint in self.app.iter_blueprints():
            loader = blueprint.jinja_loader
            if loader is not None:
                yield blueprint, loader

    def list_templates(self):
        result = set()
        loader = self.app.jinja_loader
        if loader is not None:
            result.update(loader.list_templates())

        for blueprint in self.app.iter_blueprints():
            loader = blueprint.jinja_loader
            if loader is not None:
                for template in loader.list_templates():
                    result.add(template)

        return list(result)


def _render(template, context, app):
    """渲染模板并发射信号"""

    # 发送模板渲染前信号
    before_render_template.send(app, template=template, context=context)
    rv = template.render(context)
    # 发送模板渲染完成信号
    template_rendered.send(app, template=template, context=context)
    return rv


def render_template(template_name_or_list, **context):
    """Renders a template from the template folder with the given
    context.

    :param template_name_or_list: the name of the template to be
                                  rendered, or an iterable with template names
                                  the first one existing will be rendered
    :param context: the variables that should be available in the
                    context of the template.
    """
    ctx = _app_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.get_or_select_template(template_name_or_list),
                   context, ctx.app)


def render_template_string(source, **context):
    """Renders a template from the given template source string
    with the given context. Template variables will be autoescaped.

    :param source: the source code of the template to be
                   rendered
    :param context: the variables that should be available in the
                    context of the template.
    """
    ctx = _app_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.from_string(source),
                   context, ctx.app)
