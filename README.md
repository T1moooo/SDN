# 校园网智能运维与策略管理平台

本项目是一个基于软件定义网络（SDN）思想的Python应用，旨在为校园网提供自动化的运维和策略管理能力。它利用Cisco Nexus 9000v交换机的NX-API，实现了动态QoS策略管理和基础的网络健康监控。

## 核心功能

1.  **基于策略的QoS自动化**:
    - 通过简单的`policy.yaml`文件定义网络意图（例如，为关键应用提升网络优先级）。
    - 平台自动将YAML策略翻译为设备配置命令，并通过NX-API下发。

2.  **网络健康监控与可视化**:
    - 后台定时采集交换机的关键性能指标（KPI），如CPU利用率、接口状态等。
    - 提供一个简洁的Web仪表盘，实时展示网络健康状况。

## 技术架构

系统采用模块化设计，主要包括：

-   **Web服务 (`app.py`)**: 基于Flask，提供API接口和Web仪表盘。
-   **策略引擎 (`engine.py`)**: 读取YAML策略文件，并将其翻译成NX-API命令。
-   **配置下发器 (`deployer.py`)**: 负责与交换机通信，执行配置命令。
-   **数据采集器 (`collector.py`)**: 负责从交换机采集状态数据。
-   **任务调度器 (`APScheduler`)**: 在后台定时运行数据采集任务。

```mermaid
graph TD
    subgraph 定义与交互
        A[策略文件 (policy.yaml)]
        B[Web仪表盘]
    end

    subgraph 智能运维平台 (Python应用)
        C[Web服务 (Flask API)]
        D[策略引擎]
        E[任务调度器]
        F[数据采集模块]
        G[配置下发模块]
    end

    subgraph 网络设备 (Nexus 9000v)
        H[NX-API REST]
    end

    A --> D
    B --> C
    C --> D
    E --> F
    F --> H
    G --> H
    D --> G
```

## 环境准备与运行

1.  **克隆项目并安装依赖**:
    ```bash
    git clone <repository_url>
    cd <project_directory>
    ```

2.  **配置环境变量**:
    - 复制 `.env.example` 文件为 `.env`。
    - 编辑 `.env` 文件，填入你的Nexus交换机的IP地址、用户名和密码。
    ```
    SWITCH_IP=192.168.1.1
    SWITCH_USERNAME=admin
    SWITCH_PASSWORD=your_secure_password
    ```

3.  **创建并激活Python虚拟环境**:
    ```powershell
    # (在PowerShell中)
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

4.  **安装依赖库**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **运行应用**:
    ```bash
    python app.py
    ```
    应用启动后，你可以在浏览器中访问 `http://127.0.0.1:5001/dashboard` 来查看监控仪表盘。

## 如何使用

### 通过Web API应用策略

你可以通过发送POST请求来触发策略的下发。

```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"policy_file": "policy.yaml"}' \
http://127.0.0.1:5001/api/apply-policy
```

### 独立测试脚本

项目中包含几个用于独立测试的脚本：

-   `qos_api_explorer.py`: 演示如何通过API完成一次完整的QoS配置与清理，用于核心功能验证。
-   `connection_test.py`: 用于测试与交换机的基本连接是否通畅，排除底层网络或SSL问题。
-   `engine.py`: 可直接运行以测试YAML策略引擎。

```bash
# 运行连接测试
python connection_test.py

# 运行策略引擎测试
python engine.py
```
