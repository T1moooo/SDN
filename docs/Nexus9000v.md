# Nexus9000v

## 概要

本文档面向网络工程师与开发人员，旨在提供 Cisco Nexus 9000v 的基础概念、常用操作指南、与在 SDN/自动化场景下的实战经验与要点。包含 NX-API 使用注意事项、常见故障排查步骤与实用命令示例，便于在校园网或实验环境中部署与调试。

---

## 基础概念

### 设备与平台
- Nexus 9000v 是 Cisco 提供的虚拟交换机平台（以软件形式运行），常用于实验、开发或测试环境。
- 运行模式：NX-OS (软件版本)；可具备多种特性（L2/L3、QoS、ACL、VLAN、VXLAN等）。

### 管理接口
- 管理平面常见方式：Console、SSH、HTTP/HTTPS（NX-API）、NETCONF/RESTCONF（取决于版本和许可）。
- NX-API：Cisco 为 NX-OS 提供的 HTTP(S)-based JSON-RPC 接口，适合自动化脚本调用，能够执行 `show`（只读）或 `cli_conf`（配置）命令。

### 证书与加密
- NX-API 支持 HTTPS，但在虚拟或实验环境中往往使用自签名证书或直接配置为 HTTP（不推荐生产）。
- 在生产或校网场景，请配置受信任的证书并强制 HTTPS，避免凭证和配置命令在网络中明文传输。

### 命令与模式
- 交互式命令分为 `exec`（show）与 `config`（配置）模式，NX-API 的 `method` 字段通常为 `cli` 或 `cli_conf`。

---

## 使用指南

### 访问准备
1. 启用 NX-API（如尚未启用）：

```
configure terminal
feature nxapi
copy running-config startup-config
```

2. 检查管理接口的连通性（从控制主机）：

```powershell
# curl 测试（HTTP）
curl -v http://<SWITCH_IP>/ins

# curl 测试（HTTPS，跳过证书验证）
curl -k https://<SWITCH_IP>/ins
```

3. 推荐在 `.env` 或机密存储中管理用户名/密码，避免放在脚本中明文。


### 常用 NX-API 示例（Python requests）
- 只读命令（show）：

```python
payload = {
  "jsonrpc": "2.0",
  "method": "cli",
  "params": {"cmd": "show interface brief", "version": 1},
  "id": 1
}
res = requests.post(url, auth=(user, pwd), headers=headers, data=json.dumps([payload]), verify=False)
```

- 配置命令（cli_conf）：

```python
payload = [
  {"jsonrpc":"2.0", "method":"cli_conf", "params":{"cmd":"vlan 100", "version":1}, "id":1},
  {"jsonrpc":"2.0", "method":"cli_conf", "params":{"cmd":"name VLAN100", "version":1}, "id":2}
]
res = requests.post(url, auth=(user, pwd), headers=headers, data=json.dumps(payload), verify=False)
```

> 注意：某些 NX-OS 版本对一次性批量 `cli_conf` 的命令数量或顺序有要求，必要时分多次发送并检查返回结果。


### 常见配置示例

- 创建 VLAN：
```
configure terminal
vlan 100
name STUDENT_NET
exit
```

- 在接口上配置 QoS 策略示例：
```
configure terminal
ip access-list ACL_COURSE
  10 permit ip 10.1.1.10/32 any
class-map type qos CM_COURSE
  match access-group name ACL_COURSE
policy-map type qos PM_COURSE
  class CM_COURSE
    set dscp af41
interface Ethernet1/1
  service-policy type qos input PM_COURSE
exit
```

---

## 实战经验（在 SDN / 自动化 场景）

### 1) 开发与调试建议
- 从只读 `show` 命令开始验证连通性，确认 JSON 返回格式后再执行 `cli_conf`。
- 在虚拟环境中优先使用 HTTP 方便调试（但要注意安全）；生产环境必须使用 HTTPS 并配置受信任证书。
- 使用 `timeout` 与 `retry` 逻辑，避免因为短暂网络问题导致脚本失败。

### 2) 命令幂等性与回滚
- 自动化脚本应尽量保证幂等（idempotent），例如使用 `vlan 100`（重复执行无害）
- 对于不可逆或会覆盖现有策略的操作，先读取并保存当前配置（快照），在失败时回滚：
  - 方案A：在发送配置前使用 `show running-config` 保存相关片段；失败则把原配置写回。
  - 方案B：将变更封装为可逆命令序列（先应用，再在完成确认后删除备份）。

