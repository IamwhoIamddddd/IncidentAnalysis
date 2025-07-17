let summaryOffset = 0;
const summaryLimit = 20;
let totalSummaryFiles = 0;
let isLoadingSummary = false;

let clusteredOffset = 0;
const clusteredLimit = 20;
let totalClusteredFiles = 0;
let isLoadingClustered = false;


// ----- 2. 分批載入 summaries，累積 append -----
async function loadSummaryFilesBatch() {
  if (isLoadingSummary) return;
  isLoadingSummary = true;

  const summaryList = document.getElementById('summaryFileList');
  const summaryListLoading = document.getElementById('summaryListLoading');
  const loadMoreBtn = document.getElementById('loadMoreSummaryBtn');
  if (!summaryList || !summaryListLoading || !loadMoreBtn) return;

  summaryListLoading.style.display = '';
  loadMoreBtn.style.display = 'none';

try {
    const res = await fetch(`/summary-files?offset=${summaryOffset}&limit=${summaryLimit}`);
    const data = await res.json();
    const files = data.files || [];
    totalSummaryFiles = data.total || 0;

    summaryListLoading.style.display = 'none';

    if (files.length === 0 && summaryOffset === 0) {
      summaryList.innerHTML = '<li>📭 尚無摘要檔案</li>';
      return;
    }

    // 「累積 append」新資料
    files.forEach(f => {
      const li = document.createElement('li');
      const url = `/download-summary?file=${encodeURIComponent(f.name)}`;
      const icon = '📝';

      li.innerHTML = `
        <a href="${url}" download>${icon} ${f.name}</a>
        <span style="color:gray;">（${f.rows} 筆）</span>
      `;
      summaryList.appendChild(li);
      

      li.querySelector("a").addEventListener("click", () => {
        showDownloadToast(`🚀 開始下載：${f.name}`);
      });
    });

    summaryOffset += files.length;

    // 有剩就顯示「載入更多」
    if (summaryOffset < totalSummaryFiles) {
      loadMoreBtn.style.display = '';
    } else {
      loadMoreBtn.style.display = 'none';
    }

  } catch (err) {
    summaryListLoading.style.display = 'none';
    summaryList.innerHTML = '<li>❌ 載入失敗，請稍後再試。</li>';
    console.error('載入錯誤：', err);
  }
  isLoadingSummary = false;
}





async function loadClusteredFilesBatch() {
  if (isLoadingClustered) return;
  isLoadingClustered = true;

  const fileList = document.getElementById('clusteredFileList');
  const fileListLoading = document.getElementById('fileListLoading');
  const loadMoreBtn = document.getElementById('loadMoreClusteredBtn');
  const loadMoreSpinner = document.getElementById('loadMoreClusteredSpinner');
  const loadMoreBtnText = loadMoreBtn.querySelector('.btn-text');
  if (!fileList || !fileListLoading || !loadMoreBtn || !loadMoreSpinner || !loadMoreBtnText) return;

  fileListLoading.style.display = '';
  loadMoreBtn.disabled = true;
  loadMoreSpinner.style.display = '';
  loadMoreBtnText.textContent = '載入中...';

  try {
    const res = await fetch(`/clustered-files?offset=${clusteredOffset}&limit=${clusteredLimit}`);
    const data = await res.json();
    const files = data.files || [];
    totalClusteredFiles = data.total || 0;

    fileListLoading.style.display = 'none';

    if (files.length === 0 && clusteredOffset === 0) {
      fileList.innerHTML = '<li>📭 尚無分群檔案</li>';
      loadMoreBtn.style.display = 'none';
      return;
    }

    files.forEach(f => {
      const li = document.createElement('li');
      const detailsUrl = `/download-clustered?file=${encodeURIComponent(f.name)}`;
      const icon = '📎';

      const summaryName = f.name.replace(/^Cluster_/, "Summary_");
      const summaryUrl = `/download-summary?file=${encodeURIComponent(summaryName)}`;
      const summaryIcon = '📝';

      li.innerHTML = `
        <a href="${detailsUrl}" download>${icon} ${f.name}</a>
        <span style="color:gray;">（${f.rows} 筆）</span>
        <a href="${summaryUrl}" class="btn btn-sm btn-outline-success ms-1" style="margin-left:10px;" target="_blank">${summaryIcon} Summary</a>
      `;
      fileList.appendChild(li);

      li.querySelector("a").addEventListener("click", () => {
        showDownloadToast(`🚀 開始下載：${f.name}`);
      });
    });

    clusteredOffset += files.length;

    if (clusteredOffset >= totalClusteredFiles) {
      loadMoreBtn.disabled = true;
      loadMoreBtn.style.display = '';
      loadMoreSpinner.style.display = 'none';
      loadMoreBtnText.textContent = '已全部載完';
    } else {
      loadMoreBtn.disabled = false;
      loadMoreBtn.style.display = '';
      loadMoreSpinner.style.display = 'none';
      loadMoreBtnText.textContent = '載入更多';
    }

  } catch (err) {
    fileListLoading.style.display = 'none';
    fileList.innerHTML = '<li>❌ 載入失敗，請稍後再試。</li>';
    loadMoreBtn.disabled = false;
    loadMoreBtnText.textContent = '載入更多';
    loadMoreSpinner.style.display = 'none';
    console.error('載入錯誤：', err);
  }
  isLoadingClustered = false;
}



