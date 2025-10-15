# SDN QoS 策略管理系统

🌐 基于 Cisco Nexus NX-API 的声明式 QoS 策略自动化管理系统

## 📖 项目简介

本项目通过 Web UI 管理校园网 QoS 策略，解决关键应用（如选课系统）与视频流、P2P 下载竞争带宽的问题。

**核心功能**：
- 📤 通过 Web UI 上传 YAML 格式策略
- ✅ 自动验证策略完整性
- 🔄 自动生成 Cisco NX-CLI 配置命令
- 🚀 一键下发配置到 Nexus 设备
- 📊 可视化策略列表与操作日志
- 🧪 Dry-run 模式预览命令

## 🏗️ 技术架构

```
前端 UI (HTML/CSS/JS) 
    ↓ REST API
Flask 后端
    ↓
策略引擎 (YAML → CLI)
    ↓
NX-API 客户端 (JSON-RPC)
    ↓
Cisco Nexus 9000v
```

**核心模块**：
- **app.py** - Flask Web 应用和 REST API
- **core/engine.py** - YAML 策略解析与 CLI 命令生成
- **core/deployer.py** - NX-API 客户端与配置下发
- **core/models.py** - 数据模型定义
- **utils/logger.py** - 日志系统
- **frontend/** - Web UI 界面

## 📁 项目结构

```
SDN/
├── app.py                      # Flask 应用入口
├── config.py                   # 配置管理
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
├── core/                       # 核心业务逻辑
│   ├── models.py               # 数据模型
│   ├── engine.py               # 策略引擎
│   └── deployer.py             # NX-API 客户端
├── utils/                      # 工具模块
│   └── logger.py               # 日志系统
├── frontend/                   # 前端界面
│   ├── index.html              # 主页
│   ├── upload.html             # 上传页面
│   ├── logs.html               # 日志页面
│   └── static/                 # 静态资源
├── policies/                   # 策略文件
│   ├── examples/               # 示例策略
│   └── uploaded/               # 用户上传
└── logs/                       # 日志目录
```

## 🚀 快速开始

### 1. 环境准备

**要求**：
- Python 3.9+
- Cisco Nexus 9000v 或 DevNet Sandbox 访问权限

**安装依赖**：
```powershell
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```powershell
# 复制配置模板
Copy-Item .env.example .env

# 编辑 .env 填入设备信息
# SWITCH_IP=sbx-nxos-mgmt.cisco.com
# SWITCH_USERNAME=admin
# SWITCH_PASSWORD=Admin_1234!
```

### 3. 启动应用

```powershell
python app.py
```

访问: http://localhost:5000

### 4. 上传策略

1. 打开浏览器访问 http://localhost:5000/upload
2. 选择策略文件（如 `policies/examples/course-priority.yaml`）
3. 点击"上传"按钮
4. 返回主页查看策略列表
5. 点击"预览"查看生成的命令
6. 点击"应用"下发配置到设备

## 📝 策略文件格式

策略使用 YAML 格式，示例：

```yaml
---
id: course-priority-v1
name: "选课系统高优先级策略"
description: "确保选课系统流量获得最高优先级"

access_lists:
  - name: ACL_COURSE_SELECTION
    type: ipv4
    rules:
      - sequence: 10
        action: permit
        protocol: tcp
        source: 10.100.0.0/16
        destination: any
        dest_port: [80, 443]

class_maps:
  - name: CLASS_CRITICAL_APPS
    match_type: match-any
    conditions:
      - type: access-group
        name: ACL_COURSE_SELECTION

policy_maps:
  - name: PM_CAMPUS_QOS
    classes:
      - class_name: CLASS_CRITICAL_APPS
        actions:
          - type: set
            parameter: dscp
            value: ef

service_policies:
  - interface: Ethernet1/1
    direction: input
    policy_map: PM_CAMPUS_QOS
```

**更多示例**：查看 `policies/examples/` 目录

## 🔧 API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/policies` | 获取策略列表 |
| POST | `/api/policies` | 上传策略 |
| GET | `/api/policies/{id}` | 获取策略详情 |
| GET | `/api/policies/{id}/preview` | 预览命令 |
| POST | `/api/policies/{id}/apply` | 应用策略 |
| DELETE | `/api/policies/{id}` | 删除策略 |
| GET | `/api/logs` | 查询日志 |
| GET | `/api/switch/test` | 测试连接 |

## 🧪 测试

```powershell
# 测试 NX-API 连接
curl http://localhost:5000/api/switch/test

# 测试健康检查
curl http://localhost:5000/api/health
```

## 📊 日志系统

日志保存在 `logs/` 目录：
- `app.log` - 应用日志
- `operations/YYYY-MM-DD.log` - 操作日志（JSON 格式）

通过 Web UI 查看：http://localhost:5000/logs

## ⚠️ 注意事项

1. **生产环境**：修改 `.env` 中的 `SECRET_KEY`
2. **SSL 证书**：生产环境启用 `SWITCH_VERIFY_SSL=True`
3. **Dry-run**：首次使用建议启用 `DRY_RUN=True` 测试
4. **备份**：应用策略前备份设备配置
5. **权限**：确保 NX-API 用户有配置权限

## 📚 参考文档

- [Cisco NX-API 文档](https://developer.cisco.com/docs/nx-os/)
- [DevNet Sandbox](https://devnetsandbox.cisco.com/)
- [技术方案文档](./技术方案.md)

## 📄 许可证

MIT License