### 3) 策略冲突检测
- 在下发重要QoS或ACL策略前，先查询现有 class-map / policy-map / ACL，检测命名冲突或匹配范围重叠。
- 维护策略命名约定（例如 `PM_<policy_name>`），便于清理与审计。

### 4) 安全与审计
- 将操作日志化：记录谁（用户/服务）在何时对哪台设备下发了哪些命令以及返回结果。
- 对高权限API访问限制IP白名单或使用基于角色的访问控制（RBAC），并且使用API令牌或证书验证。

### 5) 性能与可用性
- 批量变更（如同时在多台设备上下发）时，采用并发但有速率限制的方式，以避免对交换机管理平面造成压力。
- 避免在高峰时段对关键接口或策略做大规模修改。

---

## 经验总结

- 对于快速验证与实验环境，Nexus 9000v + NX-API 是高效的选择。
- 自动化策略下发必须考虑幂等性、回滚与冲突检测，否则容易产生网络中断或策略覆盖问题。
- 在校园网等生产环境中，安全（HTTPS、证书、审计）永远是首要考虑。
- 先做小范围验证，再放大到批量下发；并确保有监控与可回滚方案。

---

## 信息参考

- Cisco NX-OS and NX-API 文档（Cisco 官方）
- NX-API JSON-RPC 接口说明
- Cisco CLI 命令参考手册
- 项目内部 `qos_api_explorer.py`、`connection_test.py`、`engine.py` 供示例参考


---

如果你希望我：
- 把该文档添加到 README 的链接中；
- 或者把内容拆成多个子文件（如 `nxapi.md`, `qos_practices.md`）；
- 或者把某些命令改成可复制的一键脚本（PowerShell / Bash）；
请告诉我，我会继续帮你完善。

---

## NX-SDK（NX-API） — Python 使用指南

下面补充一节面向 Python 开发者的 NX-API 使用指南，包含一个小型客户端封装示例、重试/超时与 SSL 处理建议、幂等与回滚模式示例，以及单元/集成测试建议。

### 概要

在 Python 中直接使用 `requests` 调用 NX-API 是最常见的做法。为降低重复代码并统一错误处理，建议封装一个轻量的客户端类，提供 `show`（只读）和 `config`（配置）两类方法，并在上层实现重试、超时、日志与回滚策略。

### 环境与依赖

- Python 3.8+
- requests（已在 `requirements.txt`）
- 可选：`urllib3` 的 `Retry` 或 `tenacity` 用于更灵活的重试策略

示例安装：

```powershell
pip install requests
# 可选的重试库
pip install tenacity
```

### 推荐的轻量 `NXAPIClient`（示例）

下面是一个同步、基于 `requests.Session` 的示例客户端：

```python
import json
import logging
from typing import List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class NXAPIClient:
  def __init__(self, url: str, username: str, password: str,
         timeout: int = 10, verify: bool = True, cert: Optional[str] = None,
         max_retries: int = 3):
    self.url = url
    self.auth = (username, password)
    self.timeout = timeout
    self.verify = cert if cert is not None else verify
    self.session = requests.Session()

    # Configure retries for idempotent requests
    retries = Retry(total=max_retries,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=frozenset(['GET', 'POST']))
    self.session.mount('https://', HTTPAdapter(max_retries=retries))
    self.session.mount('http://', HTTPAdapter(max_retries=retries))

  def _post(self, payload, expect_list: bool = True):
    data = json.dumps(payload)
    try:
      resp = self.session.post(self.url,
                   auth=self.auth,
                   headers={'Content-Type': 'application/json-rpc'},
                   data=data,
                   timeout=self.timeout,
                   verify=self.verify)
      resp.raise_for_status()
      return resp.json()
    except requests.exceptions.RequestException as e:
      logger.exception("NX-API request failed")
      raise

  def run_show(self, cmd: str):
    payload = {"jsonrpc": "2.0", "method": "cli", "params": {"cmd": cmd, "version": 1}, "id": 1}
    return self._post([payload])

  def run_config(self, commands: List[str]) -> Tuple[bool, List]:
    payload = []
    for i, cmd in enumerate(commands, 1):
      payload.append({
        "jsonrpc": "2.0",
        "method": "cli_conf",
        "params": {"cmd": cmd, "version": 1},
        "id": i
      })
    results = self._post(payload)
    # 返回 (success, results)
    if isinstance(results, list):
      for r in results:
        if 'error' in r:
          return False, results
      return True, results
    elif 'error' in results:
      return False, [results]
    return True, [results]

  def snapshot_running_config(self) -> Optional[str]:
    # 获取运行配置的文本快照（示例）
    res = self.run_show('show running-config')
    # 尽量从返回中提取 body 或文本部分
    return json.dumps(res)

  def rollback_from_snapshot(self, snapshot_text: str) -> bool:
    # 回滚示例：把 snapshot_text 拆成命令并下发
    # 注意：实际回滚需要解析并取出必要的命令片段
    # 这里给出一个占位说明
    raise NotImplementedError('Rollback needs project-specific logic')

```

