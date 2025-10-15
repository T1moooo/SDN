"""测试 Flask 应用是否正常运行"""
import requests
import time

# 等待应用启动
time.sleep(2)

# 测试健康检查
try:
    response = requests.get('http://localhost:5000/api/health')
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print("\n✅ 应用运行正常！")
except Exception as e:
    print(f"❌ 连接失败: {e}")

# 测试配置端点
try:
    response = requests.get('http://localhost:5000/api/config')
    print(f"\n配置信息:")
    print(response.json())
except Exception as e:
    print(f"配置端点失败: {e}")

# 测试策略列表
try:
    response = requests.get('http://localhost:5000/api/policies')
    print(f"\n策略列表:")
    print(response.json())
except Exception as e:
    print(f"策略列表失败: {e}")
