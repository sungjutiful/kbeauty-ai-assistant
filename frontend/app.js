// 백엔드 주소: config.js(배포 시 Vercel 환경 변수로 생성)에서 읽고, 없으면 로컬 주소 사용
const API = (window.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const $ = (id) => document.getElementById(id);
let currentConvId = null;

// ---------- 공통 fetch ----------
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg).join(", ")
      : body.detail;
    throw new Error(detail || `요청 실패 (${res.status})`);
  }
  return body;
}

// ---------- 서버 깨우기 (Render 콜드스타트 대응) ----------
async function wakeServer() {
  const status = $("server-status");
  const banner = $("cold-banner");
  const timer = setTimeout(() => banner.classList.remove("hidden"), 3000);
  try {
    await api("/");
    status.textContent = "서버 연결됨";
    status.className = "status ok";
  } catch {
    status.textContent = "서버 연결 실패";
    status.className = "status err";
  } finally {
    clearTimeout(timer);
    banner.classList.add("hidden");
  }
}

// ---------- 요약 ----------
async function loadSummary() {
  try {
    const s = await api("/api/data/summary");
    const m = s.metrics || {};
    $("s-keyword").textContent = s.keyword ?? "-";
    $("s-period").textContent = s.period ?? "-";
    $("s-count").textContent = `${s.count}개`;
    $("s-avg").textContent = m.average ?? "-";
    $("s-max").textContent = m.max != null ? `${m.max} (${m.max_date})` : "-";
    $("s-latest").textContent = m.latest != null ? `${m.latest} (${m.latest_date})` : "-";
    $("s-trend").textContent = s.trend ?? "-";
  } catch (e) {
    $("s-trend").textContent = "요약을 불러오지 못했습니다: " + e.message;
  }
}

// ---------- 탭 ----------
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $("tab-chat").classList.toggle("hidden", btn.dataset.tab !== "chat");
    $("tab-data").classList.toggle("hidden", btn.dataset.tab !== "data");
    if (btn.dataset.tab === "data") loadData();
  });
});

// ---------- 채팅 ----------
function addBubble(role, text) {
  const box = $("messages");
  box.querySelector(".empty")?.remove();
  const div = document.createElement("div");
  div.className = `msg-bubble ${role}`;
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function addLoading() {
  const div = addBubble("assistant", "");
  div.innerHTML = '<span class="loading"><span></span><span></span><span></span></span>';
  return div;
}

function resetChat() {
  currentConvId = null;
  $("messages").innerHTML =
    '<div class="empty">예: "요즘 PDRN 관심도 어때?", "가장 높았던 때는 언제야?"</div>';
  highlightConv();
}

$("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("chat-input");
  const message = input.value.trim();
  if (!message) return;

  addBubble("user", message);
  input.value = "";
  $("send-btn").disabled = true;
  const loading = addLoading();

  try {
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: currentConvId }),
    });
    loading.remove();
    addBubble("assistant", res.reply);
    currentConvId = res.conversation_id;
    loadConversations();
  } catch (err) {
    loading.remove();
    addBubble("error", "오류: " + err.message);
  } finally {
    $("send-btn").disabled = false;
    input.focus();
  }
});

$("new-chat").addEventListener("click", resetChat);

// ---------- 대화 기록 ----------
function highlightConv() {
  document.querySelectorAll("#conv-list li[data-id]").forEach((li) => {
    li.classList.toggle("active", li.dataset.id === currentConvId);
  });
}

async function loadConversations() {
  const list = $("conv-list");
  try {
    const convs = await api("/api/conversations");
    list.innerHTML = "";
    if (!convs.length) {
      list.innerHTML = '<li class="empty">저장된 대화가 없습니다</li>';
      return;
    }
    convs.forEach((c) => {
      const li = document.createElement("li");
      li.dataset.id = c.id;
      const title = document.createElement("span");
      title.className = "title";
      title.textContent = c.title;
      const del = document.createElement("button");
      del.className = "link danger";
      del.textContent = "삭제";
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteConversation(c.id);
      });
      li.append(title, del);
      li.addEventListener("click", () => openConversation(c.id));
      list.appendChild(li);
    });
    highlightConv();
  } catch (e) {
    list.innerHTML = `<li class="empty">불러오기 실패: ${e.message}</li>`;
  }
}

