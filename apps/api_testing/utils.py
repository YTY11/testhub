import json
import time
import logging
from django.utils import timezone
from .models import RequestHistory
from .variable_resolver import VariableResolver

logger = logging.getLogger(__name__)


def _build_script_helpers():
    """为请求前/请求后脚本提供工具函数（兼容业务 SDK 的 AES-256-CBC-PKCS7，key=UTF-8，IV=0）。"""
    from apps.data_factory.tools.encryption_tools import EncryptionTools

    def aes_encrypt(text, key):
        r = EncryptionTools.aes_pkcs7_encrypt(text, key)
        return r.get('result', r.get('error', ''))

    def aes_decrypt(text, key):
        r = EncryptionTools.aes_pkcs7_decrypt(text, key)
        return r.get('result', r.get('error', ''))

    return {'aes_encrypt': aes_encrypt, 'aes_decrypt': aes_decrypt}


def run_pre_request_script(script, context):
    """执行请求前脚本（Python）。

    上下文可读写：params(dict)、headers(dict)、body(dict|str)、url(str)、variables(dict)，
    并内置 json、urllib.parse、aes_encrypt、aes_decrypt。脚本可直接修改这些变量实现参数加密。
    脚本内的变量表达式（${...}，如 ${date_offset(-7)}、${datetime()}）在执行前会被解析为字面值。
    """
    if not script or not script.strip():
        return context
    ctx = dict(context)
    ctx['json'] = json
    from urllib import parse as _urlparse
    ctx['urllib'] = _urlparse
    ctx.update(_build_script_helpers())
    # 先解析脚本中的变量表达式 ${...}，使脚本可直接使用变量助手插入的占位符
    try:
        script = VariableResolver().resolve(script)
    except Exception as e:
        logger.error(f"[请求前脚本] 变量解析失败: {e}")
    try:
        exec(compile(script, '<pre_request_script>', 'exec'), {'__builtins__': __builtins__}, ctx)
    except Exception as e:
        logger.error(f"[请求前脚本] 执行失败: {e}")
        ctx['script_error'] = str(e)
    return ctx


def run_post_request_script(script, context):
    """执行请求后脚本（Python）。

    上下文可读：response_text(str)、response_json(dict|None)、status_code(int)、variables(dict)；
    内置 json、aes_encrypt、aes_decrypt。脚本可把解密结果赋给 decrypted_body，前端将优先展示它。
    脚本内的变量表达式（${...}）在执行前会被解析为字面值。
    """
    if not script or not script.strip():
        return context
    ctx = dict(context)
    ctx['json'] = json
    ctx.update(_build_script_helpers())
    try:
        script = VariableResolver().resolve(script)
    except Exception as e:
        logger.error(f"[请求后脚本] 变量解析失败: {e}")
    try:
        exec(compile(script, '<post_request_script>', 'exec'), {'__builtins__': __builtins__}, ctx)
    except Exception as e:
        logger.error(f"[请求后脚本] 执行失败: {e}")
        ctx['script_error'] = str(e)
    return ctx


