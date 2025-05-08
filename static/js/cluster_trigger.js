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

  // ✅ 分群功能與 Toast 控制
  const button = document.getElementById("run-cluster-btn");
  const status = document.getElementById("cluster-status");
  const toast = document.getElementById("toast");
  const copyBtn = document.getElementById("copyResult");
  const closeBtn = document.querySelector(".close-toast");

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
