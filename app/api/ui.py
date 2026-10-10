"""Interactive Web Interface for EnterpriseDocs AI."""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EnterpriseDocs AI — Company Knowledge Base</title>
  <style>
    :root {
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-border: #334155;
      --surface-hover: #293548;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --primary-glow: rgba(59, 130, 246, 0.25);
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.15);
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.15);
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.15);
      --radius: 10px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      background: var(--surface);
      border-bottom: 1px solid var(--surface-border);
      padding: 1rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 1.1rem;
      color: white;
    }
    .brand-title {
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .brand-tag {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .header-links {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      border: 1px solid transparent;
    }
    .badge-success { background: var(--success-bg); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
    .badge-warning { background: var(--warning-bg); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3); }
    .badge-primary { background: var(--primary-glow); color: #60a5fa; border-color: rgba(59, 130, 246, 0.3); }
    .btn-link {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.85rem;
      padding: 0.35rem 0.65rem;
      border-radius: 6px;
      border: 1px solid var(--surface-border);
      transition: all 0.15s ease;
    }
    .btn-link:hover { color: var(--text); border-color: var(--text-muted); }

    main {
      flex: 1;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 1.5rem;
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 1.5rem;
    }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius);
      padding: 1.25rem;
    }

    .query-form {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .input-row {
      display: flex;
      gap: 0.5rem;
    }
    .query-input {
      flex: 1;
      background: #0f172a;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 0.85rem 1rem;
      font-size: 1rem;
      color: var(--text);
      outline: none;
      transition: border 0.2s;
    }
    .query-input:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 2px var(--primary-glow);
    }
    .btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.75rem 1.25rem;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      transition: background 0.15s;
    }
    .btn:hover { background: var(--primary-hover); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #334155;
    }
    .btn-secondary:hover { background: #475569; }
    .btn-sm {
      padding: 0.35rem 0.65rem;
      font-size: 0.8rem;
    }
    .btn-danger {
      background: transparent;
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .btn-danger:hover { background: var(--danger-bg); }

    .query-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .mode-select, .topk-select {
      background: #0f172a;
      color: var(--text);
      border: 1px solid var(--surface-border);
      padding: 0.3rem 0.6rem;
      border-radius: 6px;
      font-size: 0.85rem;
      outline: none;
    }

    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }
    .suggestion-chip {
      background: #0f172a;
      border: 1px solid var(--surface-border);
      color: var(--text-muted);
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.15s;
    }
    .suggestion-chip:hover {
      border-color: var(--primary);
      color: var(--text);
    }

    .results-section {
      margin-top: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .result-box {
      background: #0f172a;
      border: 1px solid var(--surface-border);
      border-radius: var(--radius);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .result-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .answer-text {
      font-size: 1.05rem;
      color: #e2e8f0;
      line-height: 1.7;
    }
    .citation-mark {
      background: rgba(59, 130, 246, 0.2);
      color: #93c5fd;
      border: 1px solid rgba(59, 130, 246, 0.4);
      padding: 0.1rem 0.35rem;
      border-radius: 4px;
      font-weight: 700;
      font-size: 0.85rem;
      cursor: pointer;
      margin: 0 0.15rem;
    }
    .citation-mark:hover {
      background: rgba(59, 130, 246, 0.4);
    }

    .sources-title {
      font-size: 0.9rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-top: 0.5rem;
    }
    .sources-list {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }
    .source-card {
      background: #1e293b;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 0.75rem 1rem;
      transition: border 0.15s;
    }
    .source-card.highlight {
      border-color: var(--primary);
      box-shadow: 0 0 0 2px var(--primary-glow);
    }
    .source-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.8rem;
      margin-bottom: 0.35rem;
    }
    .source-meta {
      display: flex;
      gap: 0.5rem;
      font-weight: 600;
      color: #cbd5e1;
    }
    .source-snippet {
      font-size: 0.85rem;
      color: var(--text-muted);
      line-height: 1.5;
    }

    .doc-sidebar {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .doc-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }
    .doc-item {
      background: #0f172a;
      border: 1px solid var(--surface-border);
      border-radius: 6px;
      padding: 0.6rem 0.85rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.85rem;
    }
    .doc-info {
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .doc-name {
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 190px;
    }
    .doc-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .upload-zone {
      border: 2px dashed var(--surface-border);
      border-radius: 8px;
      padding: 1.25rem 1rem;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      background: #0f172a;
    }
    .upload-zone:hover {
      border-color: var(--primary);
      background: rgba(59, 130, 246, 0.05);
    }
    .upload-text {
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .upload-hint {
      font-size: 0.7rem;
      color: #64748b;
      margin-top: 0.25rem;
    }

    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: white;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    footer {
      border-top: 1px solid var(--surface-border);
      padding: 1rem 1.5rem;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">ED</div>
      <div>
        <div class="brand-title">EnterpriseDocs AI</div>
        <div class="brand-tag">RAG Knowledge Assistant with Citation Verification</div>
      </div>
    </div>
    <div class="header-links">
      <span id="health-badge" class="badge badge-primary">Checking...</span>
      <a href="/docs" target="_blank" class="btn-link">Swagger API</a>
    </div>
  </header>

  <main>
    <section>
      <div class="card">
        <form id="query-form" class="query-form">
          <div class="input-row">
            <input
              type="text"
              id="query-input"
              class="query-input"
              placeholder="Ask a question about company policies, leave, IT or procurement..."
              required
              autocomplete="off"
            />
            <button type="submit" id="submit-btn" class="btn">
              <span id="btn-text">Ask AI</span>
              <span id="btn-spinner" class="spinner" style="display: none;"></span>
            </button>
          </div>

          <div class="query-controls">
            <div style="display: flex; gap: 0.75rem; align-items: center;">
              <label>
                Mode:
                <select id="mode-select" class="mode-select">
                  <option value="ask">Ask AI (Grounded RAG)</option>
                  <option value="search">Search Only (Raw Retrieval)</option>
                </select>
              </label>
              <label>
                Top passages:
                <select id="topk-select" class="topk-select">
                  <option value="2">2</option>
                  <option value="4" selected>4</option>
                  <option value="6">6</option>
                </select>
              </label>
            </div>
            <span>Press Enter to query</span>
          </div>

          <div class="suggestions">
            <span class="suggestion-chip" data-q="How many days of annual leave do employees get?">Annual leave allowance</span>
            <span class="suggestion-chip" data-q="What is the probation period for new staff?">Probation period</span>
            <span class="suggestion-chip" data-q="What are the rules on gifts and hospitality?">Gifts policy</span>
            <span class="suggestion-chip" data-q="My work phone went missing, who do I tell?">Lost device procedure</span>
          </div>
        </form>
      </div>

      <div id="results-area" class="results-section" style="display: none;">
        <div class="result-box">
          <div class="result-header">
            <h3 id="result-title" style="font-size: 1.1rem; font-weight: 700;">Answer</h3>
            <span id="grounded-badge" class="badge badge-success">Grounded</span>
          </div>
          <div id="answer-container" class="answer-text"></div>
          
          <div id="sources-container" style="margin-top: 0.5rem;">
            <div class="sources-title">Verified Sources</div>
            <div id="sources-list" class="sources-list"></div>
          </div>
        </div>
      </div>
    </section>

    <aside class="doc-sidebar">
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <h3 style="font-size: 1rem; font-weight: 700;">Document Library</h3>
          <button id="reingest-btn" class="btn btn-secondary btn-sm" title="Re-scan documents folder">Sync</button>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;">
          Company policies indexed into the local vector store.
        </p>

        <div class="upload-zone" id="upload-zone">
          <input type="file" id="file-input" style="display: none;" accept=".pdf,.txt,.md" />
          <div class="upload-text"><strong>Click to upload</strong> or drag & drop</div>
          <div class="upload-hint">PDF, TXT, or MD (max 10 MB)</div>
        </div>

        <div id="doc-list" class="doc-list">
          <div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 1rem;">
            Loading documents...
          </div>
        </div>
      </div>
    </aside>
  </main>

  <footer>
    EnterpriseDocs AI &bull; Exact Cosine Vector Search &bull; Tested on Python 3.12 &bull; Fast, safe & citation-verified
  </footer>

  <script>
    const queryForm = document.getElementById("query-form");
    const queryInput = document.getElementById("query-input");
    const submitBtn = document.getElementById("submit-btn");
    const btnText = document.getElementById("btn-text");
    const btnSpinner = document.getElementById("btn-spinner");
    const modeSelect = document.getElementById("mode-select");
    const topkSelect = document.getElementById("topk-select");
    const resultsArea = document.getElementById("results-area");
    const resultTitle = document.getElementById("result-title");
    const groundedBadge = document.getElementById("grounded-badge");
    const answerContainer = document.getElementById("answer-container");
    const sourcesList = document.getElementById("sources-list");
    const docList = document.getElementById("doc-list");
    const healthBadge = document.getElementById("health-badge");
    const reingestBtn = document.getElementById("reingest-btn");
    const uploadZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("file-input");

    modeSelect.addEventListener("change", () => {
      btnText.textContent = modeSelect.value === "ask" ? "Ask AI" : "Search";
    });

    document.querySelectorAll(".suggestion-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        queryInput.value = chip.dataset.q;
        queryForm.requestSubmit();
      });
    });

    async function updateHealth() {
      try {
        const res = await fetch("/health");
        if (res.ok) {
          const data = await res.json();
          healthBadge.textContent = `${data.documents} docs (${data.chunks} chunks)`;
          healthBadge.className = "badge badge-success";
        }
      } catch (err) {
        healthBadge.textContent = "Offline";
        healthBadge.className = "badge badge-warning";
      }
    }

    async function loadDocuments() {
      try {
        const res = await fetch("/documents");
        if (res.ok) {
          const docs = await res.json();
          if (docs.length === 0) {
            docList.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-muted); text-align: center;">No documents indexed</div>';
            return;
          }
          docList.innerHTML = docs.map(d => `
            <div class="doc-item">
              <div class="doc-info">
                <span class="doc-name" title="${d.name}">${d.name}</span>
                <span class="doc-sub">${d.pages} page${d.pages > 1 ? 's' : ''} &bull; ${d.chunks} chunks</span>
              </div>
              <button class="btn btn-sm btn-danger" onclick="deleteDocument('${d.name}')" title="Delete document">&times;</button>
            </div>
          `).join("");
        }
      } catch (err) {
        docList.innerHTML = '<div style="font-size: 0.8rem; color: var(--danger); text-align: center;">Failed to load documents</div>';
      }
    }

    window.deleteDocument = async function(name) {
      if (!confirm(`Are you sure you want to delete ${name}?`)) return;
      try {
        const res = await fetch(`/documents/${encodeURIComponent(name)}`, { method: "DELETE" });
        if (res.ok) {
          loadDocuments();
          updateHealth();
        } else {
          const err = await res.json();
          alert("Could not delete document: " + (err.detail || "Server error"));
        }
      } catch (err) {
        alert("Delete failed: " + err.message);
      }
    };

    reingestBtn.addEventListener("click", async () => {
      reingestBtn.disabled = true;
      reingestBtn.textContent = "...";
      try {
        await fetch("/ingest", { method: "POST" });
        await loadDocuments();
        await updateHealth();
      } finally {
        reingestBtn.disabled = false;
        reingestBtn.textContent = "Sync";
      }
    });

    uploadZone.addEventListener("click", () => fileInput.click());
    uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.style.borderColor = "var(--primary)"; });
    uploadZone.addEventListener("dragleave", () => { uploadZone.style.borderColor = "var(--surface-border)"; });
    uploadZone.addEventListener("drop", e => {
      e.preventDefault();
      uploadZone.style.borderColor = "var(--surface-border)";
      if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) uploadFile(fileInput.files[0]);
    });

    async function uploadFile(file) {
      const formData = new FormData();
      formData.append("file", file);
      uploadZone.style.opacity = "0.5";
      try {
        const res = await fetch("/documents", { method: "POST", body: formData });
        if (!res.ok) {
          const data = await res.json();
          alert("Upload failed: " + (data.detail || res.statusText));
        } else {
          await loadDocuments();
          await updateHealth();
        }
      } catch (err) {
        alert("Upload error: " + err.message);
      } finally {
        uploadZone.style.opacity = "1";
        fileInput.value = "";
      }
    }

    function renderCitations(text) {
      return text.replace(/\\[(\\d+(?:\\s*,\\s*\\d+)*)\\]/g, (match, nums) => {
        return nums.split(/\\s*,\\s*/).map(n => 
          `<span class="citation-mark" onclick="highlightSource(${n})">[${n}]</span>`
        ).join("");
      });
    }

    window.highlightSource = function(id) {
      document.querySelectorAll(".source-card").forEach(el => el.classList.remove("highlight"));
      const card = document.getElementById(`source-card-${id}`);
      if (card) {
        card.classList.add("highlight");
        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    };

    queryForm.addEventListener("submit", async e => {
      e.preventDefault();
      const question = queryInput.value.trim();
      if (!question) return;

      const mode = modeSelect.value;
      const topK = parseInt(topkSelect.value, 10);

      submitBtn.disabled = true;
      btnSpinner.style.display = "inline-block";
      btnText.style.display = "none";
      resultsArea.style.display = "none";

      try {
        if (mode === "ask") {
          const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, top_k: topK })
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Query failed");
          }

          const data = await res.json();
          resultTitle.textContent = "Answer";
          groundedBadge.style.display = "inline-block";
          if (data.grounded) {
            groundedBadge.textContent = "Grounded";
            groundedBadge.className = "badge badge-success";
          } else {
            groundedBadge.textContent = "Ungrounded";
            groundedBadge.className = "badge badge-warning";
          }

          answerContainer.innerHTML = renderCitations(data.answer);
          renderSources(data.sources);
          resultsArea.style.display = "flex";
        } else {
          const res = await fetch("/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: question, top_k: topK })
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Search failed");
          }

          const data = await res.json();
          resultTitle.textContent = `Raw Retrieval (${data.results.length} passages)`;
          groundedBadge.style.display = "none";
          answerContainer.innerHTML = `<em style="color: var(--text-muted);">Threshold: ${data.min_score.toFixed(2)} &bull; Retrieved passages displayed below ranked by similarity.</em>`;
          renderSources(data.results);
          resultsArea.style.display = "flex";
        }
      } catch (err) {
        alert(err.message);
      } finally {
        submitBtn.disabled = false;
        btnSpinner.style.display = "none";
        btnText.style.display = "inline";
      }
    });

    function renderSources(sources) {
      if (!sources || sources.length === 0) {
        sourcesList.innerHTML = '<div style="font-size: 0.85rem; color: var(--text-muted);">No passages retrieved.</div>';
        return;
      }

      sourcesList.innerHTML = sources.map(s => `
        <div class="source-card" id="source-card-${s.id}">
          <div class="source-card-header">
            <div class="source-meta">
              <span style="color: #60a5fa;">[${s.id}]</span>
              <span>${s.document}</span>
              <span style="color: var(--text-muted);">&bull; Page ${s.page}</span>
              <span style="color: #a78bfa;">&bull; ${s.section}</span>
            </div>
            <span class="badge ${s.relevant !== false ? 'badge-primary' : 'badge-warning'}">
              Score: ${s.score.toFixed(4)}
            </span>
          </div>
          <div class="source-snippet">${s.snippet}</div>
        </div>
      `).join("");
    }

    updateHealth();
    loadDocuments();
  </script>
</body>
</html>
"""
