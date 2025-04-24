window.addEventListener('DOMContentLoaded', async () => {
    // ===== 深色模式初始化 =====
    const isDark = localStorage.getItem('dark-mode');
    const toggleBtn = document.getElementById('toggleDarkMode');
    const sidebarToggle = document.getElementById('sidebarToggle');

    if (isDark === null || isDark === 'true') {
        document.body.classList.add('dark-mode');
        if (toggleBtn) toggleBtn.innerHTML = '🌞 淺色模式';
    } else {
        document.body.classList.remove('dark-mode');
        if (toggleBtn) toggleBtn.innerHTML = '🌙 深色模式';
    }

    if (sidebarToggle) {
        sidebarToggle.textContent = document.body.classList.contains('sidebar-collapsed') ? '→' : '←';
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            toggleBtn.innerHTML = isDark ? '🌞 淺色模式' : '🌙 深色模式';
            localStorage.setItem('dark-mode', isDark);
        });
    }

    // ===== 動態載入分析結果卡片 =====
    const container = document.getElementById('resultCards');
    if (!container) return;

    try {
        const res = await fetch('/get-results');
        const data = await res.json();

        if (!data || data.length === 0) {
            container.innerHTML = '<p>⚠️ 尚無分析資料，請先回首頁上傳 Excel。</p>';
            return;
        }

    const container = document.getElementById('resultCards');

    data.forEach(row => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <h3>🎯 Incident: ${row.id}</h3>
            <div class="card-grid">
                <div><strong>Config Item:</strong><span>${row.configurationItem || '—'}</span></div>
                <div><strong>Severity:</strong><span>${row.severityScore}</span></div>
                <div><strong>Frequency:</strong><span>${row.frequencyScore}</span></div>
                <div><strong>Impact:</strong><span>${row.impactScore}</span></div>
                <div><strong>Risk Level:</strong>
                    <span class="badge ${row.riskLevel}">${row.riskLevel}</span>
                </div>
                <div><strong>Solution:</strong><span>${row.solution || '—'}</span></div>
                <div><strong>Location:</strong><span>${row.location || '—'}</span></div>
                <div><strong>Analysis Date:</strong><span>${row.analysisDate || '—'}</span></div>
            </div>
        `;
        container.appendChild(card);
    });



    } catch (err) {
        console.error('🚨 無法取得結果：', err);
        container.innerHTML = '<p style="color:red;">❌ 無法載入分析結果。</p>';
    }
});


// 定義函數：切換側邊欄的顯示狀態
function toggleSidebar() {
    // 切換側邊欄的樣式
    document.body.classList.toggle('sidebar-collapsed');
    // 獲取側邊欄切換按鈕元素
    const toggleBtn = document.getElementById('sidebarToggle');
    // 根據側邊欄狀態更新按鈕文字
    if (document.body.classList.contains('sidebar-collapsed')) {
        toggleBtn.textContent = '→'; // 側邊欄收起時顯示箭頭向右
    } else {
        toggleBtn.textContent = '←'; // 側邊欄展開時顯示箭頭向左
    }
}

// 定義函數：平滑滾動到指定的元素
function navigateTo(id) {
    // 獲取目標元素
    const target = document.getElementById(id);
    if (target) {
        // 滾動到目標元素，並啟用平滑滾動效果
        target.scrollIntoView({ behavior: 'smooth' });
    }
}

// 定義函數：導航到指定的頁面
function navigateTo1(page) {
    if (page === 'upload') {
        // 導航到 Flask 的首頁路由
        window.location.href = '/';
    } else if (page === 'result') {
        // 導航到 Flask 的 /result 路由
        window.location.href = '/result';
    } else if (page === 'history') {
        // 導航到 Flask 的 /history 路由
        window.location.href = '/history';
    }
}