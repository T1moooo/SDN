// SDN QoS 策略管理系统 - 日志页面 JavaScript

const API_BASE = '/api';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function () {
    // 设置默认日期为今天
    const dateInput = document.getElementById('date-filter');
    dateInput.value = new Date().toISOString().split('T')[0];

    // 加载日志
    loadLogs();

    // 日期变化事件
    dateInput.addEventListener('change', loadLogs);

    // 行数变化事件
    document.getElementById('lines-filter').addEventListener('change', loadLogs);
});

// 加载日志
async function loadLogs() {
    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error-message');
    const containerEl = document.getElementById('logs-container');
    const emptyEl = document.getElementById('empty-state');

    // 获取过滤参数
    const date = document.getElementById('date-filter').value;
    const lines = document.getElementById('lines-filter').value;

    // 显示加载状态
    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';
    containerEl.style.display = 'none';
    emptyEl.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/logs?date=${date}&lines=${lines}`);
        const data = await response.json();

        loadingEl.style.display = 'none';

        if (!data.success) {
            throw new Error(data.error || '加载失败');
        }

        if (data.count === 0) {
            emptyEl.style.display = 'block';
        } else {
            containerEl.style.display = 'block';
            document.getElementById('logs-count').textContent = data.count;
            document.getElementById('logs-date').textContent = data.date;
            renderLogs(data.logs);
        }
    } catch (error) {
        console.error('加载日志失败:', error);
        loadingEl.style.display = 'none';
        errorEl.textContent = `加载失败: ${error.message}`;
        errorEl.style.display = 'block';
    }
}

// 渲染日志列表
function renderLogs(logs) {
    const tbody = document.getElementById('logs-body');
    tbody.innerHTML = '';

    // 倒序显示（最新的在上面）
    logs.reverse().forEach(log => {
        const tr = document.createElement('tr');

        // 解析日志
        const timestamp = log.timestamp ?
            new Date(log.timestamp).toLocaleString('zh-CN') :
            '-';

        const level = log.level || 'INFO';
        const operation = log.operation || '-';
        const policyId = log.policy_id || '-';
        const message = log.message || '';

        // 级别样式
        const levelClass = {
            'DEBUG': 'level-debug',
            'INFO': 'level-info',
            'WARNING': 'level-warning',
            'ERROR': 'level-error'
        }[level] || 'level-info';

        tr.innerHTML = `
            <td>${timestamp}</td>
            <td><span class="level-badge ${levelClass}">${level}</span></td>
            <td>${operation}</td>
            <td><code>${policyId}</code></td>
            <td>${escapeHtml(message)}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick='viewLogDetail(${JSON.stringify(log)})'>
                    🔍 详情
                </button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

// 查看日志详情
function viewLogDetail(log) {
    const content = JSON.stringify(log, null, 2);
    document.getElementById('detail-content').textContent = content;
    document.getElementById('detail-modal').style.display = 'block';
}

// 刷新日志
function refreshLogs() {
    loadLogs();
}

// 导出日志
async function exportLogs() {
    const date = document.getElementById('date-filter').value;
    const lines = document.getElementById('lines-filter').value;

    try {
        const response = await fetch(`${API_BASE}/logs?date=${date}&lines=${lines}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error);
        }

        // 转换为 JSON 字符串
        const jsonStr = JSON.stringify(data.logs, null, 2);

        // 创建下载
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logs-${date}.json`;
        a.click();
        URL.revokeObjectURL(url);

        alert('日志导出成功!');
    } catch (error) {
        alert(`导出失败: ${error.message}`);
    }
}

// 关闭模态框
function closeModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// 点击模态框外部关闭
window.onclick = function (event) {
    const modal = document.getElementById('detail-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// HTML 转义（防止 XSS）
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