def execute_assertions(response, assertions, text_override=None, json_override=None):
    """执行断言验证

    text_override / json_override：当响应被请求后脚本解密为明文时传入，
    使断言基于解密后的明文进行（如 contains / json_path / equals）。
    """
    results = []
    
    for assertion in assertions:
        result = {
            'name': assertion.get('name', '未命名断言'),
            'type': assertion.get('type'),
            'passed': False,
            'expected': assertion.get('expected'),
            'actual': None,
            'error': None
        }
        
        try:
            assertion_type = assertion.get('type')
            expected = assertion.get('expected')
            actual = None
            passed = False
            
            if assertion_type == 'status_code':
                actual = response.status_code
                passed = actual == expected
                
            elif assertion_type == 'response_time':
                # 响应时间断言在调用方处理
                actual = assertion.get('actual_time')
                passed = actual <= expected if actual else False
                
            elif assertion_type == 'contains':
                text = text_override if text_override is not None else (response.text or '')
                pattern = str(expected)
                actual = text[:200] + '...' if len(text) > 200 else text
                passed = pattern in str(text)
                
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                expected_value = assertion.get('expected')
                actual = None
                passed = False
                
                try:
                    # 优先使用解密后的 JSON；否则解析原始响应
                    if json_override is not None:
                        response_json = json_override
                    else:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'application/json' not in content_type:
                            raise ValueError(f"响应不是JSON格式，Content-Type: {content_type}")
                        response_json = json.loads(response.text)
                    
                    # 检查JSONPath表达式是否为空
                    if not json_path:
                        raise ValueError("JSON路径表达式不能为空")
                    
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = str(actual) == str(expected_value)
                    
                    # 确保actual值被正确设置到result中
                    result['actual'] = actual
                except json.JSONDecodeError as e:
                    actual = None
                    passed = False
                    result['error'] = f"JSON解析失败: {str(e)}"
                    result['actual'] = actual
                except ImportError as e:
                    actual = None
                    passed = False
                    result['error'] = f"缺少依赖库: {str(e)}，请安装jsonpath-ng"
                    result['actual'] = actual
                except Exception as e:
                    actual = None
                    passed = False
                    result['error'] = f"执行错误: {str(e)}"
                    result['actual'] = actual
                    
            elif assertion_type == 'header':
                header_name = assertion.get('header_name', '')
                expected_value = assertion.get('expected_value')
                actual = response.headers.get(header_name)
                passed = actual == expected_value
                
            elif assertion_type == 'equals':
                actual = (text_override if text_override is not None else response.text).strip()
                passed = actual == str(expected).strip()
            
            # 确保在所有情况下都设置actual值
            if 'actual' not in result or result['actual'] is None:
                result['actual'] = actual
            result['passed'] = passed
            
        except Exception as e:
            result['error'] = str(e)
            result['passed'] = False
        
        results.append(result)
    
    return results


