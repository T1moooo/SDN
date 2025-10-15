// SDN QoS 策略管理系统 - 主页 JavaScript

// API 基础 URL
const API_BASE = '/api';

// 当前预览的策略 ID
let currentPreviewPolicyId = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function () {
    loadConfig();
    loadPolicies();
    testConnection();
});

// 加载配置信息
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const data = await response.json();

        if (data) {
            document.getElementById('switch-ip').textContent =
                `${data.switch_ip}:${data.switch_port}`;
        }
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

// 测试交换机连接
async function testConnection() {
    const statusEl = document.getElementById('connection-status');
    statusEl.textContent = '检测中...';
    statusEl.className = 'value status-loading';

    try {
        const response = await fetch(`${API_BASE}/switch/test`);
        const data = await response.json();

        if (data.connected) {
            statusEl.textContent = '已连接 ✓';
            statusEl.className = 'value status-connected';
        } else {
            statusEl.textContent = '未连接 ✗';
            statusEl.className = 'value status-disconnected';
        }
    } catch (error) {
        console.error('连接测试失败:', error);
        statusEl.textContent = '错误';
        statusEl.className = 'value status-disconnected';
    }
}

// 加载策略列表
async function loadPolicies() {
    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error-message');
    const tableEl = document.getElementById('policies-table');
    const emptyEl = document.getElementById('empty-state');

    // 显示加载状态
    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';
    tableEl.style.display = 'none';
    emptyEl.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/policies`);
        const data = await response.json();

        loadingEl.style.display = 'none';

        if (!data.success) {
            throw new Error(data.error || '加载失败');
        }

        // 更新策略数量
        document.getElementById('policy-count').textContent = data.count;

        if (data.count === 0) {
            emptyEl.style.display = 'block';
        } else {
            tableEl.style.display = 'table';
            renderPolicies(data.policies);
        }
    } catch (error) {
        console.error('加载策略失败:', error);
        loadingEl.style.display = 'none';
        errorEl.textContent = `加载失败: ${error.message}`;
        errorEl.style.display = 'block';
    }
}

// 渲染策略列表
function renderPolicies(policies) {
    const tbody = document.getElementById('policies-body');
    tbody.innerHTML = '';

    policies.forEach(policy => {
        const tr = document.createElement('tr');

        // 状态样式映射
        const statusClass = {
            'uploaded': 'status-uploaded',
            'validated': 'status-validated',
            'applied': 'status-applied',
            'failed': 'status-failed',
            'pending': 'status-pending'
        }[policy.status] || 'status-pending';

        const statusText = {
            'uploaded': '已上传',
            'validated': '已验证',
            'applied': '已应用',
            'failed': '失败',
            'pending': '待处理'
        }[policy.status] || '未知';

        // 格式化时间
        const createdAt = new Date(policy.created_at).toLocaleString('zh-CN');

        tr.innerHTML = `
            <td><code>${policy.id}</code></td>
            <td><strong>${policy.name}</strong></td>
            <td>${policy.description}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>${createdAt}</td>
            <td class="action-btns">
                <button class="btn btn-sm btn-primary" onclick="viewPolicy('${policy.id}')">
                    📄 详情
                </button>
                <button class="btn btn-sm btn-secondary" onclick="previewPolicy('${policy.id}')">
                    👁️ 预览
                </button>
                <button class="btn btn-sm btn-success" onclick="applyPolicy('${policy.id}', false)">
                    ✅ 应用
                </button>
                <button class="btn btn-sm btn-danger" onclick="deletePolicy('${policy.id}')">
                    🗑️ 删除
                </button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

// 查看策略详情
async function viewPolicy(policyId) {
    try {
        const response = await fetch(`${API_BASE}/policies/${policyId}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error);
        }

        const policy = data.policy;
        const content = `
<div class="detail-section">
    <h3>基本信息</h3>
    <p><strong>策略 ID:</strong> ${policy.id}</p>
    <p><strong>名称:</strong> ${policy.name}</p>
    <p><strong>描述:</strong> ${policy.description}</p>
    <p><strong>状态:</strong> ${policy.status}</p>
    <p><strong>创建时间:</strong> ${new Date(policy.created_at).toLocaleString('zh-CN')}</p>
</div>
<div class="detail-section">
    <h3>配置统计</h3>
    <p><strong>ACL 数量:</strong> ${policy.access_lists_count}</p>
    <p><strong>Class-map 数量:</strong> ${policy.class_maps_count}</p>
    <p><strong>Policy-map 数量:</strong> ${policy.policy_maps_count}</p>
    <p><strong>Service-policy 数量:</strong> ${policy.service_policies_count}</p>
</div>
        `;

        document.getElementById('detail-content').innerHTML = content;
        document.getElementById('detail-modal').style.display = 'block';
    } catch (error) {
        alert(`查看详情失败: ${error.message}`);
    }
}

// 预览策略命令
async function previewPolicy(policyId) {
    try {
        const response = await fetch(`${API_BASE}/policies/${policyId}/preview`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error);
        }

        currentPreviewPolicyId = policyId;
        document.getElementById('preview-content').textContent = data.preview;
        document.getElementById('preview-modal').style.display = 'block';
    } catch (error) {
        alert(`预览失败: ${error.message}`);
    }
}

// 从预览模态框应用策略
function applyPolicyFromPreview() {
    if (currentPreviewPolicyId) {
        closePreviewModal();
        applyPolicy(currentPreviewPolicyId, false);
    }
}

// 应用策略
async function applyPolicy(policyId, dryRun = false) {
    const action = dryRun ? 'Dry-run' : '应用';

    if (!dryRun && !confirm(`确定要应用策略 ${policyId} 到设备吗？`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/policies/${policyId}/apply`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ dry_run: dryRun })
        });

        const data = await response.json();

        if (data.success) {
            alert(`${action}成功!\n\n${data.message}\n\n耗时: ${data.result.duration_ms}ms`);
            refreshPolicies();
        } else {
            alert(`${action}失败:\n\n${data.message}`);
        }
    } catch (error) {
        alert(`${action}失败: ${error.message}`);
    }
}

// 删除策略
async function deletePolicy(policyId) {
    if (!confirm(`确定要删除策略 ${policyId} 吗？`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/policies/${policyId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            alert('删除成功!');
            refreshPolicies();
        } else {
            alert(`删除失败: ${data.error}`);
        }
    } catch (error) {
        alert(`删除失败: ${error.message}`);
    }
}

// 刷新策略列表
function refreshPolicies() {
    loadPolicies();
    testConnection();
}

// 关闭详情模态框
function closeModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// 关闭预览模态框
function closePreviewModal() {
    document.getElementById('preview-modal').style.display = 'none';
    currentPreviewPolicyId = null;
}

// 点击模态框外部关闭
window.onclick = function (event) {
    const detailModal = document.getElementById('detail-modal');
    const previewModal = document.getElementById('preview-modal');

    if (event.target === detailModal) {
        closeModal();
    }
    if (event.target === previewModal) {
        closePreviewModal();
    }
}
