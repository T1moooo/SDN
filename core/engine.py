"""
策略引擎 - 负责解析 YAML 策略并生成 NX-CLI 命令
Policy Engine - Parse YAML policies and generate NX-CLI commands
"""

import yaml
from typing import List, Dict, Any, Tuple
from pathlib import Path
import re

from .models import (
    PolicyModel, AccessList, ACLRule, ACLType, ClassMap, 
    PolicyMap, PolicyMapClass, ServicePolicy, PolicyStatus, ValidationError
)


class PolicyEngine:
    """策略引擎核心类"""
    
    def __init__(self):
        """初始化策略引擎"""
        self.validation_errors: List[ValidationError] = []
    
    def parse_yaml(self, filepath: str) -> PolicyModel:
        """
        解析 YAML 策略文件
        
        Args:
            filepath: YAML 文件路径
            
        Returns:
            PolicyModel 对象
            
        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML 格式错误
            ValueError: 策略内容不合法
        """
        # 读取文件
        file_path = Path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"Policy file not found: {filepath}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {e}")
        
        if not data:
            raise ValueError("Empty policy file")
        
        # 验证必需字段
        required_fields = ['id', 'name', 'description']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # 构建 PolicyModel
        policy = PolicyModel(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            status=PolicyStatus.UPLOADED
        )
        
        # 解析 ACLs
        if 'access_lists' in data:
            policy.access_lists = self._parse_access_lists(data['access_lists'])
        
        # 解析 class-maps
        if 'class_maps' in data:
            policy.class_maps = self._parse_class_maps(data['class_maps'])
        
        # 解析 policy-maps
        if 'policy_maps' in data:
            policy.policy_maps = self._parse_policy_maps(data['policy_maps'])
        
        # 解析 service-policies
        if 'service_policies' in data:
            policy.service_policies = self._parse_service_policies(data['service_policies'])
        
        return policy
    
    def _parse_access_lists(self, acl_data: List[Dict]) -> List[AccessList]:
        """解析 ACL 列表"""
        access_lists = []
        
        for acl in acl_data:
            acl_type = ACLType.IPV4 if acl.get('type', 'ipv4') == 'ipv4' else ACLType.IPV6
            access_list = AccessList(
                name=acl['name'],
                type=acl_type
            )
            
            # 解析规则
            for rule_data in acl.get('rules', []):
                rule = ACLRule(
                    sequence=rule_data['sequence'],
                    action=rule_data['action'],
                    protocol=rule_data['protocol'],
                    source=rule_data['source'],
                    destination=rule_data['destination'],
                    source_port=rule_data.get('source_port'),
                    dest_port=rule_data.get('dest_port')
                )
                access_list.add_rule(rule)
            
            access_lists.append(access_list)
        
        return access_lists
    
    def _parse_class_maps(self, cm_data: List[Dict]) -> List[ClassMap]:
        """解析 class-map 列表"""
        class_maps = []
        
        for cm in cm_data:
            class_map = ClassMap(
                name=cm['name'],
                match_type=cm.get('match_type', 'match-any'),
                conditions=cm.get('conditions', [])
            )
            class_maps.append(class_map)
        
        return class_maps
    
    def _parse_policy_maps(self, pm_data: List[Dict]) -> List[PolicyMap]:
        """解析 policy-map 列表"""
        policy_maps = []
        
        for pm in pm_data:
            policy_map = PolicyMap(name=pm['name'])
            
            # 解析 class 配置
            for cls in pm.get('classes', []):
                pm_class = PolicyMapClass(
                    class_name=cls['class_name'],
                    actions=cls.get('actions', [])
                )
                policy_map.classes.append(pm_class)
            
            policy_maps.append(policy_map)
        
        return policy_maps
    
    def _parse_service_policies(self, sp_data: List[Dict]) -> List[ServicePolicy]:
        """解析 service-policy 列表"""
        service_policies = []
        
        for sp in sp_data:
            service_policy = ServicePolicy(
                interface=sp['interface'],
                direction=sp['direction'],
                policy_map=sp['policy_map']
            )
            service_policies.append(service_policy)
        
        return service_policies
    
    def validate(self, policy: PolicyModel) -> Tuple[bool, List[ValidationError]]:
        """
        验证策略的完整性和合法性
        
        Args:
            policy: 策略模型
            
        Returns:
            (是否通过, 错误列表)
        """
        self.validation_errors = []
        
        # 验证 ACL 规则
        self._validate_access_lists(policy)
        
        # 验证 class-map 引用
        self._validate_class_maps(policy)
        
        # 验证 policy-map 引用
        self._validate_policy_maps(policy)
        
        # 验证 service-policy 引用
        self._validate_service_policies(policy)
        
        # 验证接口名称
        self._validate_interfaces(policy)
        
        is_valid = len([e for e in self.validation_errors if e.severity == "error"]) == 0
        
        return is_valid, self.validation_errors
    
    def _validate_access_lists(self, policy: PolicyModel):
        """验证 ACL"""
        for acl in policy.access_lists:
            if not acl.rules:
                self.validation_errors.append(
                    ValidationError('access_lists', f"ACL '{acl.name}' has no rules")
                )
            
            # 检查序号重复
            sequences = [r.sequence for r in acl.rules]
            if len(sequences) != len(set(sequences)):
                self.validation_errors.append(
                    ValidationError('access_lists', f"ACL '{acl.name}' has duplicate sequence numbers")
                )
    
    def _validate_class_maps(self, policy: PolicyModel):
        """验证 class-map"""
        acl_names = {acl.name for acl in policy.access_lists}
        
        for cm in policy.class_maps:
            for condition in cm.conditions:
                if condition.get('type') == 'access-group':
                    acl_name = condition.get('name')
                    if acl_name not in acl_names:
                        self.validation_errors.append(
                            ValidationError('class_maps', 
                                f"Class-map '{cm.name}' references non-existent ACL '{acl_name}'")
                        )
    
    def _validate_policy_maps(self, policy: PolicyModel):
        """验证 policy-map"""
        class_names = {cm.name for cm in policy.class_maps}
        
        for pm in policy.policy_maps:
            if not pm.classes:
                self.validation_errors.append(
                    ValidationError('policy_maps', f"Policy-map '{pm.name}' has no classes", "warning")
                )
            
            for cls in pm.classes:
                if cls.class_name not in class_names and cls.class_name != 'class-default':
                    self.validation_errors.append(
                        ValidationError('policy_maps',
                            f"Policy-map '{pm.name}' references non-existent class '{cls.class_name}'")
                    )
    
    def _validate_service_policies(self, policy: PolicyModel):
        """验证 service-policy"""
        policy_names = {pm.name for pm in policy.policy_maps}
        
        for sp in policy.service_policies:
            if sp.policy_map not in policy_names:
                self.validation_errors.append(
                    ValidationError('service_policies',
                        f"Service-policy references non-existent policy-map '{sp.policy_map}'")
                )
    
    def _validate_interfaces(self, policy: PolicyModel):
        """验证接口名称格式"""
        interface_pattern = re.compile(r'^(Ethernet|Vlan|port-channel)\d+(/\d+)?$', re.IGNORECASE)
        
        for sp in policy.service_policies:
            if not interface_pattern.match(sp.interface):
                self.validation_errors.append(
                    ValidationError('service_policies',
                        f"Invalid interface name format: '{sp.interface}'", "warning")
                )
    
    def generate_commands(self, policy: PolicyModel) -> List[str]:
        """
        生成 NX-CLI 配置命令
        
        Args:
            policy: 策略模型
            
        Returns:
            命令列表（按执行顺序排列）
        """
        commands = []
        
        # 1. 生成 ACL 命令
        commands.extend(self._generate_acl_commands(policy.access_lists))
        
        # 2. 生成 class-map 命令
        commands.extend(self._generate_class_map_commands(policy.class_maps))
        
        # 3. 生成 policy-map 命令
        commands.extend(self._generate_policy_map_commands(policy.policy_maps))
        
        # 4. 生成 service-policy 命令
        commands.extend(self._generate_service_policy_commands(policy.service_policies))
        
        return commands
    
    def _generate_acl_commands(self, access_lists: List[AccessList]) -> List[str]:
        """生成 ACL 配置命令"""
        commands = []
        
        for acl in access_lists:
            # ACL 头部
            commands.append(f"ip access-list {acl.name}")
            
            # 规则
            for rule in acl.rules:
                cmd = f"  {rule.sequence} {rule.action} {rule.protocol}"
                cmd += f" {rule.source}"
                
                # 源端口
                if rule.source_port:
                    if len(rule.source_port) == 1:
                        cmd += f" eq {rule.source_port[0]}"
                    else:
                        cmd += f" range {rule.source_port[0]} {rule.source_port[1]}"
                
                cmd += f" {rule.destination}"
                
                # 目的端口
                if rule.dest_port:
                    if len(rule.dest_port) == 1:
                        cmd += f" eq {rule.dest_port[0]}"
                    elif len(rule.dest_port) == 2:
                        cmd += f" range {rule.dest_port[0]} {rule.dest_port[1]}"
                    else:
                        # 多个独立端口
                        for port in rule.dest_port:
                            commands.append(cmd + f" eq {port}")
                        continue
                
                commands.append(cmd)
            
            commands.append("")  # 空行分隔
        
        return commands
    
    def _generate_class_map_commands(self, class_maps: List[ClassMap]) -> List[str]:
        """生成 class-map 配置命令"""
        commands = []
        
        for cm in class_maps:
            commands.append(f"class-map {cm.match_type} {cm.name}")
            
            for condition in cm.conditions:
                if condition['type'] == 'access-group':
                    commands.append(f"  match access-group name {condition['name']}")
                elif condition['type'] == 'dscp':
                    commands.append(f"  match dscp {condition['value']}")
                elif condition['type'] == 'precedence':
                    commands.append(f"  match precedence {condition['value']}")
            
            commands.append("")
        
        return commands
    
    def _generate_policy_map_commands(self, policy_maps: List[PolicyMap]) -> List[str]:
        """生成 policy-map 配置命令"""
        commands = []
        
        for pm in policy_maps:
            commands.append(f"policy-map {pm.name}")
            
            for cls in pm.classes:
                commands.append(f"  class {cls.class_name}")
                
                for action in cls.actions:
                    if action['type'] == 'set':
                        param = action['parameter']
                        value = action['value']
                        commands.append(f"    set {param} {value}")
                    elif action['type'] == 'police':
                        rate = action.get('rate', '10m')
                        commands.append(f"    police cir {rate}")
                    elif action['type'] == 'bandwidth':
                        bw = action.get('value', '10')
                        commands.append(f"    bandwidth {bw}")
            
            commands.append("")
        
        return commands
    
    def _generate_service_policy_commands(self, service_policies: List[ServicePolicy]) -> List[str]:
        """生成 service-policy 配置命令"""
        commands = []
        
        for sp in service_policies:
            commands.append(f"interface {sp.interface}")
            commands.append(f"  service-policy {sp.direction} {sp.policy_map}")
            commands.append("")
        
        return commands
    
    def preview_commands(self, policy: PolicyModel) -> str:
        """
        预览生成的命令（格式化输出）
        
        Args:
            policy: 策略模型
            
        Returns:
            格式化的命令字符串
        """
        commands = self.generate_commands(policy)
        
        output = f"# Policy: {policy.name}\n"
        output += f"# Description: {policy.description}\n"
        output += f"# Total Commands: {len([c for c in commands if c.strip()])}\n"
        output += "# " + "=" * 70 + "\n\n"
        output += "\n".join(commands)
        
        return output
