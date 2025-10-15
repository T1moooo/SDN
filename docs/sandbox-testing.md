## DevNet Sandbox (sbx-nxos-mgmt) — 快速测试与诊断记录

本文件基于实时测试输出整理，记录如何用 curl 与 Python 脚本验证 NX-API（JSON-RPC）、常见错误含义与修复建议。

### 已验证的环境
- Host: https://sbx-nxos-mgmt.cisco.com
- Username: admin
- Password: Admin_1234!

### 验证步骤与关键输出

1) 只读命令（show version）成功：

示例命令：
```powershell
curl -k -u admin:Admin_1234! -H "Content-Type: application/json-rpc" \
  -d '[{"jsonrpc":"2.0","method":"cli","params":{"cmd":"show version","version":1},"id":1}]' \
  https://sbx-nxos-mgmt.cisco.com/ins
```

输出说明：服务器返回 JSON，包含 `result.body`，例中显示 `nxos_ver_str` 等字段，说明读接口可用且认证正常。

2) 配置类命令失败示例（缺少 version）

如果命令的 `params` 缺少 `version` 字段，NX-API 会返回 HTTP 400 和 JSON-RPC 错误：

```
{"error": {"code": -32600, "message": "Invalid request", "data": {"msg": "The required NX-API \"version\" object was not found in params structure"}}}
```

因此：所有 `cli` 或 `cli_conf` 的 `params` 必须包含 `version`（通常使用 1）。

3) 配置下发的常见限制

- 部分 DevNet Sandbox 实例对写操作有限制（只读或仅允许特定命令）。如果写操作被网关拒绝，可能返回 403/404/400 或在返回体中带有更明确的错误信息。
- 若某条命令被设备拒绝（例如语法或权限问题），设备会在相应命令的返回中包含 `error` 字段——脚本应当把这些原始返回记录下来以便诊断。

### 建议的排查步骤（按优先级）
1. 用带认证的 curl 执行 `show`（确认基本连通与认证）。
2. 用带认证的 curl 执行最小的 `cli_conf`（包含 `version`）来验证是否允许配置写操作。若返回 4xx/5xx，请查看返回体 JSON 的 `error.data.msg`。
3. 若 curl 成功，但脚本失败：在脚本中打印完整的 `response.status_code` 和 `response.text`（或 resp.json）以获得设备/网关的原始错误信息。
4. 若沙箱不允许写操作：改用 Dry-Run 模式（仅生成并打印命令），或在能写的实体设备/本地镜像上继续测试。

### 常见修复
- 确保 payload 的 `params` 包含 `"version": 1`。
- 对配置命令使用 `cli_conf` 方法并把每个命令构造成单独的 JSON-RPC 请求元素（批量发送时注意 API 的支持情况）。
- 在代码中对失败响应返回更多上下文（HTTP 状态码、返回体）以便定位哪条命令失败和失败原因。

---

如果需要，我可以把项目改为默认在沙箱环境下使用 `DRY_RUN=true`（只打印命令），或把失败时的原始响应自动保存到 `logs/` 目录供分析。
