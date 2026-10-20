"""
UI 测试浏览器全局并发控制。

多个 UI 测试执行（手动单用例 / 套件 / 定时任务）会在各自线程里创建真实浏览器，
无限制并发时会把服务器 CPU 打满导致项目崩溃、需重启。此模块提供一个进程级信号量，
Playwright 引擎与 Selenium 引擎共享同一个信号量，保证“同时运行的 UI 测试浏览器总数”
不超过限制（默认 1，可在 settings 里通过 MAX_UI_TEST_CONCURRENCY 调整）。
"""
import threading
from django.conf import settings

_ui_engine_semaphore = None
_semaphore_lock = threading.Lock()


def _get_ui_engine_semaphore():
    global _ui_engine_semaphore
    if _ui_engine_semaphore is None:
        with _semaphore_lock:
            if _ui_engine_semaphore is None:
                limit = int(getattr(settings, 'MAX_UI_TEST_CONCURRENCY', 1) or 1)
                _ui_engine_semaphore = threading.Semaphore(max(1, limit))
    return _ui_engine_semaphore


def acquire_ui_engine():
    """占用一个 UI 测试浏览器并发名额；成功返回 True，失败说明已有测试在运行。"""
    return _get_ui_engine_semaphore().acquire(blocking=False)


def release_ui_engine():
    """释放一个 UI 测试浏览器并发名额。"""
    try:
        _get_ui_engine_semaphore().release()
    except ValueError:
        pass
