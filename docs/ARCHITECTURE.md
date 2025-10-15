# 系统架构设计文档

**项目**: SDN QoS 策略自动化管理系统  
**版本**: v1.0  
**日期**: 2025-10-15

---

## 1. 架构概览

本系统采用**分层架构**设计，从上到下分为：
1. **用户交互层** - CLI/REST 客户端/Web UI
2. **应用服务层** - Flask REST API 网关
3. **核心业务层** - 策略引擎、配置下发、校验
4. **设备接口层** - NX-API 通信
5. **持久化层** - 文件存储与日志

### 架构图（简化版）

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│         CLI Tool  │  REST Client  │  Web UI (Future)        │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    应用服务层 (Flask)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  API Gateway (app.py)                               │    │
│  │  • Authentication Middleware                        │    │
│  │  • Request Validation                               │    │
│  │  • Response Formatting                              │    │
│  │  • Error Handling                                   │    │
│  └───────────────────┬─────────────────────────────────┘    │
└────────────────────────┼──────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
┌─────────────┐  ┌────────────┐  ┌────────────┐
│ PolicyAPI   │  │ HealthAPI  │  │ LogsAPI    │
│ (policies.py│  │(health.py) │  │ (logs.py)  │
└──────┬──────┘  └────────────┘  └────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      核心业务层                              │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ PolicyEngine   │  │  NXAPIClient   │  │  Validator   │  │
│  │ (engine.py)    │  │ (deployer.py)  │  │(validator.py)│  │
│  │                │  │                │  │              │  │
│  │ • Parser       │  │ • HTTP Client  │  │ • Show Cmds  │  │
│  │ • Generator    │  │ • Retry Logic  │  │ • Diff Check │  │
│  │ • Validator    │  │ • Error Parse  │  │ • Report Gen │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐                    │
│  │ AuditLogger    │  │  DataModels    │                    │
│  │ (audit.py)     │  │ (models.py)    │                    │
│  └────────────────┘  └────────────────┘                    │
└──────────────────────────┬───────────────────────────────────┘
                           │ NX-API (JSON-RPC/HTTPS)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      设备接口层                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Cisco Nexus 9000v - NX-API Endpoint                 │   │
│  │  • /ins (JSON-RPC)                                   │   │
│  │  • cli / cli_conf / cli_show                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

持久化层:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ policies/    │  │ logs/        │  │ backups/     │
│ YAML files   │  │ audit/app    │  │ config snaps │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 2. 核心组件详解

### 2.1 PolicyEngine（策略引擎）

**职责**: 解析 YAML 策略并生成 NX-CLI 命令

**类图**:
```
┌──────────────────────────────────────┐
│         PolicyEngine                 │
├──────────────────────────────────────┤
│ + parse_yaml(file: str)              │
│ + generate_commands(policy)          │
│ + validate_syntax(policy)            │
├──────────────────────────────────────┤
│ - _parse_acls()                      │
│ - _parse_class_maps()                │
│ - _parse_policy_maps()               │
│ - _parse_service_policies()          │
└──────────────────────────────────────┘
           │
           │ uses
           ▼
┌──────────────────────────────────────┐
│      CommandGenerator                │
├──────────────────────────────────────┤
│ + generate(policy: PolicyModel)      │
├──────────────────────────────────────┤
│ - _gen_acl_commands()                │
│ - _gen_classmap_commands()           │
│ - _gen_policymap_commands()          │
│ - _order_commands(cmds)              │
└──────────────────────────────────────┘
```

**处理流程**:
```
YAML File → PolicyParser → PolicyModel → CommandGenerator → List[CLICommand]
                ↓                                  ↓
         Schema Validation               Dependency Resolution
                ↓                                  ↓
         Semantic Check                    Order by Topology
```

---

### 2.2 NXAPIClient（设备通信客户端）

**职责**: 封装 NX-API 调用，处理通信细节

**接口设计**:
```python
class NXAPIClient:
    def execute_commands(
        self,
        commands: List[str],
        dry_run: bool = False,
        timeout: int = 30
    ) -> ExecutionResult:
        """批量执行配置命令"""
        
    def show_command(
        self,
        command: str
    ) -> Dict[str, Any]:
        """执行 show 命令并返回结构化数据"""
        
    def check_connectivity(self) -> bool:
        """测试设备连通性"""
```

**错误处理策略**:
```
┌─────────────┐
│ Send Request│
└──────┬──────┘
       │
       ▼
┌─────────────┐    Yes    ┌──────────────┐
│ HTTP >= 400?├──────────►│ Parse Error  │
└──────┬──────┘            │ Return Detail│
       │ No                └──────────────┘
       ▼
┌─────────────┐
│ Parse JSON  │
└──────┬──────┘
       │
       ▼
┌─────────────┐    Yes    ┌──────────────┐
│JSON-RPC Err?├──────────►│ Extract Code │
└──────┬──────┘            │ & Message    │
       │ No                └──────────────┘
       ▼
┌─────────────┐
│ Return Data │
└─────────────┘
```

---

### 2.3 ConfigValidator（配置校验器）

**职责**: 验证配置是否在设备上正确生效

**校验流程**:
```
Apply Policy
     ↓
┌─────────────────────────────────┐
│  Wait for Device Processing     │ (可选: sleep 1-2s)
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Execute Show Commands           │
│  • show ip access-lists          │
│  • show class-map                │
│  • show policy-map               │
│  • show run interface            │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Parse Device Responses          │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Compare Expected vs Actual      │
│  • ACL rules match?              │
│  • Class-map references correct? │
│  • Policy-map applied?           │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Generate Validation Report      │
│  {passed: bool, details: [...]}  │
└─────────────────────────────────┘
```

---

## 3. 数据模型

### 3.1 PolicyModel（策略数据模型）

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ACLRule:
    sequence: int
    action: str  # permit | deny
    protocol: str  # tcp | udp | ip | icmp
    source: str
    destination: str
    source_port: Optional[List[int]] = None
    dest_port: Optional[List[int]] = None

@dataclass
class ACLModel:
    name: str
    type: str  # ipv4 | ipv6
    rules: List[ACLRule]

@dataclass
class ClassMapModel:
    name: str
    match_type: str  # match-any | match-all
    conditions: List[Dict[str, Any]]

@dataclass
class PolicyMapClass:
    class_name: str
    actions: List[Dict[str, Any]]

@dataclass
class PolicyMapModel:
    name: str
    classes: List[PolicyMapClass]

@dataclass
class ServicePolicyModel:
    interface: str
    direction: str  # input | output
    policy_map: str

@dataclass
class PolicyModel:
    id: str
    name: str
    description: str
    version: str
    acls: List[ACLModel]
    class_maps: List[ClassMapModel]
    policy_maps: List[PolicyMapModel]
    service_policies: List[ServicePolicyModel]
```

### 3.2 ExecutionResult（执行结果）

```python
@dataclass
class ExecutionResult:
    success: bool
    executed_commands: List[str]
    device_responses: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    http_status: int
    duration_ms: int
    validation: Optional[ValidationResult] = None
```

---

## 4. 安全设计

### 4.1 认证与授权

**MVP 阶段**:
- 基础认证: 设备连接使用用户名/密码（存储在 .env）
- API 无认证（仅内网访问）

**后续增强**:
- API Key 认证
- JWT Token
- RBAC 角色权限

### 4.2 数据保护

- 敏感信息（密码）存储在环境变量
- 日志中不记录密码明文
- HTTPS 通信加密（NX-API）

### 4.3 审计追踪

所有操作记录到审计日志：
```json
{
  "timestamp": "2025-10-15T14:30:00Z",
  "operation": "apply_policy",
  "user": "admin",
  "policy_id": "course-priority-v1",
  "result": "success",
  "device": "192.168.1.1"
}
```

---

## 5. 性能优化

### 5.1 批量操作

**单个 HTTP 请求发送多条命令**:
```json
{
  "jsonrpc": "2.0",
  "method": "cli_conf",
  "params": {
    "cmd": "ip access-list ACL_TEST ; 10 permit ip any any",
    "version": 1
  },
  "id": 1
}
```

优化效果：
- 减少网络往返次数
- 降低设备处理开销
- 提升整体性能 3-5x

### 5.2 缓存策略

- 缓存设备 show 命令结果（TTL: 60s）
- 缓存策略解析结果（避免重复解析）

---

## 6. 可扩展性

### 6.1 插件化架构（未来）

```
┌────────────────────────────────────┐
│      Plugin Manager                │
├────────────────────────────────────┤
│ • load_plugin(name)                │
│ • register_hook(event, callback)   │
└────────────────────────────────────┘
           │
           ├──────────┬──────────┐
           ▼          ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Notifier │ │  Backup  │ │  Metrics │
    │  Plugin  │ │  Plugin  │ │  Plugin  │
    └──────────┘ └──────────┘ └──────────┘
```

支持自定义插件：
- 告警通知（Email/Slack/Webhook）
- 配置备份（Git/S3）
- 指标收集（Prometheus）

### 6.2 多设备支持

```python
class DeviceManager:
    def add_device(self, device: DeviceConfig)
    def apply_policy_to_all(self, policy: PolicyModel)
    def execute_parallel(self, commands: List[str])
```

---

## 7. 部署架构

### 7.1 单机部署（MVP）

```
┌─────────────────────────────────────┐
│      Application Server             │
│  ┌───────────────────────────────┐  │
│  │  Flask App (app.py)           │  │
│  │  • API Server                 │  │
│  │  • Business Logic             │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  File Storage                 │  │
│  │  • policies/                  │  │
│  │  • logs/                      │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
             │
             │ HTTPS
             ▼
┌─────────────────────────────────────┐
│      Nexus 9000v                    │
└─────────────────────────────────────┘
```

### 7.2 生产部署（未来）

```
          ┌──────────────┐
          │ Load Balancer│
          └──────┬───────┘
                 │
       ┌─────────┼─────────┐
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  App Node 1 │     │  App Node 2 │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 │
                 ▼
        ┌────────────────┐
        │  Database      │
        │  (PostgreSQL)  │
        └────────────────┘
```

---

## 8. 监控与告警

### 8.1 健康检查端点

```
GET /api/health
{
  "status": "healthy",
  "components": {
    "api": "ok",
    "device_connection": "ok",
    "disk_space": "ok"
  },
  "uptime_seconds": 86400
}
```

### 8.2 关键指标

- API 请求延迟（P50/P95/P99）
- 错误率
- 设备连接成功率
- 策略应用成功率

---

## 附录

### A. 技术栈总结

| 层级 | 技术 | 用途 |
|------|------|------|
| 应用层 | Flask | Web 框架 |
| 业务层 | Python 3.9+ | 核心逻辑 |
| 数据层 | YAML + JSON | 配置存储 |
| 通信层 | HTTPS + JSON-RPC | 设备通信 |
| 测试 | pytest | 单元/集成测试 |
| 文档 | Markdown + OpenAPI | 技术文档 |

### B. 代码规范

- 遵循 PEP 8 风格指南
- 使用类型提示（Type Hints）
- 文档字符串（Docstrings）必须包含
- 单元测试覆盖率 >85%

---

**文档维护**: 请在架构变更时同步更新本文档。
