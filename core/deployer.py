"""
配置下发器 - 通过 NX-API 与 Cisco Nexus 设备通信
Deployer - Communicate with Cisco Nexus devices via NX-API
"""

import requests
import json
from typing import List, Dict, Any, Optional
from urllib3.exceptions import InsecureRequestWarning
import time

from .models import ExecutionResult, CommandResult

# 禁用 SSL 警告（仅用于开发环境）
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class NXAPIClient:
    """NX-API 客户端"""
    
    def __init__(self, host: str, username: str, password: str, 
                 port: int = 443, verify_ssl: bool = False, timeout: int = 30):
        """
        初始化 NX-API 客户端
        
        Args:
            host: 设备 IP 或主机名
            username: 用户名
            password: 密码
            port: HTTPS 端口（默认 443）
            verify_ssl: 是否验证 SSL 证书
            timeout: 请求超时时间（秒）
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        
        # NX-API 端点
        self.url = f"https://{host}:{port}/ins"
        
        # 会话
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/json-rpc',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """
        测试连接
        
        Returns:
            连接是否成功
        """
        try:
            result = self.show_command("show version")
            return result.get('success', False)
        except Exception:
            return False
    
    def show_command(self, command: str) -> Dict[str, Any]:
        """
        执行 show 命令（只读）
        
        Args:
            command: show 命令
            
        Returns:
            执行结果字典
        """
        payload = self._build_payload([command], method="cli")
        
        try:
            response = self._send_request(payload)
            return self._parse_response(response, [command])
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_commands(self, commands: List[str], 
                        dry_run: bool = False) -> ExecutionResult:
        """
        执行配置命令（批量）
        
        Args:
            commands: 命令列表
            dry_run: 是否为预演模式（不实际执行）
            
        Returns:
            ExecutionResult 对象
        """
        start_time = time.time()
        
        result = ExecutionResult(
            policy_id="unknown",
            success=True,
            message="",
            commands=commands,
            dry_run=dry_run
        )
        
        if dry_run:
            result.message = "Dry-run mode: commands not executed"
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result
        
        # 过滤空命令和注释
        valid_commands = [cmd.strip() for cmd in commands if cmd.strip() and not cmd.strip().startswith('#')]
        
        if not valid_commands:
            result.message = "No valid commands to execute"
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result
        
        try:
            # 构建 JSON-RPC 请求
            payload = self._build_payload(valid_commands, method="cli_conf")
            
            # 发送请求
            response = self._send_request(payload)
            
            # 解析响应
            parsed = self._parse_response(response, valid_commands)
            
            if parsed['success']:
                result.message = f"Successfully executed {len(valid_commands)} commands"
                
                # 记录每条命令的结果
                for i, cmd in enumerate(valid_commands):
                    cmd_result = CommandResult(
                        command=cmd,
                        success=True,
                        output=parsed.get('results', [{}])[i].get('body', {}).get('TABLE_result', '')
                    )
                    result.command_results.append(cmd_result)
            else:
                result.success = False
                result.message = parsed.get('error', 'Unknown error')
                result.add_error(parsed.get('error', 'Unknown error'))
                
                # 记录失败的命令
                for cmd in valid_commands:
                    cmd_result = CommandResult(
                        command=cmd,
                        success=False,
                        error=parsed.get('error', 'Unknown error')
                    )
                    result.command_results.append(cmd_result)
        
        except requests.exceptions.Timeout:
            result.success = False
            result.message = f"Request timeout after {self.timeout} seconds"
            result.add_error(result.message)
        
        except requests.exceptions.ConnectionError as e:
            result.success = False
            result.message = f"Connection error: {str(e)}"
            result.add_error(result.message)
        
        except Exception as e:
            result.success = False
            result.message = f"Unexpected error: {str(e)}"
            result.add_error(result.message)
        
        finally:
            result.duration_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    def _build_payload(self, commands: List[str], method: str = "cli_conf") -> List[Dict]:
        """
        构建 JSON-RPC 请求体
        
        Args:
            commands: 命令列表
            method: 方法名（cli_show/cli_conf/cli_show_ascii）
            
        Returns:
            JSON-RPC 请求列表
        """
        payload = []
        
        for i, cmd in enumerate(commands, start=1):
            payload.append({
                "jsonrpc": "2.0",
                "method": method,
                "params": {
                    "cmd": cmd,
                    "version": 1
                },
                "id": i
            })
        
        return payload
    
    def _send_request(self, payload: List[Dict]) -> requests.Response:
        """
        发送 HTTP 请求
        
        Args:
            payload: JSON-RPC 请求体
            
        Returns:
            Response 对象
            
        Raises:
            requests.exceptions.RequestException: 请求失败
        """
        response = self.session.post(
            self.url,
            json=payload,
            verify=self.verify_ssl,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response
    
    def _parse_response(self, response: requests.Response, 
                       commands: List[str]) -> Dict[str, Any]:
        """
        解析 NX-API 响应
        
        Args:
            response: HTTP 响应对象
            commands: 原始命令列表
            
        Returns:
            解析后的结果字典
        """
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f"Failed to parse JSON response: {e}"
            }
        
        # data 是一个列表，每个元素对应一条命令的响应
        if not isinstance(data, list):
            data = [data]
        
        result = {
            'success': True,
            'results': []
        }
        
        for i, item in enumerate(data):
            # 检查错误
            if 'error' in item:
                error_info = item['error']
                error_msg = error_info.get('message', 'Unknown error')
                error_data = error_info.get('data', {})
                
                result['success'] = False
                result['error'] = f"Command #{i+1} failed: {error_msg}"
                
                if 'msg' in error_data:
                    result['error'] += f" - {error_data['msg']}"
                
                result['failed_command'] = commands[i] if i < len(commands) else 'unknown'
                break
            
            # 成功的响应
            if 'result' in item:
                result['results'].append(item['result'])
        
        return result
    
    def get_running_config(self, section: Optional[str] = None) -> str:
        """
        获取运行配置
        
        Args:
            section: 配置段（如 'interface'、'ip access-list'）
            
        Returns:
            配置文本
        """
        if section:
            cmd = f"show running-config {section}"
        else:
            cmd = "show running-config"
        
        result = self.show_command(cmd)
        
        if result.get('success'):
            # 从结果中提取配置文本
            results = result.get('results', [])
            if results and 'body' in results[0]:
                return results[0]['body']
        
        return ""
    
    def verify_configuration(self, expected_patterns: List[str]) -> Dict[str, bool]:
        """
        验证配置是否生效
        
        Args:
            expected_patterns: 期望出现的配置片段列表
            
        Returns:
            验证结果字典 {pattern: exists}
        """
        config = self.get_running_config()
        
        verification = {}
        for pattern in expected_patterns:
            verification[pattern] = pattern in config
        
        return verification
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
