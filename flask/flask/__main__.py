# -*- coding: utf-8 -*-
"""
    flask.__main__：flask.run的别名，用于命令行.
"""

if __name__ == '__main__':
    from .cli import main

    main(as_module=True)
