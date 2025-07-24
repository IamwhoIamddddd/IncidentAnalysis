let summaryOffset = 0;
const summaryLimit = 20;
let totalSummaryFiles = 0;
let isLoadingSummary = false;

let clusteredOffset = 0;
const clusteredLimit = 20;
let totalClusteredFiles = 0;
let isLoadingClustered = false;

function showCustomBackdrop() {
  document.getElementById("customBackdrop").classList.add("active");
}
function hideCustomBackdrop() {
  document.getElementById("customBackdrop").classList.remove("active");
}


// 打開 Modal 時呼叫
function openProgressModal() {
  showCustomBackdrop();
  const modal = new bootstrap.Modal(document.getElementById('clusterProgressModal'), {backdrop: false});
  modal.show();
}


async function reloadSummaryAndClusteredLists() {
  // 1. 重新載入 Summary 區塊
  summaryOffset = 0;
  const summaryList = document.getElementById('summaryFileList');
  if (summaryList) summaryList.innerHTML = '';
  await loadSummaryFilesBatch();

  // 2. 重新載入 Clustered 區塊
  clusteredOffset = 0;
  const clusteredList = document.getElementById('clusteredFileList');
  if (clusteredList) clusteredList.innerHTML = '';
  await loadClusteredFilesBatch();
}


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


  // 這一行就直接加在這裡
  document.getElementById('clusterProgressModal').addEventListener('hidden.bs.modal', () => {
    hideCustomBackdrop();
  });

  console.log("Button:", document.getElementById("run-cluster-btn"));
  console.log("Status:", document.getElementById("cluster-status"));
  console.log("Toast:", document.getElementById("toast"));
  console.log("CopyBtn:", document.getElementById("copyResult"));


  summaryOffset = 0;
  document.getElementById('summaryFileList').innerHTML = '';
  loadSummaryFilesBatch();
  document.getElementById('loadMoreSummaryBtn').addEventListener('click', loadSummaryFilesBatch);


const openModalBtn = document.getElementById("openProgressModalBtn");
if (openModalBtn) {
  openModalBtn.addEventListener("click", () => {
    // ✅ 可選：重置進度條內容
    updateClusterModal(0, 1, "這是手動開啟的分群進度視窗！");
    openProgressModal(); // 這一行自帶 showCustomBackdrop()
    // ✅ 改成這樣就不會有灰色背景
    const modal = new bootstrap.Modal(document.getElementById("clusterProgressModal"), {
      backdrop: false
    });
    modal.show();
  });
}

    clusteredOffset = 0;
    document.getElementById('clusteredFileList').innerHTML = '';
    loadClusteredFilesBatch();
    document.getElementById('loadMoreClusteredBtn').addEventListener('click', loadClusteredFilesBatch);



    let clusterProgressInterval = null;

    function updateClusterModal(progress, total, status) {
      const percent = Math.round((progress / total) * 100);
      const progressBar = document.getElementById('clusterProgressBar');
      const progressText = document.getElementById('clusterProgressText');
      if (!progressBar || !progressText) return;
      progressBar.style.width = percent + '%';
      progressBar.textContent = percent + '%';
      progressText.textContent = status || `已完成 ${progress}/${total}`;
    }

  function startClusterProgressPolling(onFinish) {
    // 👉 一開始重置進度條
    updateClusterModal(0, 1, "初始化中...");

const modal = new bootstrap.Modal(document.getElementById('clusterProgressModal'), {
  backdrop: false
});
if (!document.getElementById('clusterProgressModal').classList.contains("show")) {
  modal.show();
}
    // 👉 clearInterval 保險
    if (clusterProgressInterval) clearInterval(clusterProgressInterval);

    // 👉 設定輪詢
    clusterProgressInterval = setInterval(async () => {
      try {
        const res = await fetch('/cluster-progress');
        const data = await res.json();

    // 這一行可以看到後端丟來的 progress、total、status
    console.log("進度資料", data);

        updateClusterModal(data.progress, data.total, data.status);

        if (data.progress >= data.total) {
          clearInterval(clusterProgressInterval);

          setTimeout(() => {
            modal.hide();
            showToast("🎉 分群完成！請查看結果");
            if (onFinish) onFinish();
          }, 1000);
        }

      } catch (err) {
        console.error("❌ 輪詢失敗：", err);
        clearInterval(clusterProgressInterval);
        updateClusterModal(0, 1, "❌ 無法取得進度，已中止。");
      }
    }, 1200);
}



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
      showCustomBackdrop();  // <-- 這一行

    button.disabled = true;
    status.textContent = "⏳ 分群中，請稍候...";
    status.style.color = "#aaa";
    copyBtn.disabled = true;    // 👈 按下分群時就讓複製結果再度不能按
      // 1️⃣ 分群前先重置進度條
    updateClusterModal(0, 1, "準備開始分群...");





          // 3️⃣ 開始輪詢進度
      let clusterFinished = false;
      let excelPosted = false;

      startClusterProgressPolling(async () => {
        clusterFinished = true;
        if (excelPosted) {
          bootstrap.Modal.getOrCreateInstance(document.getElementById('clusterProgressModal')).hide();
          await reloadSummaryAndClusteredLists();  // ⬅️ 你可以包裝起來
        }
      });

      try {
        const response = await fetch("/cluster-excel", {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });

        const result = await response.json();
        excelPosted = true;

        if (result.message) {
          lastMessage = result.message;
          status.textContent = "✅ " + result.message;
          status.style.color = "#4CAF50";

          showToast(result.message);
          scrollToElement(status);
          copyBtn.disabled = false;
          button.disabled = true;

          if (clusterFinished) {
            bootstrap.Modal.getOrCreateInstance(document.getElementById('clusterProgressModal')).hide();
            await reloadSummaryAndClusteredLists();  // ⬅️ 共用 reload
          }

        } else {
          status.textContent = "❌ 分群失敗或無回傳訊息。";
          status.style.color = "red";
          copyBtn.disabled = true;
          button.disabled = false;
        }
      } catch (err) {
        console.error(err);
        status.textContent = "❌ 無法與伺服器連線。";
        status.style.color = "red";
        copyBtn.disabled = true;
        button.disabled = false;
      }

    finally {
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
