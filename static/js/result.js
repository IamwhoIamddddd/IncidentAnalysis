// 初始化深色模式狀態
window.addEventListener('DOMContentLoaded', () => {
    // 從 localStorage 取得深色模式的狀態
    const isDark = localStorage.getItem('dark-mode');
    // 獲取切換深色模式的按鈕元素
    const toggleBtn = document.getElementById('toggleDarkMode');
    // 獲取側邊欄切換按鈕元素
    const sidebarToggle = document.getElementById('sidebarToggle');

    // 如果深色模式狀態為 null 或 'true'，啟用深色模式
    if (isDark === null || isDark === 'true') {
        document.body.classList.add('dark-mode'); // 添加深色模式的樣式
        if (toggleBtn) toggleBtn.innerHTML = '🌞 淺色模式'; // 更新按鈕文字
    } else {
        // 否則，移除深色模式
        document.body.classList.remove('dark-mode'); // 移除深色模式的樣式
        if (toggleBtn) toggleBtn.innerHTML = '🌙 深色模式'; // 更新按鈕文字
    }

    // 如果側邊欄切換按鈕存在，根據側邊欄狀態更新按鈕文字
    if (sidebarToggle) {
        sidebarToggle.textContent = document.body.classList.contains('sidebar-collapsed') ? '→' : '←';
    }
});

// 切換深色模式按鈕行為
document.addEventListener('DOMContentLoaded', () => {
    // 獲取切換深色模式的按鈕元素
    const toggleBtn = document.getElementById('toggleDarkMode');
    if (toggleBtn) {
        // 為按鈕添加點擊事件監聽器
        toggleBtn.addEventListener('click', () => {
            // 切換深色模式的樣式
            document.body.classList.toggle('dark-mode');
            // 獲取當前是否為深色模式
            const isDark = document.body.classList.contains('dark-mode');
            // 根據模式更新按鈕文字
            toggleBtn.innerHTML = isDark ? '🌞 淺色模式' : '🌙 深色模式';
            // 將深色模式狀態存入 localStorage
            localStorage.setItem('dark-mode', isDark);
        });
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