// SDN QoS 策略管理系统 - 上传页面 JavaScript

const API_BASE = '/api';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('policy-file');
    const uploadForm = document.getElementById('upload-form');

    // 文件选择事件
    fileInput.addEventListener('change', handleFileSelect);

    // 表单提交事件
    uploadForm.addEventListener('submit', handleFormSubmit);
});

// 处理文件选择
function handleFileSelect(event) {
    const file = event.target.files[0];

    if (!file) {
        hideFileInfo();
        return;
    }

    // 显示文件信息
    showFileInfo(file);

    // 读取文件内容预览
    const reader = new FileReader();
    reader.onload = function (e) {
        const content = e.target.result;
        showFilePreview(content);
    };
    reader.readAsText(file);
}

// 显示文件信息
function showFileInfo(file) {
    const fileInfoDiv = document.getElementById('file-info');
    const filenameSpan = document.getElementById('filename');
    const filesizeSpan = document.getElementById('filesize');

    filenameSpan.textContent = file.name;
    filesizeSpan.textContent = formatFileSize(file.size);

    fileInfoDiv.style.display = 'block';
}

// 隐藏文件信息
function hideFileInfo() {
    document.getElementById('file-info').style.display = 'none';
    document.getElementById('preview-section').style.display = 'none';
}

// 显示文件预览
function showFilePreview(content) {
    const previewSection = document.getElementById('preview-section');
    const previewPre = document.getElementById('file-preview');

    // 限制预览长度
    const maxLength = 1000;
    let displayContent = content;

    if (content.length > maxLength) {
        displayContent = content.substring(0, maxLength) + '\n\n... (内容过长，已截断)';
    }

    previewPre.textContent = displayContent;
    previewSection.style.display = 'block';
}

// 处理表单提交
async function handleFormSubmit(event) {
    event.preventDefault();

    const fileInput = document.getElementById('policy-file');
    const uploadBtn = document.getElementById('upload-btn');
    const progressBar = document.getElementById('upload-progress');
    const errorDiv = document.getElementById('upload-error');
    const successDiv = document.getElementById('upload-success');

    // 验证文件
    if (!fileInput.files || fileInput.files.length === 0) {
        showError('请选择文件');
        return;
    }

    const file = fileInput.files[0];

    // 验证文件类型
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.yaml') && !fileName.endsWith('.yml')) {
        showError('文件格式错误，只支持 .yaml 或 .yml 文件');
        return;
    }

    // 隐藏消息
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    // 显示进度条
    uploadBtn.disabled = true;
    progressBar.style.display = 'block';

    try {
        // 创建 FormData
        const formData = new FormData();
        formData.append('file', file);

        // 上传文件
        const response = await fetch(`${API_BASE}/policies`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        // 隐藏进度条
        progressBar.style.display = 'none';
        uploadBtn.disabled = false;

        if (data.success) {
            showSuccess(`策略上传成功！<br><br>
                <strong>策略 ID:</strong> ${data.policy_id}<br>
                <strong>名称:</strong> ${data.policy.name}<br><br>
                <a href="/">查看策略列表</a>`);

            // 3秒后自动跳转
            setTimeout(() => {
                window.location.href = '/';
            }, 3000);
        } else {
            // 处理验证错误
            if (data.validation_errors) {
                const errorList = data.validation_errors.map(e => `  • ${e}`).join('<br>');
                showError(`策略验证失败：<br><br>${errorList}`);
            } else {
                showError(data.error || '上传失败');
            }
        }
    } catch (error) {
        console.error('上传错误:', error);
        progressBar.style.display = 'none';
        uploadBtn.disabled = false;
        showError(`上传失败: ${error.message}`);
    }
}

// 显示错误消息
function showError(message) {
    const errorDiv = document.getElementById('upload-error');
    errorDiv.innerHTML = `❌ ${message}`;
    errorDiv.style.display = 'block';

    // 滚动到错误消息
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// 显示成功消息
function showSuccess(message) {
    const successDiv = document.getElementById('upload-success');
    successDiv.innerHTML = `✅ ${message}`;
    successDiv.style.display = 'block';

    // 滚动到成功消息
    successDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// 重置表单
function resetForm() {
    document.getElementById('upload-form').reset();
    hideFileInfo();
    document.getElementById('upload-error').style.display = 'none';
    document.getElementById('upload-success').style.display = 'none';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
