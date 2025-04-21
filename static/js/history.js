// 當 DOM 完全加載後執行
window.addEventListener('DOMContentLoaded', () => {
    // 獲取顯示歷史紀錄的列表元素
    const historyList = document.getElementById('historyList');
    // 從 localStorage 取得歷史紀錄資料，若無資料則設為空陣列
    const savedHistory = JSON.parse(localStorage.getItem('historyData') || '[]');

    // 清空原本的內容
    historyList.innerHTML = '';

    // 遍歷歷史紀錄資料，將每一項添加到列表中
    savedHistory.forEach(item => {
        // 創建一個新的列表項目
        const li = document.createElement('li');
        // 設定列表項目的 HTML，包含檔案名稱、時間和摘要
        li.innerHTML = `<strong>${item.file}</strong> - ${item.time}<br><span>${item.summary}</span>`;
        // 將列表項目添加到歷史紀錄列表中
        historyList.appendChild(li);
    });

    // 初始化深色模式
    const isDark = localStorage.getItem('dark-mode') === 'true'; // 從 localStorage 取得深色模式狀態
    if (isDark) {
        // 如果是深色模式，添加深色模式的樣式
        document.body.classList.add('dark-mode');
        // 更新深色模式按鈕的文字
        document.getElementById('toggleDarkMode').innerHTML = '🌞 淺色模式';
    } else {
        // 如果不是深色模式，移除深色模式的樣式
        document.body.classList.remove('dark-mode');
        // 更新深色模式按鈕的文字
        document.getElementById('toggleDarkMode').innerHTML = '🌙 深色模式';
    }

    // 獲取側邊欄切換按鈕
    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn) {
        // 根據側邊欄的狀態更新按鈕文字
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

// 為清除歷史紀錄按鈕添加點擊事件
document.getElementById('clearHistoryBtn').addEventListener('click', () => {
    // 確認是否清除歷史紀錄
    if (confirm('你確定要清除所有歷史紀錄嗎？這個操作無法復原。')) {
        // 從 localStorage 移除歷史紀錄資料
        localStorage.removeItem('historyData');
        localStorage.removeItem('historyHTML');
        // 清空歷史紀錄列表的內容
        historyList.innerHTML = '';
        // 顯示清除成功的提示訊息
        alert('✅ 歷史紀錄已清除！');
    }
});