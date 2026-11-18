(() => {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "eka_chats_v1";

  const els = {
    modeBadge: $("modeBadge"),
    disclaimer: $("disclaimer"),
    queryForm: $("queryForm"),
    question: $("question"),
    departmentFilter: $("departmentFilter"),
    categoryFilter: $("categoryFilter"),
    askBtn: $("askBtn"),
    threadRegion: $("threadRegion"),
    emptyState: $("emptyState"),
    thinking: $("thinking"),
    chatMain: $("chatMain"),
    chatList: $("chatList"),
    chatCount: $("chatCount"),
    chatEmpty: $("chatEmpty"),
    newChatBtn: $("newChatBtn"),
    docList: $("docList"),
    docCount: $("docCount"),
    docEmpty: $("docEmpty"),
    uploadForm: $("uploadForm"),
    uploadDisabled: $("uploadDisabled"),
    uploadStatus: $("uploadStatus"),
    uploadBtn: $("uploadBtn"),
    fileInput: $("fileInput"),
    dropZone: $("dropZone"),
    dropFileName: $("dropFileName"),
    uploadDepartment: $("uploadDepartment"),
    uploadCategory: $("uploadCategory"),
    examples: $("examples"),
    rail: $("rail"),
    railToggle: $("railToggle"),
    railBackdrop: $("railBackdrop"),
  };

  let config = {
    mode: "local_demo",
    uploads_enabled: true,
    deletions_enabled: true,
  };

  /** @type {{id:string,title:string,createdAt:number,updatedAt:number,question:string,response:object|null}[]} */
  let chats = [];
  /** @type {string|null} */
  let activeChatId = null;

  async function api(path, options = {}) {
    const res = await fetch(path, options);
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      const message = typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
          : res.statusText;
      throw new Error(message || "Request failed");
    }
    return data;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function uid() {
    return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function titleFromQuestion(question) {
    const cleaned = question.replace(/\s+/g, " ").trim();
    return cleaned.length > 42 ? `${cleaned.slice(0, 42)}…` : cleaned;
  }

  function loadChats() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      chats = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(chats)) chats = [];
    } catch {
      chats = [];
    }
  }

  function saveChats() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  }

  function getActiveChat() {
    return chats.find((c) => c.id === activeChatId) || null;
  }

  function setModeUI() {
    const demo = config.mode === "local_demo";
    els.modeBadge.dataset.mode = config.mode;
    els.modeBadge.textContent = demo
      ? "Local demo — evidence only"
      : `OpenAI · ${config.chat_model || "chat"}`;
    if (config.disclaimer) els.disclaimer.textContent = config.disclaimer;

    const uploads = Boolean(config.uploads_enabled);
    els.uploadForm.hidden = !uploads;
    els.uploadDisabled.hidden = uploads;
  }

  function statusChip(status) {
    const cls = ["ready", "processing", "failed", "pending"].includes(status)
      ? status
      : "pending";
    return `<span class="status-chip ${cls}">${status}</span>`;
  }

  function renderDocuments(payload) {
    const docs = payload.documents || [];
    els.docCount.textContent = String(payload.total);
    els.docEmpty.hidden = docs.length > 0;
    els.docList.innerHTML = docs.map((doc) => {
      const err = doc.error_message
        ? `<div class="hint" style="margin-top:0.35rem">${escapeHtml(doc.error_message)}</div>`
        : "";
      const del = config.deletions_enabled
        ? `<div class="doc-actions"><button type="button" data-del="${doc.id}">Delete</button></div>`
        : "";
      return `
        <li class="doc-item">
          <strong>${escapeHtml(doc.original_filename)}</strong>
          <div class="doc-meta">
            ${statusChip(doc.status)}
            <span>${escapeHtml(doc.department)} · ${escapeHtml(doc.category)}</span>
            <span>${doc.chunk_count} chunks</span>
            ${doc.is_sample ? "<span>sample</span>" : ""}
          </div>
          ${err}
          ${del}
        </li>`;
    }).join("");
  }

  function renderChatList() {
    const ordered = [...chats].sort((a, b) => b.updatedAt - a.updatedAt);
    els.chatCount.textContent = String(ordered.length);
    els.chatEmpty.hidden = ordered.length > 0;
    els.chatList.innerHTML = ordered.map((chat) => `
      <li>
        <button type="button" class="chat-item ${chat.id === activeChatId ? "active" : ""}" data-chat="${chat.id}">
          <span class="chat-item-title">${escapeHtml(chat.title)}</span>
          <span class="chat-item-del" data-del-chat="${chat.id}" title="Delete chat">×</span>
        </button>
      </li>
    `).join("");
  }

  function sourcesHtml(sources) {
    if (!sources?.length) return "";
    return `
      <div class="sources-wrap">
        <p class="section-label">Sources</p>
        <p class="sources-hint">Open a source to read the exact passage used for grounding.</p>
        <div class="sources">
          ${sources.map((src, idx) => `
            <details class="source" ${idx === 0 ? "open" : ""}>
              <summary>
                <span><span class="cite">[${escapeHtml(src.citation_marker)}]</span>${escapeHtml(src.filename)}</span>
                <span class="meta">${escapeHtml(src.department)} · sim ${src.similarity}</span>
              </summary>
              <div class="body">${escapeHtml(src.content)}</div>
            </details>
          `).join("")}
        </div>
      </div>`;
  }

  function renderActiveChat() {
    const chat = getActiveChat();
    els.thinking.hidden = true;

    if (!chat || !chat.response) {
      els.threadRegion.hidden = true;
      els.threadRegion.innerHTML = "";
      els.emptyState.hidden = false;
      renderChatList();
      return;
    }

    const data = chat.response;
    const label = data.abstained
      ? "Result"
      : data.retrieval_mode === "local_demo"
        ? "Evidence summary"
        : "Answer";

    els.emptyState.hidden = true;
    els.threadRegion.hidden = false;
    els.threadRegion.innerHTML = `
      <div class="turn">
        <div class="bubble user">${escapeHtml(chat.question)}</div>
        <div class="bubble assistant">
          <div class="assistant-head">
            <span class="pulse-dot" aria-hidden="true"></span>
            <span class="meta-line">mode · ${escapeHtml(data.retrieval_mode || "")}</span>
            <span class="meta-line">${
              data.citations_used?.length
                ? `citations · ${escapeHtml(data.citations_used.join(", "))}`
                : "citations · none"
            }</span>
          </div>
          ${data.abstained ? `
            <div class="abstain">
              Insufficient evidence for a grounded answer with the current filters.
            </div>` : ""}
          <p class="section-label">${escapeHtml(label)}</p>
          <article class="answer-body">${escapeHtml(data.answer || "")}</article>
          ${sourcesHtml(data.sources)}
        </div>
      </div>
    `;

    renderChatList();
    els.chatMain.scrollTo({ top: 0, behavior: "smooth" });
  }

  function startNewChat(options = {}) {
    const { focusComposer = true } = options;
    activeChatId = null;
    els.question.value = "";
    autosize();
    els.thinking.hidden = true;
    els.threadRegion.hidden = true;
    els.threadRegion.innerHTML = "";
    els.emptyState.hidden = false;
    renderChatList();
    if (focusComposer) els.question.focus();
  }

  function openChat(chatId) {
    activeChatId = chatId;
    els.thinking.hidden = true;
    renderActiveChat();
    if (window.innerWidth <= 980) setRail(false);
  }

  function deleteChat(chatId) {
    chats = chats.filter((c) => c.id !== chatId);
    saveChats();
    if (activeChatId === chatId) startNewChat({ focusComposer: false });
    else renderChatList();
  }

  function autosize() {
    const el = els.question;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function setRail(open) {
    els.rail.classList.toggle("open", open);
    els.railBackdrop.hidden = !open;
    els.railBackdrop.classList.toggle("show", open);
  }

  async function loadConfig() {
    config = await api("/api/config");
    setModeUI();
  }

  async function loadDocuments() {
    const data = await api("/api/documents");
    renderDocuments(data);
  }

  els.examples.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-q]");
    if (!btn) return;
    // Examples always start a fresh chat context.
    startNewChat({ focusComposer: false });
    els.question.value = btn.dataset.q;
    autosize();
    els.question.focus();
  });

  els.question.addEventListener("input", autosize);
  els.question.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.queryForm.requestSubmit();
    }
  });

  els.newChatBtn.addEventListener("click", () => startNewChat());

  els.chatList.addEventListener("click", (event) => {
    const del = event.target.closest("[data-del-chat]");
    if (del) {
      event.preventDefault();
      event.stopPropagation();
      const id = del.getAttribute("data-del-chat");
      if (id && confirm("Delete this chat?")) deleteChat(id);
      return;
    }
    const item = event.target.closest("[data-chat]");
    if (!item) return;
    openChat(item.getAttribute("data-chat"));
  });

  els.queryForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = els.question.value.trim();
    if (!question) return;

    // Each question gets its own chat so previous answers never mix in.
    const chat = {
      id: uid(),
      title: titleFromQuestion(question),
      createdAt: Date.now(),
      updatedAt: Date.now(),
      question,
      response: null,
    };
    chats.unshift(chat);
    activeChatId = chat.id;
    saveChats();
    renderChatList();

    els.askBtn.disabled = true;
    els.emptyState.hidden = true;
    els.threadRegion.hidden = true;
    els.threadRegion.innerHTML = "";
    els.thinking.hidden = false;
    els.question.value = "";
    autosize();

    try {
      const body = {
        question,
        department: els.departmentFilter.value || null,
        category: els.categoryFilter.value || null,
      };
      const data = await api("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      // Ignore stale responses if the user switched chats mid-request.
      if (activeChatId !== chat.id) return;
      chat.response = data;
      chat.updatedAt = Date.now();
      saveChats();
      renderActiveChat();
    } catch (err) {
      if (activeChatId !== chat.id) return;
      chat.response = {
        answer: `Error: ${err.message}`,
        abstained: false,
        retrieval_mode: config.mode || "local_demo",
        citations_used: [],
        sources: [],
      };
      chat.updatedAt = Date.now();
      saveChats();
      renderActiveChat();
    } finally {
      els.askBtn.disabled = false;
      els.thinking.hidden = true;
    }
  });

  els.fileInput.addEventListener("change", () => {
    const file = els.fileInput.files?.[0];
    els.dropFileName.textContent = file ? file.name : "No file selected";
  });

  ["dragenter", "dragover"].forEach((evt) => {
    els.dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      els.dropZone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((evt) => {
    els.dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      els.dropZone.classList.remove("dragover");
    });
  });
  els.dropZone.addEventListener("drop", (e) => {
    const file = e.dataTransfer?.files?.[0];
    if (!file) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    els.fileInput.files = dt.files;
    els.dropFileName.textContent = file.name;
  });

  els.uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = els.fileInput.files?.[0];
    if (!file) return;
    els.uploadBtn.disabled = true;
    els.uploadStatus.textContent = "Uploading and indexing…";
    els.uploadStatus.className = "status";
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("department", els.uploadDepartment.value || "General");
      form.append("category", els.uploadCategory.value || "Policy");
      const doc = await api("/api/documents", { method: "POST", body: form });
      if (doc.status === "failed") {
        els.uploadStatus.textContent = doc.error_message || "Indexing failed.";
        els.uploadStatus.className = "status error";
      } else {
        els.uploadStatus.textContent = `Indexed ${doc.original_filename} (${doc.chunk_count} chunks).`;
        els.uploadStatus.className = "status ok";
        els.fileInput.value = "";
        els.dropFileName.textContent = "No file selected";
      }
      await loadDocuments();
    } catch (err) {
      els.uploadStatus.textContent = err.message;
      els.uploadStatus.className = "status error";
    } finally {
      els.uploadBtn.disabled = false;
    }
  });

  els.docList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-del]");
    if (!btn) return;
    const id = btn.dataset.del;
    if (!confirm("Delete this document and its chunks?")) return;
    try {
      await api(`/api/documents/${id}`, { method: "DELETE" });
      await loadDocuments();
    } catch (err) {
      alert(err.message);
    }
  });

  els.railToggle.addEventListener("click", () => {
    setRail(!els.rail.classList.contains("open"));
  });
  els.railBackdrop.addEventListener("click", () => setRail(false));

  loadChats();
  startNewChat({ focusComposer: false });

  (async () => {
    try {
      await loadConfig();
      await loadDocuments();
    } catch (err) {
      els.docEmpty.hidden = false;
      els.docEmpty.textContent = `Could not load app state: ${err.message}`;
    }
  })();
})();
