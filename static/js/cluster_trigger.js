document.addEventListener("DOMContentLoaded", () => {
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

  if (sidebarToggle) {
    sidebarToggle.textContent = document.body.classList.contains('sidebar-collapsed') ? '→' : '←';
  }


    const fileList = document.getElementById('clusteredFileList');
  if (!fileList) return;

  fetch('/clustered-files')
    .then(res => res.json())
    .then(data => {
      const files = data.files || [];
      if (files.length === 0) {
        fileList.innerHTML = '<li>📭 尚無分群檔案</li>';
      } else {
        files.forEach(f => {
          const li = document.createElement('li');
          const url = `/download-clustered?file=${encodeURIComponent(f)}`;
          li.innerHTML = `<a href="${url}" download>📎 ${f}</a>`;

          fileList.appendChild(li);
          // 加下載提示
            li.querySelector("a").addEventListener("click", (e) => {
            showDownloadToast(`🚀 開始下載：${f}`);
            });

        });
        fileList.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    })
    .catch(err => {
      fileList.innerHTML = '<li>❌ 載入失敗，請稍後再試。</li>';
      console.error('載入錯誤：', err);
    });







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

  if (!button || !status || !toast || !copyBtn) return;

  let lastMessage = "";

  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "⏳ 分群中，請稍候...";
    status.style.color = "#aaa";

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
      } else {
        status.textContent = "❌ 分群失敗或無回傳訊息。";
        status.style.color = "red";
      }
    } catch (err) {
      console.error(err);
      status.textContent = "❌ 無法與伺服器連線。";
      status.style.color = "red";
    } finally {
      button.disabled = false;
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
    if (!lastMessage) return;

    navigator.clipboard.writeText(lastMessage).then(() => {
      copyBtn.innerText = "✅ 已複製！";
      setTimeout(() => (copyBtn.innerText = "📋 複製結果"), 2000);
    });
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
    cluster: "/generate_cluster"
  };
  if (routes[page]) window.location.href = routes[page];
}