def execute_test_suite(test_suite, environment, executed_by):
    """执行测试套件并返回结果"""
    from .models import TestExecution, RequestHistory
    import requests
    import time
    
    try:
        # 创建变量解析器
        resolver = VariableResolver()
        
        # 创建执行记录
        execution = TestExecution.objects.create(
            test_suite=test_suite,
            status='RUNNING',
            start_time=timezone.now(),
            executed_by=executed_by
        )
        
        # 获取套件中的请求
        suite_requests = test_suite.testsuiterequest_set.filter(enabled=True).order_by('order')
        
        execution.total_requests = suite_requests.count()
        execution.save()
        
        results = []
        passed_count = 0
        failed_count = 0
        
        # 执行每个请求
        for suite_request in suite_requests:
            api_request = suite_request.request
            
            try:
                # 解析环境变量
                variables = {}
                if environment:
                    variables.update(environment.variables)
                
                # 替换URL中的变量（先解析动态函数，再替换环境变量）
                url = _replace_variables(api_request.url, variables)
                url = resolver.resolve(url)
                
                # 准备请求头
                headers = {}
                if isinstance(api_request.headers, list):
                    for header_item in api_request.headers:
                        if header_item.get('enabled', True) and header_item.get('key'):
                            key = header_item['key']
                            value = _replace_variables(str(header_item.get('value', '')), variables)
                            value = resolver.resolve(value)
                            headers[key] = value
                else:
                    headers = api_request.headers.copy()
                    for key, value in headers.items():
                        headers[key] = _replace_variables(str(value), variables)
                        headers[key] = resolver.resolve(headers[key])
                
                # 准备请求参数
                params = api_request.params.copy() if api_request.params else {}
                for key, value in params.items():
                    params[key] = _replace_variables(str(value), variables)
                    params[key] = resolver.resolve(params[key])
                
                # 准备请求体
                body_data = None
                if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
                    if api_request.body.get('type') == 'json':
                        body_data = api_request.body.get('data', {})
                        body_data = _replace_variables_in_dict(body_data, variables)
                        body_data = _resolve_variables_in_dict(body_data, resolver)
                
                # 执行请求
                start_time = time.time()
                response = requests.request(
                    method=api_request.method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=body_data,
                    timeout=30
                )
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # 执行断言验证
                assertions = api_request.assertions or []
                for assertion in assertions:
                    if assertion.get('type') == 'response_time':
                        assertion['actual_time'] = response_time
                
                assertions_results = execute_assertions(response, assertions)
                
                # 检查所有断言是否通过
                passed = True
                error_message = ''
                
                # 检查套件请求的断言
                for assertion in suite_request.assertions:
                    if assertion.get('type') == 'status_code':
                        expected = assertion.get('value')
                        if response.status_code != expected:
                            passed = False
                            error_message = f'状态码断言失败: 期望 {expected}, 实际 {response.status_code}'
                            break
                
                # 检查接口自身的断言
                if passed and assertions_results:
                    for assertion_result in assertions_results:
                        if not assertion_result.get('passed', True):
                            passed = False
                            error_message = f"断言失败: {assertion_result.get('name', '未命名断言')} - {assertion_result.get('error', '断言不通过')}"
                            break
                
                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'passed': passed,
                    'error': error_message,
                    'assertions_results': assertions_results,
                    # 真实执行数据，供 Allure 报告展示完整请求/响应
                    'start_time': int(start_time * 1000),
                    'stop_time': int(end_time * 1000),
                    'request_data': {
                        'url': url,
                        'method': api_request.method,
                        'headers': headers,
                        'params': params,
                        'body': body_data,
                    },
                    'response_data': {
                        'headers': dict(response.headers),
                        'body': response.text,
                        'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                    },
                })
                
                # 保存请求历史
                RequestHistory.objects.create(
                    request=api_request,
                    environment=environment,
                    request_data={
                        'url': url,
                        'method': api_request.method,
                        'headers': headers,
                        '极速版params': params,
                        'body': body_data
                    },
                    response_data={
                        'headers': dict(response.headers),
                        'body': response.text,
                        'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
                    },
                    status_code=response.status_code,
                    response_time=response_time,
                    assertions_results=assertions_results,
                    executed_by=executed_by
                )
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': api_request.url,
                    'passed': False,
                    'error': str(e)
                })
        
        # 更新执行结果
        execution.end_time = timezone.now()
        execution.passed_requests = passed_count
        execution.failed_requests = failed_count
        execution.status = 'COMPLETED' if failed_count == 0 else 'FAILED'
        execution.results = results
        execution.save()
        
        return {
            'success': True,
            'execution_id': execution.id,
            'passed_count': passed_count,
            'failed_count': failed_count,
            'total_count': execution.total_requests,
            'results': results
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def execute_api_request(api_request, environment, executed_by):
    """执行单个API请求并返回结果"""
    import requests
    import time
    
    try:
        # 创建变量解析器
        resolver = VariableResolver()
        
        # 解析环境变量
        variables = {}
        if environment:
            variables.update(environment.variables)
        
        # 替换URL中的变量（先解析动态函数，再替换环境变量）
        url = _replace_variables(api_request.url, variables)
        url = resolver.resolve(url)
        
        # 准备请求头
        headers = {}
        if isinstance(api_request.headers, list):
            for header_item in api_request.headers:
                if header_item.get('enabled', True) and header_item.get('key'):
                    key = header_item['key']
                    value = _replace_variables(str(header_item.get('value', '')), variables)
                    value = resolver.resolve(value)
                    headers[key] = value
        else:
            headers = api_request.headers.copy()
            for key, value in headers.items():
                headers[key] = _replace_variables(str(value), variables)
                headers[key] = resolver.resolve(headers[key])
        
        # 准备请求参数
        params = api_request.params.copy() if api_request.params else {}
        for key, value in params.items():
            params[key] = _replace_variables(str(value), variables)
            params[key] = resolver.resolve(params[key])
        
        # 准备请求体
        body_data = None
        if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
            if api_request.body.get('type') == 'json':
                body_data = api_request.body.get('data', {})
                body_data = _replace_variables_in_dict(body_data, variables)
                body_data = _resolve_variables_in_dict(body_data, resolver)

        # 执行请求前脚本（可修改 params/headers/body_data 实现参数加密）
        if api_request.pre_request_script and api_request.pre_request_script.strip():
            _pre_ctx = run_pre_request_script(api_request.pre_request_script, {
                'params': params,
                'headers': headers,
                'body': body_data,
                'url': url,
                'variables': variables,
            })
            params = _pre_ctx.get('params', params)
            headers = _pre_ctx.get('headers', headers)
            body_data = _pre_ctx.get('body', body_data)
            url = _pre_ctx.get('url', url)

        # 执行请求
        start_time = time.time()
        response = requests.request(
            method=api_request.method,
            url=url,
            headers=headers,
            params=params,
            json=body_data,
            timeout=30
        )
        end_time = time.time()
        response_time = (end_time - start_time) * 1000

        # 执行请求后脚本（可解密响应，把解密结果赋给 decrypted_body 供前端展示）
        decrypted_body = None
        if api_request.post_request_script and api_request.post_request_script.strip():
            try:
                _resp_json = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            except Exception:
                _resp_json = None
            _post_ctx = run_post_request_script(api_request.post_request_script, {
                'response_text': response.text,
                'response_json': _resp_json,
                'status_code': response.status_code,
                'variables': variables,
            })
            decrypted_body = _post_ctx.get('decrypted_body')

        # 执行断言验证
        assertions = api_request.assertions or []
        for assertion in assertions:
            if assertion.get('type') == 'response_time':
                assertion['actual_time'] = response_time
        
        _decrypted_json = None
        if decrypted_body:
            try:
                _decrypted_json = json.loads(decrypted_body)
            except Exception:
                _decrypted_json = None
        assertions_results = execute_assertions(response, assertions, text_override=decrypted_body, json_override=_decrypted_json)
        
        # 保存请求历史
        history = RequestHistory.objects.create(
            request=api_request,
            environment=environment,
            request_data={
                'url': url,
                'method': api_request.method,
                'headers': headers,
                'params': params,
                'body': body_data
            },
            response_data={
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                'decrypted': decrypted_body
            },
            status_code=response.status_code,
            response_time=response_time,
            assertions_results=assertions_results,
            executed_by=executed_by
        )
        
        return {
            'success': True,
            'history_id': history.id,
            'status_code': response.status_code,
            'response_time': response_time,
            'assertions_results': assertions_results,
            'response_data': {
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                'decrypted': decrypted_body
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _replace_variables(text, variables):
    """替换文本中的变量"""
    if not isinstance(text, str):
        return text
    
    result = text
    for key, value in (variables or {}).items():
        if isinstance(value, dict):
            replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
        else:
            replacement = str(value) if value is not None else ''
        result = result.replace(f'{{{{{key}}}}}', replacement)
    return result

def _replace_variables_in_dict(data, variables):
    """递归替换字典中的变量"""
    if isinstance(data, dict):
        return {k: _replace_variables_in_dict(v, variables) for k, v in data.items()}
    elif isinstance(data, list):
        return [_replace_variables_in_dict(item, variables) for item in data]
    elif isinstance(data, str):
        return _replace_variables(data, variables)
    else:
        return data

def _resolve_variables_in_dict(data, resolver):
    """递归解析字典中的动态函数占位符"""
    if isinstance(data, dict):
        return {k: _resolve_variables_in_dict(v, resolver) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_variables_in_dict(item, resolver) for item in data]
    elif isinstance(data, str):
        return resolver.resolve(data)
    else:
        return data
