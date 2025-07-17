let currentPage = 1;         // 現在在第幾頁
let pageSize = 3;            // 每頁幾筆（和 Bootstrap 卡片排法對齊）
let totalPages = 1;          // 全部有幾頁

const historyList = document.getElementById('historyList');
const noHistoryMsg = document.getElementById('no-history-msg');


async function loadHistoryPage(page) {
    try {
        // 加上 page/pageSize 查詢參數
        const res = await fetch(`/history-list?page=${page}&pageSize=${pageSize}`);
        const data = await res.json();
        const savedHistory = data.records || [];
        const total = data.total || 0;

        // 算出總頁數
        totalPages = Math.ceil(total / pageSize);
        currentPage = page;

        // 顯示/隱藏「沒有紀錄」訊息
        noHistoryMsg.style.display = (savedHistory.length === 0) ? 'block' : 'none';

        // 清空原內容
        historyList.innerHTML = '';

        // 渲染這一頁所有紀錄
        savedHistory.forEach(item => {
            const li = document.createElement('div');
            li.className = "col-12 col-sm-6 col-md-4";
            li.innerHTML = `
                <div class="history-item card p-3 h-100 shadow-sm">
                    <div class="history-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-1">${item.file}</h5>
                        <small class="text-extra-muted">${item.time}</small>
                    </div>
                    <p class="mb-2 text-secondary">${item.summary}</p>
                    <div class="btn-group mt-auto" role="group">
                        <a href="/get-json?file=${item.uid}.json" target="_blank"
                        class="btn btn-sm btn-outline-info">🧾 預覽 JSON</a>
                        <a href="/download-excel?uid=${item.uid}" download
                        class="btn btn-sm btn-outline-success">📥 分析 Excel</a>
                        <a href="/download-original?uid=${item.uid}" download
                        class="btn btn-sm btn-outline-secondary">📤 原始 Excel</a>
                    </div>
                </div>
            `;
            historyList.appendChild(li);
        });

        // 分頁資訊顯示
        document.getElementById('pageInfo').textContent = `第 ${currentPage} 頁 / 共 ${totalPages} 頁`;
        document.getElementById('prevPageBtn').disabled = (currentPage === 1);
        document.getElementById('nextPageBtn').disabled = (currentPage === totalPages || totalPages === 0);

    } catch (err) {
        alert("❌ 無法載入歷史紀錄，請稍後再試");
    }
}


document.getElementById('prevPageBtn').addEventListener('click', () => {
    if (currentPage > 1) loadHistoryPage(currentPage - 1);
});
document.getElementById('nextPageBtn').addEventListener('click', () => {
    if (currentPage < totalPages) loadHistoryPage(currentPage + 1);
});

window.addEventListener('DOMContentLoaded', () => {
    loadHistoryPage(1);

    // 深色模式初始化
    const isDark = localStorage.getItem('dark-mode') === 'true';
    if (isDark) {
        document.body.classList.add('dark-mode');
        document.getElementById('toggleDarkMode').innerHTML = '🌞 淺色模式';
    } else {
        document.body.classList.remove('dark-mode');
        document.getElementById('toggleDarkMode').innerHTML = '🌙 深色模式';
    }
    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn) {
        toggleBtn.textContent = document.body.classList.contains('sidebar-collapsed') ? '→' : '←';
    }
});

// 為深色模式切換按鈕添加點擊事件
document.getElementById('toggleDarkMode').addEventListener('click', () => {
    // 切換深色模式的樣式
    document.body.classList.toggle('dark-mode');
    // 獲取當前是否為深色模式
    const isDark = document.body.classList.contains('dark-mode');
    // 將深色模式狀態存入 localStorage
    localStorage.setItem('dark-mode', isDark);
    // 根據模式更新按鈕文字
    document.getElementById('toggleDarkMode').innerHTML = isDark ? '🌞 淺色模式' : '🌙 深色模式';
});

// 定義函數：切換側邊欄的顯示狀態
function toggleSidebar() {
    // 切換側邊欄的樣式
    document.body.classList.toggle('sidebar-collapsed');
    // 獲取側邊欄切換按鈕
    const toggleBtn = document.getElementById('sidebarToggle');
    // 根據側邊欄的狀態更新按鈕文字
    toggleBtn.textContent = document.body.classList.contains('sidebar-collapsed') ? '→' : '←';
}

// 定義函數：導航到指定的頁面
function navigateTo1(page) {
    if (page === 'upload') {
        window.location.href = '/';
    } else if (page === 'result') {
        window.location.href = '/result';
    } else if (page === 'history') {
        window.location.href = '/history';
    } else if (page === 'cluster') {
        window.location.href = '/generate_cluster';
    } else if (page === 'manual') {
        window.location.href = '/manual_input';
    } else if (page === 'gpt_prompt') {
        window.location.href = '/gpt_prompt';
    } else if (page === 'chat') {
        window.location.href = '/chat_ui';
    }
}


document.getElementById('clearHistoryBtn').addEventListener('click', async () => {
    if (confirm('你確定要清除所有歷史紀錄嗎？這個操作無法復原。')) {
        try {
            // 假設你有一個 Flask 路由 /clear-history (POST)
            const res = await fetch('/clear-history', { method: 'POST' });
            const result = await res.json();
            if (result.success) {
                document.getElementById('historyList').innerHTML = '';
                document.getElementById('no-history-msg').style.display = 'block';
                alert('✅ 歷史紀錄已清除！');
            } else {
                alert('❌ 清除失敗，請稍後再試。');
            }
        } catch {
            alert('❌ 清除歷史紀錄時發生錯誤！');
        }
    }
});
