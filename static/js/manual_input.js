window.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("sentenceForm");
  const textInput = document.getElementById("sentenceText");
  const tagInput = document.getElementById("sentenceTag");
  const listContainer = document.getElementById("existingSentences");
  const saveEditBtn = document.getElementById('saveEditBtn');

  // 深色模式與側邊欄初始化
  const toggleBtn = document.getElementById("toggleDarkMode");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const isDark = localStorage.getItem("dark-mode") === "true";
  document.body.classList.toggle("dark-mode", isDark);
  if (toggleBtn) toggleBtn.innerHTML = isDark ? "🌞 淺色模式" : "🌙 深色模式";
  const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
  document.body.classList.toggle("sidebar-collapsed", isCollapsed);
  if (sidebarToggle) sidebarToggle.textContent = isCollapsed ? "→" : "←";
  if (toggleBtn) toggleBtn.onclick = () => {
    const nowDark = document.body.classList.toggle("dark-mode");
    localStorage.setItem("dark-mode", nowDark);
    toggleBtn.innerHTML = nowDark ? "🌞 淺色模式" : "🌙 深色模式";
    renderSentences(JSON.parse(localStorage.getItem("sentenceCache") || "[]"));
  };
  if (sidebarToggle) sidebarToggle.onclick = () => {
    const collapsed = document.body.classList.toggle("sidebar-collapsed");
    localStorage.setItem("sidebarCollapsed", collapsed);
    sidebarToggle.textContent = collapsed ? "→" : "←";
  };

    // 加在最後面
  const collapse = document.getElementById('collapseSentences');
  const btn = document.getElementById('toggleAccordionBtn');
  if (collapse && btn) {
    collapse.addEventListener('show.bs.collapse', function () {
      btn.innerText = '點擊關閉';
    });

    collapse.addEventListener('hide.bs.collapse', function () {
      btn.innerText = '點擊展開';
    });
}

  // 讀取語句資料
  listContainer.innerHTML = `<p class="text-info">🔄 正在載入語句資料...</p>`;
  fetch("/get-sentence-db")
    .then(res => res.json())
    .then(data => {
      localStorage.setItem("sentenceCache", JSON.stringify(data));
      renderSentences(data);
    })
    .catch(err => {
      listContainer.innerHTML = `<p class="text-danger fw-bold">❌ 載入語句失敗</p>`;
      console.error(err);
    });
form.onsubmit = async e => {
  e.preventDefault();

  // 前端自動規則轉換
  let sentence = textInput.value.trim();

  // 1. 去掉包裹的引號
  if ((sentence.startsWith("'") && sentence.endsWith("'")) ||
      (sentence.startsWith('"') && sentence.endsWith('"'))) {
    sentence = sentence.slice(1, -1);
  }

  // 2. 去掉句尾逗號
  sentence = sentence.replace(/^[,，\s]+|[,，\s]+$/g, "");

  // 3. 轉成半形
  sentence = sentence.replace(/’/g, "'").replace(/“|”/g, '"').replace(/，/g, ",");

  // 4. 偵測多句（逗號/分號分隔），自動拆多筆存（進階功能，可以選擇不自動拆，直接 alert）
  // 範例：自動存多筆
  let sentences = sentence.split(/[,;，；]\s*/).map(s => s.trim()).filter(s => s.length > 0);

  // 若超過一句，提示使用者
  if (sentences.length > 1) {
    if (!confirm("偵測到你輸入了多個語句，將自動分成多筆儲存：\n" + sentences.join("\n"))) return;
  }

  for (let s of sentences) {
    if (!s) continue;
    const newEntry = {
      text: s,
      tag: tagInput.value
    };
    const res = await fetch("/save-sentence-db", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newEntry)
    });
    if (res.ok) {
      // 可選擇只 reload 一次
      const updated = await res.json();
      localStorage.setItem("sentenceCache", JSON.stringify(updated));
      renderSentences(updated);
    } else {
      alert("❌ 儲存失敗");
    }
  }

  form.reset();
};


