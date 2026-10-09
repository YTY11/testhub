"""UI 自动化项目登录态文件存储与"登录用例"配置。

完全基于文件，不写数据库、不做迁移、不改动源数据。
- 登录态文件：<BASE_DIR>/ui_login_states/login_state_<project_id>.json
  内容：{"saved_at": "<iso>", "state": {Playwright storage_state}}
- 登录用例配置：<BASE_DIR>/ui_login_states/login_case_<project_id>.json
  内容：{"test_case_id": <id>}
"""
import json
import os
from datetime import datetime, timezone

from django.conf import settings

STATE_DIR_NAME = 'ui_login_states'

# 登录态默认有效期（秒）：超过则视为过期，需重新执行登录用例
DEFAULT_MAX_AGE_SECONDS = 6 * 3600  # 6 小时


def login_state_dir():
    return os.path.join(settings.BASE_DIR, STATE_DIR_NAME)


def login_state_path(project_id):
    return os.path.join(login_state_dir(), f'login_state_{project_id}.json')


def login_case_path(project_id):
    return os.path.join(login_state_dir(), f'login_case_{project_id}.json')


def _now():
    return datetime.now(timezone.utc)


def save_login_state(project_id, state, max_age_seconds=None):
    """把登录态（storage_state dict）写入项目对应文件，记录保存时间。"""
    if not project_id:
        return
    directory = login_state_dir()
    os.makedirs(directory, exist_ok=True)
    path = login_state_path(project_id)
    payload = {
        'saved_at': _now().isoformat(),
        'max_age_seconds': max_age_seconds or DEFAULT_MAX_AGE_SECONDS,
        'state': state,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)


def load_login_state(project_id, max_age_seconds=None):
    """读取项目登录态。

    返回 storage_state dict；文件不存在、损坏或超过有效期时返回 None。
    兼容旧格式（无 saved_at / 直接是裸 state dict 时视为未过期）。
    """
    if not project_id:
        return None
    path = login_state_path(project_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as f:
            payload = json.load(f)
    except Exception:
        return None
    # 旧格式：直接是裸 storage_state dict
    if isinstance(payload, dict) and 'state' not in payload and 'saved_at' not in payload:
        return payload
    state = payload.get('state')
    if not isinstance(state, dict):
        return None
    age = max_age_seconds if max_age_seconds is not None else payload.get('max_age_seconds',
                                                                          DEFAULT_MAX_AGE_SECONDS)
    try:
        saved_at = datetime.fromisoformat(payload['saved_at'])
    except (KeyError, ValueError):
        return state  # 无保存时间，视为有效
    if saved_at.tzinfo is None:
        saved_at = saved_at.replace(tzinfo=timezone.utc)
    if (_now() - saved_at).total_seconds() > age:
        return None
    return state


def clear_login_state(project_id):
    """删除项目的登录态文件。"""
    if not project_id:
        return
    path = login_state_path(project_id)
    if os.path.exists(path):
        os.remove(path)


def save_login_case(project_id, test_case_id):
    """保存项目指定的"登录用例" id。"""
    if not project_id or not test_case_id:
        return
    directory = login_state_dir()
    os.makedirs(directory, exist_ok=True)
    path = login_case_path(project_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'test_case_id': int(test_case_id)}, f, ensure_ascii=False)


def load_login_case(project_id):
    """读取项目指定的"登录用例" id；未配置时返回 None。"""
    if not project_id:
        return None
    path = login_case_path(project_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as f:
            payload = json.load(f)
        return int(payload.get('test_case_id'))
    except Exception:
        return None


def clear_login_case(project_id):
    """清除项目指定的"登录用例" id。"""
    if not project_id:
        return
    path = login_case_path(project_id)
    if os.path.exists(path):
        os.remove(path)