### SSL / 证书处理建议

- 实验环境常用 `verify=False` 或接受自签名证书，但**切勿**在生产中长期使用 `verify=False`。
- 推荐做法：把受信任的 CA 或交换机证书放在控制机上，传 `cert='/path/to/ca_bundle.pem'` 给 `NXAPIClient` 的 `verify` 参数。
- 如果必须跳过验证，务必在日志和运维文档中记录风险，并限制客户端来源IP。

### 重试与退避策略

- 使用 `urllib3.Retry`（示例中已配置）或 `tenacity` 实现带指数退避的重试。
- 对配置类命令（`cli_conf`）请谨慎重试，因为重复执行可能具有副作用。推荐：
  - 先在脚本层实现幂等检测（如判断某个对象是否已存在），再决定是否重试。

### 幂等性与回滚模式（示例流程）

1. 读取并保存受影响对象的当前状态（快照）：相关 ACL、class-map、policy-map、接口配置等。
2. 生成要下发的命令，进行本地静态校验（命名冲突、语法检查、影响范围）。
3. 下发变更（分批、分阶段），每步都检查返回值；若发现错误，触发回滚流程。
4. 回滚：根据事先保存的快照把配置写回或下发相应的 `no ...` 命令。

示例伪代码：

```python
client = NXAPIClient(url, user, pwd, verify=False)

# 1. snapshot
snapshot = client.snapshot_running_config()

try:
  success, res = client.run_config(commands)
  if not success:
    # 解析失败并回滚
    client.rollback_from_snapshot(snapshot)
except Exception:
  client.rollback_from_snapshot(snapshot)
  raise
```

### 并发与节流

- 当要对多台交换机或对单台设备进行大量命令时，使用并发库（`concurrent.futures.ThreadPoolExecutor`）配合限速以避免压垮管理平面。
- 对同一设备的并发写操作要特别小心，务必串行化或使用分批锁。

### 单元测试与集成测试建议

- 单元测试：使用 `unittest.mock` 或 `responses` 库 mock `requests.Session.post`，验证客户端在不同响应下的行为（成功、HTTP错误、API内部error字段）。
- 集成测试：在受控的实验环境中运行 `connection_test.py`、`qos_api_explorer.py` 验证端到端流程。建议使用一个专门的测试交换机实例或容器化的 Nexus 9000v。

示例单元测试（伪代码）：

```python
from unittest.mock import patch

@patch('requests.Session.post')
def test_run_show_success(mock_post):
  mock_post.return_value.status_code = 200
  mock_post.return_value.json.return_value = {'result': {'body': {'dummy': 1}}}
  client = NXAPIClient(url, 'u', 'p', verify=False)
  res = client.run_show('show version')
  assert 'result' in res
```

### 实践小贴士

- 先在脚本中实现“dry-run”模式：把要发送的命令打印或写入日志，人工审阅后再启用真实下发。
- 对重要变更，采用蓝绿或分段发布策略：先在一台或一小组交换机上验证，确认正确后再扩展到全网。

---

如果你愿意，我可以：

- 把上述 `NXAPIClient` 代码加入到项目（例如 `nxapi_client.py`），并为其编写 2-3 个单元测试；
- 将 `engine.py` 中调用 `deployer.send_config_commands` 的逻辑改为使用 `NXAPIClient`（兼容现有接口）；
- 或者把示例测试用例添加到 `tests/` 目录并用 `pytest` 运行验证。

请选择下一步，我会继续实现并在仓库中提交改动。