saveEditBtn.onclick = async () => {
  let editText = editNewText.value.trim();

  // 自動格式化
  if ((editText.startsWith("'") && editText.endsWith("'")) ||
      (editText.startsWith('"') && editText.endsWith('"'))) {
    editText = editText.slice(1, -1);
  }
  editText = editText.replace(/^[,，\s]+|[,，\s]+$/g, "");
  editText = editText.replace(/’/g, "'").replace(/“|”/g, '"').replace(/，/g, ",");

  // 不允許多句一起編輯
  if (editText.split(/[,;，；]\s*/).length > 1) {
    alert("請只編輯單一句語句，多句請分開新增！");
    return;
  }

  const payload = {
    tag: editTag.value,
    oldText: editOldText.value,
    newText: editText
  };
  const res = await fetch("/edit-sentence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    const updated = await res.json();
    localStorage.setItem("sentenceCache", JSON.stringify(updated));
    renderSentences(updated);
    bootstrap.Modal.getOrCreateInstance(document.getElementById('editModal')).hide();
  } else {
    alert("❌ 編輯失敗");
  }
};








  

  // 語句渲染（不顯示 prompt）
  function renderSentences(data) {
    const grouped = {};
    data.forEach(item => {
      if (!grouped[item.tag]) grouped[item.tag] = [];
      grouped[item.tag].push(item);
    });

    listContainer.innerHTML = Object.entries(grouped).map(([tag, items]) => {
      const rows = items.map(e => {
        const encodedText = encodeURIComponent(e.text);

        return `
          <li class="mb-2 d-flex justify-content-between align-items-start gap-3 sentence-item">
            <div class="sentence-text">
              <strong>${e.text}</strong>
            </div>
            <div>
              <button class="btn btn-sm btn-outline-secondary me-2 edit-btn"
                data-tag="${e.tag}"
                data-text="${encodedText}"
              >✏️ 編輯</button>
              <button class="btn btn-sm btn-outline-danger delete-btn"
                data-tag="${e.tag}"
                data-text="${encodedText}"
              >🗑️ 刪除</button>
            </div>
          </li>
        `;
      }).join("");

      return `
        <div class="card shadow fade-in mt-4">
          <div class="card-body sentence-card-body">
            <h5 class="card-title">${tagToText(tag)}</h5>
            <ul class="mb-0">${rows}</ul>
          </div>
        </div>
      `;
    }).join("");

    // 綁定編輯按鈕
    document.querySelectorAll('.edit-btn').forEach(btn => {
      btn.onclick = () => {
        document.getElementById('editTag').value = btn.dataset.tag;
        document.getElementById('editOldText').value = decodeURIComponent(btn.dataset.text);
        document.getElementById('editNewText').value = decodeURIComponent(btn.dataset.text);
        bootstrap.Modal.getOrCreateInstance(document.getElementById('editModal')).show();
      };
    });

    // 刪除按鈕
    document.querySelectorAll('.delete-btn').forEach(btn => {
      btn.onclick = async () => {
        const tag = btn.dataset.tag;
        const text = decodeURIComponent(btn.dataset.text);
        if (!confirm(`確定要刪除這句語句嗎？\n「${text}」`)) return;

        const res = await fetch("/delete-sentence", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tag, text })
        });
        if (res.ok) {
          const updated = await res.json();
          localStorage.setItem("sentenceCache", JSON.stringify(updated));
          renderSentences(updated);
        } else {
          alert("❌ 刪除失敗");
        }
      };
    });
  }

  // 標籤顯示
  function tagToText(tag) {
    const darkMode = localStorage.getItem("dark-mode") === "true";
    const style = darkMode ? "style=\"color:#ffd166;font-weight:600\"" : "style=\"color:#2c3e50\"";
    switch (tag) {
      case "high_risk": return `<span ${style}>⚠️ 高風險</span>`;
      case "escalate": return `<span ${style}>📈 升級處理</span>`;
      case "multi_user": return `<span ${style}>👥 多人影響</span>`;
      default: return `<span ${style}>📁 未分類</span>`;
    }
  }
});

// 頁面導覽
function navigateTo1(page) {
  const paths = {
    upload: "/",
    result: "/result",
    history: "/history",
    cluster: "/generate_cluster",
    manual: "/manual_input",
    gpt_prompt: "/gpt_prompt",
    chat: "/chat_ui"
  };
  window.location.href = paths[page] || "/";
}
