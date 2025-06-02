// ---- 頁面導覽（全站 sidebar 共用）----
function navigateTo1(page) {
  const paths = {
    upload: "/",
    result: "/result",
    history: "/history",
    cluster: "/generate_cluster",
    manual: "/manual_input",
    gpt_prompt: "/gpt_prompt"
  };
  window.location.href = paths[page] || "/";
}

function promptLabel(key) {
  switch (key) {
    case 'solution': return 'Solution（AI解決建議）';
    case 'ai_summary': return 'AI Summary（AI問題摘要）';
    default: return key;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("gptPromptForm");
  const taskInput = document.getElementById("promptTask");
  const promptInput = document.getElementById("promptText");
  const currentSettingDiv = document.getElementById("currentSetting");

  const mappingForm = document.getElementById("mappingForm");
  const selectSolution = document.getElementById("currentSolutionPrompt");
  const selectSummary = document.getElementById("currentSummaryPrompt");
  const solutionModelInput = document.getElementById("currentSolutionModel");
  const summaryModelInput = document.getElementById("currentSummaryModel");

  let promptDataCache = {};

  // 初始化暗色模式與側邊欄
  const toggleBtn = document.getElementById("toggleDarkMode");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const isDark = localStorage.getItem("dark-mode") === "true";
  document.body.classList.toggle("dark-mode", isDark);
  toggleBtn.innerHTML = isDark ? "🌞 淺色模式" : "🌙 深色模式";

  const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
  document.body.classList.toggle("sidebar-collapsed", isCollapsed);
  sidebarToggle.textContent = isCollapsed ? "→" : "←";

  toggleBtn.onclick = () => {
    const nowDark = document.body.classList.toggle("dark-mode");
    localStorage.setItem("dark-mode", nowDark);
    toggleBtn.innerHTML = nowDark ? "🌞 淺色模式" : "🌙 深色模式";
  };
  sidebarToggle.onclick = () => {
    const collapsed = document.body.classList.toggle("sidebar-collapsed");
    localStorage.setItem("sidebarCollapsed", collapsed);
    sidebarToggle.textContent = collapsed ? "→" : "←";
  };

// 在 loadPrompt 時呼叫 renderCurrentSetting
async function loadPrompt() {
  currentSettingDiv.innerHTML = `<span class="text-info">🔄 載入中...</span>`;
  try {
    const data = await fetch('/get-gpt-prompts').then(r => r.json());
    promptDataCache = data;
    await loadMappingArea();
    const mapping = await fetch('/get-gpt-prompt-map').then(r => r.json());
    renderCurrentSetting(data, mapping);
    renderAllPromptList(data, mapping);
  } catch (err) {
    currentSettingDiv.innerHTML = `<span class="text-danger">❌ 無法載入 GPT Prompt 設定</span>`;
    console.error('[loadPrompt]', err);
  }
}



  // 2️⃣ 新增 prompt（append 進陣列）
  form.onsubmit = async e => {
    e.preventDefault();
    const task = taskInput.value;
    const prompt = promptInput.value.trim();
    if (!prompt) {
      alert("請輸入 GPT Prompt 內容");
      promptInput.focus();
      return;
    }
    const saveBtn = form.querySelector('button[type="submit"]');
    saveBtn.disabled = true;
    saveBtn.innerHTML = "儲存中…";

    try {
      const res = await fetch('/save-gpt-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, prompt })
      }).then(r => r.json());
      if (res.success) {
        alert("儲存成功！");
        await loadPrompt();
        promptInput.value = ""; // 清空欄位
      } else {
        alert(res.message || "儲存失敗，請稍後再試！");
      }
    } catch (err) {
      alert("儲存失敗：" + err.message);
    } finally {
      saveBtn.disabled = false;
      saveBtn.innerHTML = "新增";
    }
  };
function renderCurrentSetting(data, mapping) {
  let html = '';
  let blockHtml = '';

  if (mapping && mapping.solution && mapping.solution.prompt) {
    blockHtml += `
      <div class="dashboard-block dashboard-block-solution">
        <div class="dash-icon bg-blue"><i class="fas fa-cogs"></i></div>
        <div class="dash-info">
          <div class="dash-title">Solution</div>
          <div class="dash-prompt-label">Prompt</div>
          <div class="dash-prompt-text">${mapping.solution.prompt}</div>
          <div class="dash-meta">
            <span class="dash-meta-label">GPT模型</span>
            <span class="dash-meta-value">${mapping.solution.model || '-'}</span>
          </div>
        </div>
      </div>
    `;
  }

  if (mapping && mapping.ai_summary && mapping.ai_summary.prompt) {
    blockHtml += `
      <div class="dashboard-block dashboard-block-summary">
        <div class="dash-icon bg-yellow"><i class="fas fa-lightbulb"></i></div>
        <div class="dash-info">
          <div class="dash-title">AI Summary</div>
          <div class="dash-prompt-label">Prompt</div>
          <div class="dash-prompt-text">${mapping.ai_summary.prompt}</div>
          <div class="dash-meta">
            <span class="dash-meta-label">GPT模型</span>
            <span class="dash-meta-value">${mapping.ai_summary.model || '-'}</span>
          </div>
        </div>
      </div>
    `;
  }

  if (!blockHtml) {
    html = `<div class="text-warning">目前尚未設定任何用途。</div>`;
  } else {
    html = `
      <div class="dashboard-flex-row" style="display:flex; gap:32px; align-items:stretch;">
        ${blockHtml}
      </div>
    `;
  }

  document.getElementById("currentSetting").innerHTML = html;
}





  // Mapping 區塊
  // 4️⃣ Mapping 區選擇時，取第 1 句 prompt 作為 mapping value
async function loadMappingArea() {
  let promptData = await fetch('/get-gpt-prompts').then(r => r.json());
  let mapping = await fetch('/get-gpt-prompt-map').then(r => r.json());

  // Solution 下拉：所有 solution prompts
// Solution 下拉：超過 600 字才顯示...，否則原文
let solOptions = (promptData.solution?.prompts || []).map((p, idx) =>
  `<option value="solution|${idx}" title="${p}">${
    p.length > 210 ? p.slice(0, 210) + "..." : p
  }</option>`
).join("");
selectSolution.innerHTML = solOptions;

let sumOptions = (promptData.ai_summary?.prompts || []).map((p, idx) =>
  `<option value="ai_summary|${idx}" title="${p}">${
    p.length > 210 ? p.slice(0, 210) + "..." : p
  }</option>`
).join("");
selectSummary.innerHTML = sumOptions;




  // mapping 裡記錄了目前選的用途和 index
  if (mapping.solution?.prompt) {
    const idx = promptData.solution?.prompts?.indexOf(mapping.solution.prompt);
    if (idx !== -1) selectSolution.value = `solution|${idx}`;
  }
  if (mapping.ai_summary?.prompt) {
    const idx = promptData.ai_summary?.prompts?.indexOf(mapping.ai_summary.prompt);
    if (idx !== -1) selectSummary.value = `ai_summary|${idx}`;
  }

  updateModelInputs(mapping); // 這個不用改
}


// ---- 自動顯示 mapping 區塊的「模型名稱」欄位 ----
function updateModelInputs(mapping = {}) {
  const solutionModel = mapping.solution?.model || "";
  const summaryModel = mapping.ai_summary?.model || "";

  // Solution 模型處理
  const solutionSelect = document.getElementById("currentSolutionModelSelect");
  const solutionCustom = document.getElementById("currentSolutionModelCustom");

  if (["mistral", "phi3:mini", "phi4-mini", "tinyllama"].includes(solutionModel)) {
    solutionSelect.value = solutionModel;
    solutionCustom.classList.add("d-none");
    solutionCustom.value = "";
  } else {
    solutionSelect.value = "custom";
    solutionCustom.classList.remove("d-none");
    solutionCustom.value = solutionModel;
  }

  // Summary 模型處理
  const summarySelect = document.getElementById("currentSummaryModelSelect");
  const summaryCustom = document.getElementById("currentSummaryModelCustom");

  if (["mistral", "phi3:mini", "phi4-mini", "tinyllama"].includes(summaryModel)) {
    summarySelect.value = summaryModel;
    summaryCustom.classList.add("d-none");
    summaryCustom.value = "";
  } else {
    summarySelect.value = "custom";
    summaryCustom.classList.remove("d-none");
    summaryCustom.value = summaryModel;
  }
}

// Summary 下拉選單切換時顯示輸入框
document.getElementById('currentSummaryModelSelect').addEventListener('change', (e) => {
  const customInput = document.getElementById('currentSummaryModelCustom');
  if (e.target.value === 'custom') {
    customInput.classList.remove('d-none');
  } else {
    customInput.classList.add('d-none');
    customInput.value = ""; // 清除內容
  }
});

// 抽出 Summary 模型值（送出 mapping 用）
function getSelectedSummaryModel() {
  const select = document.getElementById('currentSummaryModelSelect');
  const custom = document.getElementById('currentSummaryModelCustom');
  return select.value === 'custom' ? custom.value.trim() : select.value;
}

  selectSolution.onchange = updateModelInputs;
  selectSummary.onchange = updateModelInputs;





// 送出 mapping，記得選單 value 要拆解
mappingForm.onsubmit = async e => {
  e.preventDefault();

  // Solution
  const [solType, solIdx] = selectSolution.value.split('|');
  const solPrompt = (promptDataCache[solType]?.prompts || [])[Number(solIdx)] || "";
  const solutionModel = getSelectedSolutionModel();

  // Summary
  const [sumType, sumIdx] = selectSummary.value.split('|');
  const sumPrompt = (promptDataCache[sumType]?.prompts || [])[Number(sumIdx)] || "";
  const summaryModel = getSelectedSummaryModel();

  if (!solPrompt || !solutionModel || !sumPrompt || !summaryModel) {
    alert("請填寫所有欄位！");
    return;
  }

  const saveBtn = mappingForm.querySelector('button[type="submit"]');
  saveBtn.disabled = true;
  saveBtn.innerHTML = "儲存中…";

  try {
    await fetch('/save-gpt-prompt-map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        solution: solPrompt,
        ai_summary: sumPrompt,
        models: {
            solution: solutionModel,
            ai_summary: summaryModel
        }
      })
    });
    alert("用途 mapping 儲存成功！");
    await loadPrompt(); // 讓 currentSetting 也即時刷新
  } catch (err) {
    alert("用途 mapping 儲存失敗：" + err.message);
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = "💾 儲存目前用途對應";
  }
};


 function renderAllPromptList(promptData, mapping) {
  const allPromptListDiv = document.getElementById("allPromptList");
  if (!promptData || Object.keys(promptData).length === 0) {
    allPromptListDiv.innerHTML = `<div class="text-warning">目前尚無可用 Prompt。</div>`;
    return;
  }

  allPromptListDiv.innerHTML = Object.entries(promptData).map(([key, val]) => {
    const arr = val.prompts || [];
    return `
      <div class="mb-4">
        <div class="fw-bold">${promptLabel(key)}</div>
        <div><b>所有 Prompt：</b></div>
        <div class="mt-1 p-2 border rounded bg-light bg-opacity-25">
          ${arr.length
            ? arr.map((txt, i) => `
                <div class="d-flex align-items-center mb-2">
                  <span class="text-break flex-grow-1">${i + 1}. ${txt}</span>
                  <button class="btn btn-outline-secondary btn-sm ms-2 edit-prompt-btn" 
                    data-task="${key}" data-index="${i}">✏️ 編輯</button>
                  <button class="btn btn-outline-danger btn-sm ms-2 delete-prompt-btn" 
                    data-task="${key}" data-index="${i}">🗑️ 刪除</button>
                </div>
              `).join("")
            : "<span class='text-muted'>—</span>"
          }
        </div>
      </div>
    `;
  }).join("");

  // 註冊刪除事件
  document.querySelectorAll(".delete-prompt-btn").forEach(btn => {
    btn.onclick = async function() {
      const task = this.dataset.task;
      const index = parseInt(this.dataset.index, 10);
      const prompt = promptData[task].prompts[index];
      if (!confirm(`確定要刪除？\n\n${prompt}`)) return;

      const res = await fetch("/delete-gpt-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task, prompt })
      }).then(r => r.json());

      if (res.success) {
        alert("已刪除！");
        await loadPrompt();
      } else {
        alert("刪除失敗：" + (res.message || "未知錯誤"));
      }
    };
  });

  // ========== Modal 編輯功能 ==========
  let editTask = null;
  let editPrompt = null;
  let editIndex = null;

  document.querySelectorAll(".edit-prompt-btn").forEach(btn => {
    btn.onclick = function() {
      editTask = this.dataset.task;
      editIndex = parseInt(this.dataset.index, 10);
      editPrompt = promptData[editTask].prompts[editIndex];

      // 將內容填入 textarea
      document.getElementById("editPromptTextarea").value = editPrompt;

      // 打開 Bootstrap Modal
      const modal = new bootstrap.Modal(document.getElementById('editPromptModal'));
      modal.show();

      // 綁定 Modal「儲存」按鈕
      document.getElementById("saveEditPromptBtn").onclick = async function() {
        const newPrompt = document.getElementById("editPromptTextarea").value.trim();
        if (!newPrompt || newPrompt === editPrompt) {
          alert("請輸入不同的內容。");
          return;
        }

        // 1. 刪除舊的
        const delRes = await fetch("/delete-gpt-prompt", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task: editTask, prompt: editPrompt })
        }).then(r => r.json());
        // 2. 新增新的
        if (delRes.success) {
          const addRes = await fetch("/save-gpt-prompt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task: editTask, prompt: newPrompt })
          }).then(r => r.json());
          if (addRes.success) {
            // 關閉 Modal
            bootstrap.Modal.getInstance(document.getElementById('editPromptModal')).hide();
            alert("已更新！");
            await loadPrompt();
          } else {
            alert("更新失敗：" + (addRes.message || "未知錯誤"));
          }
        } else {
          alert("舊內容移除失敗：" + (delRes.message || "未知錯誤"));
        }
      };
    };
  });
}




  loadPrompt();

  // ----- GPT 模型選擇邏輯：下拉選「custom」會顯示自訂輸入欄 -----
const solutionModelSelect = document.getElementById("currentSolutionModelSelect");
const solutionModelCustom = document.getElementById("currentSolutionModelCustom");
const summaryModelSelect = document.getElementById("currentSummaryModelSelect");
const summaryModelCustom = document.getElementById("currentSummaryModelCustom");

function handleModelSelectChange(selectEl, customInputEl) {
  if (selectEl.value === "custom") {
    customInputEl.classList.remove("d-none");
    customInputEl.focus();
  } else {
    customInputEl.classList.add("d-none");
    customInputEl.value = "";
  }
}

solutionModelSelect.addEventListener("change", () => {
  handleModelSelectChange(solutionModelSelect, solutionModelCustom);
});
summaryModelSelect.addEventListener("change", () => {
  handleModelSelectChange(summaryModelSelect, summaryModelCustom);
});

// ---- 實際送出用：取得目前選擇的 GPT 模型名稱 ----
function getSelectedSolutionModel() {
  return solutionModelSelect.value === "custom"
    ? solutionModelCustom.value.trim()
    : solutionModelSelect.value;
}

function getSelectedSummaryModel() {
  return summaryModelSelect.value === "custom"
    ? summaryModelCustom.value.trim()
    : summaryModelSelect.value;
}

});