async function openConversation(id) {
  try {
    const conv = await api(`/api/conversations/${id}`);
    currentConvId = id;
    $("messages").innerHTML = "";
    conv.messages.forEach((m) => addBubble(m.role, m.content));
    highlightConv();
  } catch (e) {
    alert("대화를 불러오지 못했습니다: " + e.message);
  }
}

async function deleteConversation(id) {
  if (!confirm("이 대화를 삭제할까요?")) return;
  try {
    await api(`/api/conversations/${id}`, { method: "DELETE" });
    if (id === currentConvId) resetChat();
    loadConversations();
  } catch (e) {
    alert("삭제 실패: " + e.message);
  }
}

// ---------- 데이터 관리 ----------
function showDataMsg(text, ok = true) {
  const el = $("data-msg");
  el.textContent = text;
  el.className = "msg " + (ok ? "ok" : "err");
}

async function loadData(highlightId) {
  try {
    const rows = await api("/api/data");
    rows.reverse(); // 최신 날짜가 위로
    $("data-count").textContent = `(${rows.length}개)`;
    const body = $("data-body");
    body.innerHTML = "";
    rows.forEach((r) => {
      const tr = document.createElement("tr");
      if (r.id === highlightId) tr.className = "highlight";
      tr.innerHTML = `<td>${r.date}</td><td>${r.value}</td><td></td><td></td>`;
      tr.children[2].textContent = r.memo;

      const edit = document.createElement("button");
      edit.className = "link";
      edit.textContent = "수정";
      edit.addEventListener("click", () => startEdit(r));
      const del = document.createElement("button");
      del.className = "link danger";
      del.textContent = "삭제";
      del.addEventListener("click", () => deleteData(r));
      tr.children[3].append(edit, del);
      body.appendChild(tr);
    });
  } catch (e) {
    showDataMsg("목록을 불러오지 못했습니다: " + e.message, false);
  }
}

function startEdit(r) {
  $("data-id").value = r.id;
  $("data-date").value = r.date;
  $("data-value").value = r.value;
  $("data-memo").value = r.memo;
  $("form-title").textContent = "데이터 수정";
  $("data-submit").textContent = "수정 저장";
  $("data-cancel").classList.remove("hidden");
  window.scrollTo({ top: $("tab-data").offsetTop, behavior: "smooth" });
}

function resetDataForm() {
  $("data-form").reset();
  $("data-id").value = "";
  $("data-memo").value = "PDRN";
  $("form-title").textContent = "새 데이터 추가";
  $("data-submit").textContent = "추가";
  $("data-cancel").classList.add("hidden");
}

$("data-cancel").addEventListener("click", resetDataForm);

$("data-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = $("data-id").value;
  const payload = {
    date: $("data-date").value,
    value: Number($("data-value").value),
    memo: $("data-memo").value.trim() || "PDRN",
  };
  try {
    const saved = id
      ? await api(`/api/data/${id}`, { method: "PUT", body: JSON.stringify(payload) })
      : await api("/api/data", { method: "POST", body: JSON.stringify(payload) });
    showDataMsg(id ? `수정 완료: ${saved.date} → ${saved.value}` : `추가 완료: ${saved.date} (${saved.value})`);
    resetDataForm();
    await loadData(saved.id);
    loadSummary();
  } catch (err) {
    showDataMsg("저장 실패: " + err.message, false);
  }
});

async function deleteData(r) {
  if (!confirm(`${r.date} 데이터를 삭제할까요?`)) return;
  try {
    await api(`/api/data/${r.id}`, { method: "DELETE" });
    showDataMsg(`삭제 완료: ${r.date}`);
    await loadData();
    loadSummary();
  } catch (e) {
    showDataMsg("삭제 실패: " + e.message, false);
  }
}

// ---------- 시작 ----------
(async () => {
  await wakeServer();
  loadSummary();
  loadConversations();
})();
