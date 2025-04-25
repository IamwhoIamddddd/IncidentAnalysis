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
                // 🌈 切換模式後重新渲染雷達圖
    if (window.renderAllCharts) window.renderAllCharts();
        });
    }

    // ===== 動態載入分析結果卡片 =====
    const container = document.getElementById('resultCards');
    const riskLevelToClass = (level) => {
    switch(level) {
        case '高風險': return 'risk-critical';
        case '中風險': return 'risk-high';
        case '低風險': return 'risk-medium';
        case '忽略': default: return 'risk-low';
    }
};




    if (!container) return;

    try {
        document.getElementById('filterLoading').style.display = 'flex';
container.innerHTML = ''; // 清除原卡片

        const res = await fetch('/get-results');
        const data = await res.json();





const filterRange = document.getElementById('filterRange');
let rangeDays = localStorage.getItem('filter-days');

if (rangeDays === null) rangeDays = '7'; // 預設值

if (filterRange) {
    filterRange.value = rangeDays;
    filterRange.addEventListener('change', () => {
        const val = filterRange.value;
        if (val === 'all') {
            localStorage.setItem('filter-days', val);
        } else {
            localStorage.setItem('filter-days', val);
        }
        location.reload();
    });
}

let filterStartDate = null;
if (rangeDays !== 'all') {
    const now = new Date();
    if (rangeDays === '0') {
        // 只顯示今天（00:00 起）
        filterStartDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else {
        const days = parseInt(rangeDays);
        if (!isNaN(days)) {
            filterStartDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
        }
    }
}








        if (!data || data.length === 0) {
            container.innerHTML = '<p>⚠️ 尚無分析資料，請先回首頁上傳 Excel。</p>';
            return;
        }

data.forEach(row => {
    if (!row.analysisTime || isNaN(Date.parse(row.analysisTime))) return;
    const rowDate = new Date(row.analysisTime);
    if (filterStartDate && rowDate < filterStartDate) return;

    const cardRow = document.createElement('div');
    cardRow.className = 'card-row';

    const infoCard = document.createElement('div');
    infoCard.className = 'card card-info';
    infoCard.innerHTML = `
        <h3>🎯 Incident: ${row.id}</h3>
        <div class="card-grid">

            <div><strong>Config Item:</strong> <span>${row.configurationItem || '—'}</span></div>



            <div><strong>Severity<span class="score-max">(滿分 20)</span>:</strong> <span>${row.severityScore}</span>
                <div class="progress-bar" data-score="${row.severityScore}" data-type="severity"></div></div>



            <div><strong>Frequency<span class="score-max">(滿分 10)</span>:</strong> <span>${row.frequencyScore}</span>
                <div class="progress-bar" data-score="${row.frequencyScore}" data-type="frequency"></div></div>
                

            <div><strong>Impact<span class="score-max">(滿分 30)</span>:</strong> <span>${row.impactScore}</span>
                <div class="progress-bar" data-score="${row.impactScore}" data-type="impact"></div></div>

            <div><strong>Risk Level:</strong>
                <span class="badge ${riskLevelToClass(row.riskLevel)}">${row.riskLevel}</span></div>
            <div><strong>Solution:</strong> <span>${row.solution || '—'}</span></div>
            <div><strong>Location:</strong> <span>${row.location || '—'}</span></div>
            <div><strong>Analysis Date:</strong> <span>${row.analysisTime || '—'}</span></div>
        </div>
    `;

    const linker = document.createElement('div');
    linker.className = 'card-linker';
    linker.innerHTML = `<span>⇨</span>`;

    // 📌 把圖表區塊包在外層容器中
    const chartWrapper = document.createElement('div');
    chartWrapper.className = 'card-chart-wrapper';
    chartWrapper.innerHTML = `
        <h4>視覺化分析</h4>
    `;

    const chartCard = document.createElement('div');
    chartCard.className = 'card card-chart';
    chartCard.innerHTML = `
        <div class="card-visual-area"
             data-severity="${row.severityScore}" 
             data-frequency="${row.frequencyScore}" 
             data-impact="${row.impactScore}">
        </div>
    `;

    chartWrapper.appendChild(chartCard);       // 🔁 圖表卡片加到 wrapper 裡
    cardRow.appendChild(infoCard);
    cardRow.appendChild(linker);
    cardRow.appendChild(chartWrapper);         // 🟨 插入整個 wrapper

    container.appendChild(cardRow);
});



        if (typeof window.renderAllCharts === 'function') {
            window.renderAllCharts(); // ✅ 呼叫圖表渲染
        }        // ===== 動態載入進度條 =====


        const getBarStyle = (val, type) => {
            let percent = 0;
            if (type === 'severity') {
                percent = (val / 20) * 100;
            } else if (type === 'frequency') {
                percent = (val / 10) * 100;
            } else if (type === 'impact') {
                percent = (val / 30) * 100;
            }

            if (percent < 35) {
                return {
                    bg: 'linear-gradient(90deg, #6ee7b7, #3bceac)', // 綠
                    glow: '0 0 10px rgba(59, 206, 172, 0.5)'
                };
            } else if (percent < 70) {
                return {
                    bg: 'linear-gradient(90deg, #ffe57f, #ffca28)', // 黃
                    glow: '0 0 10px rgba(255, 202, 40, 0.5)'
                };
            } else {
                return {
                    bg: 'linear-gradient(90deg, #ff8a80, #e53935)', // 紅
                    glow: '0 0 10px rgba(229, 57, 53, 0.5)'
                };
            }
        };
            document.querySelectorAll('.progress-bar').forEach(bar => {
                const val = parseFloat(bar.dataset.score || 0);
                const type = bar.getAttribute('data-type');

                let percent = 0;
                if (type === 'severity') {
                    percent = Math.min((val / 20) * 100, 100);
                } else if (type === 'frequency') {
                    percent = Math.min((val / 10) * 100, 100);
                } else if (type === 'impact') {
                    percent = Math.min((val / 30) * 100, 100);
                }

                const fill = document.createElement('div');
                fill.classList.add('progress-fill');
                fill.setAttribute('data-score', val);
                fill.style.width = `${percent}%`;

                const { bg, glow } = getBarStyle(val, type); // 傳入 type
                fill.style.background = bg;
                fill.style.boxShadow = glow;

                bar.innerHTML = '';
                bar.appendChild(fill);
            });




    } catch (err) {
        console.error('🚨 無法取得結果：', err);
        container.innerHTML = '<p style="color:red;">❌ 無法載入分析結果。</p>';
    }

    document.getElementById('filterLoading').style.display = 'none';


const filterInput = document.getElementById('filterInput');
const clearBtn = document.getElementById('clearFilterBtn');
if (clearBtn) {
    clearBtn.addEventListener('click', () => {
        // 清除日期篩選器的值
        if (filterInput) filterInput.value = '';
        // 清除天數篩選器的值
        if (filterRange) filterRange.value = '7';
        // 清除 localStorage 中的天數篩選器值
        localStorage.removeItem('filter-days');
        location.reload();
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