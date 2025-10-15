"""
数据模型定义
Data models for QoS policy management
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class PolicyStatus(Enum):
    """策略状态枚举"""
    UPLOADED = "uploaded"       # 已上传
    VALIDATED = "validated"     # 已验证
    APPLIED = "applied"         # 已应用
    FAILED = "failed"           # 失败
    PENDING = "pending"         # 待处理


class ACLType(Enum):
    """ACL 类型"""
    IPV4 = "ipv4"
    IPV6 = "ipv6"


@dataclass
class ACLRule:
    """ACL 规则"""
    sequence: int
    action: str  # permit/deny
    protocol: str  # tcp/udp/ip/icmp
    source: str
    destination: str
    source_port: Optional[List[int]] = None
    dest_port: Optional[List[int]] = None
    
    def __post_init__(self):
        """验证规则"""
        if self.action not in ['permit', 'deny']:
            raise ValueError(f"Invalid action: {self.action}")
        if self.protocol not in ['tcp', 'udp', 'ip', 'icmp', 'any']:
            raise ValueError(f"Invalid protocol: {self.protocol}")


@dataclass
class AccessList:
    """访问控制列表"""
    name: str
    type: ACLType
    rules: List[ACLRule] = field(default_factory=list)
    
    def add_rule(self, rule: ACLRule):
        """添加规则"""
        self.rules.append(rule)
        # 按 sequence 排序
        self.rules.sort(key=lambda r: r.sequence)


@dataclass
class ClassMap:
    """流分类映射"""
    name: str
    match_type: str  # match-any/match-all
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """验证匹配类型"""
        if self.match_type not in ['match-any', 'match-all']:
            raise ValueError(f"Invalid match_type: {self.match_type}")


@dataclass
class PolicyMapClass:
    """策略映射中的类配置"""
    class_name: str
    actions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PolicyMap:
    """策略映射"""
    name: str
    classes: List[PolicyMapClass] = field(default_factory=list)


@dataclass
class ServicePolicy:
    """服务策略（接口应用）"""
    interface: str
    direction: str  # input/output
    policy_map: str
    
    def __post_init__(self):
        """验证方向"""
        if self.direction not in ['input', 'output']:
            raise ValueError(f"Invalid direction: {self.direction}")


@dataclass
class PolicyModel:
    """完整的 QoS 策略模型"""
    id: str
    name: str
    description: str
    access_lists: List[AccessList] = field(default_factory=list)
    class_maps: List[ClassMap] = field(default_factory=list)
    policy_maps: List[PolicyMap] = field(default_factory=list)
    service_policies: List[ServicePolicy] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: PolicyStatus = PolicyStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'access_lists_count': len(self.access_lists),
            'class_maps_count': len(self.class_maps),
            'policy_maps_count': len(self.policy_maps),
            'service_policies_count': len(self.service_policies),
        }


@dataclass
class CommandResult:
    """单条命令执行结果"""
    command: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ExecutionResult:
    """策略执行结果"""
    policy_id: str
    success: bool
    message: str
    commands: List[str] = field(default_factory=list)
    command_results: List[CommandResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    dry_run: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'policy_id': self.policy_id,
            'success': self.success,
            'message': self.message,
            'commands_count': len(self.commands),
            'errors_count': len(self.errors),
            'executed_at': self.executed_at.isoformat(),
            'duration_ms': self.duration_ms,
            'dry_run': self.dry_run,
            'details': {
                'commands': self.commands,
                'errors': self.errors,
            }
        }
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.success = False


@dataclass
class ValidationError:
    """验证错误"""
    field: str
    message: str
    severity: str = "error"  # error/warning
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.field}: {self.message}"