// ----- 1. 初始化頁面時載入第一批 summaries -----
document.addEventListener("DOMContentLoaded", () => {
console.log("Button:", document.getElementById("run-cluster-btn"));
console.log("Status:", document.getElementById("cluster-status"));
console.log("Toast:", document.getElementById("toast"));
console.log("CopyBtn:", document.getElementById("copyResult"));


summaryOffset = 0;
document.getElementById('summaryFileList').innerHTML = '';
loadSummaryFilesBatch();
document.getElementById('loadMoreSummaryBtn').addEventListener('click', loadSummaryFilesBatch);



  clusteredOffset = 0;
  document.getElementById('clusteredFileList').innerHTML = '';
  loadClusteredFilesBatch();
  document.getElementById('loadMoreClusteredBtn').addEventListener('click', loadClusteredFilesBatch);




  // ✅ 初始化深色模式
  const isDark = localStorage.getItem("dark-mode") === "true";
  const toggleBtn = document.getElementById("toggleDarkMode");
  const sidebarToggle = document.getElementById("sidebarToggle");

  if (isDark) {
    document.body.classList.add("dark-mode");
    if (toggleBtn) toggleBtn.innerHTML = "🌞 淺色模式";
  } else {
    document.body.classList.remove("dark-mode");
    if (toggleBtn) toggleBtn.innerHTML = "🌙 深色模式";
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      document.body.classList.toggle("dark-mode");
      const isNowDark = document.body.classList.contains("dark-mode");
      toggleBtn.innerHTML = isNowDark ? "🌞 淺色模式" : "🌙 深色模式";
      localStorage.setItem("dark-mode", isNowDark);
    });
  }

    // ✅ 初始化 Sidebar 折疊狀態
    const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
    document.body.classList.toggle("sidebar-collapsed", isCollapsed);
    if (sidebarToggle) sidebarToggle.textContent = isCollapsed ? "→" : "←";

    if (sidebarToggle) {
      sidebarToggle.addEventListener("click", () => {
        const collapsed = document.body.classList.toggle("sidebar-collapsed");
        localStorage.setItem("sidebarCollapsed", collapsed);
        sidebarToggle.textContent = collapsed ? "→" : "←";
      });
    }






  // ✅ 分群功能與 Toast 控制
  const button = document.getElementById("run-cluster-btn");
  const status = document.getElementById("cluster-status");
  const toast = document.getElementById("toast");
  const copyBtn = document.getElementById("copyResult");
  const closeBtn = document.querySelector(".close-toast");

  // 檢查 Unclustered 資料夾是否有檔案
  fetch("/check-unclustered")
    .then(res => res.json())
    .then(data => {
      if (!data.exists) {
        button.disabled = true;
        status.textContent = "📂 沒有未分群的 Excel 檔案";
        status.style.color = "#f66"; // 紅色提示
      } else {
        button.disabled = false;
        status.textContent = "✅ 可以開始分群分析";
        status.style.color = "#4caf50"; // 綠色提示
      }
    })
    .catch(err => {
      button.disabled = true;
      status.textContent = "⚠️ 無法檢查未分群資料夾";
      status.style.color = "#f66";
      console.error("❌ 檢查錯誤：", err);
    });

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      toast.style.display = "none";
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && toast?.style.display === "block") {
      toast.style.display = "none";
    }
  });
  console.log("check:", button, status, toast, copyBtn);

  if (!button || !status || !toast || !copyBtn) return;

  let lastMessage = "";

  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "⏳ 分群中，請稍候...";
    status.style.color = "#aaa";
    copyBtn.disabled = true;    // 👈 按下分群時就讓複製結果再度不能按

    try {
      const response = await fetch("/cluster-excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const result = await response.json();

      if (result.message) {
        lastMessage = result.message;
        status.textContent = "✅ " + result.message;
        status.style.color = "#4CAF50";

        showToast(result.message);
        scrollToElement(status);
        copyBtn.disabled = false;
        button.disabled = true;  // 🟢 這裡直接 disable，永遠不能再按

      } else {
        status.textContent = "❌ 分群失敗或無回傳訊息。";
        status.style.color = "red";
        copyBtn.disabled = true;   // 👈 失敗時還是不能按
        button.disabled = false; // 失敗還能再按
      }
    } catch (err) {
      console.error(err);
      status.textContent = "❌ 無法與伺服器連線。";
      status.style.color = "red";
      copyBtn.disabled = true;     // 👈 失敗時還是不能按
      button.disabled = false; // 失敗還能再按
    } finally {
    }
  });









  
  function showToast(msg) {
    toast.style.display = "block";
    toast.querySelector("span")?.remove();

    const msgSpan = document.createElement("span");
    msgSpan.textContent = msg;
    toast.insertBefore(msgSpan, copyBtn);
  }

  copyBtn.addEventListener("click", () => {
    const fileList = document.getElementById("clusteredFileList");
    if (!fileList) return;
    let filesText = "";
    fileList.querySelectorAll("li").forEach(li => {
      filesText += li.textContent.trim() + "\n";
    });
    if (filesText.trim()) {
      navigator.clipboard.writeText(filesText).then(() => {
        copyBtn.innerText = "✅ 已複製！";
        setTimeout(() => (copyBtn.innerText = "📋 複製結果"), 2000);
      });
    }
  });













  function scrollToElement(el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function showDownloadToast(message) {
    const toast = document.getElementById("download-toast");
    toast.textContent = message;
    toast.style.display = "block";
    toast.style.position = "fixed";
    toast.style.bottom = "30px";
    toast.style.right = "30px";
    toast.style.padding = "12px 20px";
    toast.style.background = "rgba(33, 150, 243, 0.9)";
    toast.style.color = "#fff";
    toast.style.borderRadius = "8px";
    toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.2)";
    toast.style.fontWeight = "600";
    toast.style.zIndex = "9999";
    toast.style.transition = "opacity 0.3s";

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => {
        toast.style.display = "none";
        toast.style.opacity = "1";
        }, 300);
    }, 2000);
  }

});

// ✅ 導航功能
function navigateTo1(page) {
  const routes = {
    upload: "/",
    result: "/result",
    history: "/history",
    cluster: "/generate_cluster",
    manual: "/manual_input",
    gpt_prompt: "/gpt_prompt",
    chat: "/chat_ui"
  };
  if (routes[page]) window.location.href = routes[page];
}
