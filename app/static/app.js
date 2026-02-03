const state = {
  currentUser: null,
  activeTab: "CHATBOT",
  conversationsByState: {
    CHATBOT: [],
    EN_ESPERA: [],
    ASIGNADO: [],
  },
  activeConversation: null,
  agentOptions: [],
  ws: null,
};

const els = {
  loginView: document.getElementById("login-view"),
  mainView: document.getElementById("main-view"),
  loginForm: document.getElementById("login-form"),
  loginError: document.getElementById("login-error"),
  logoutBtn: document.getElementById("logout-btn"),
  userChip: document.getElementById("user-chip"),
  tabs: document.querySelectorAll(".tab"),
  listTitle: document.getElementById("list-title"),
  listCount: document.getElementById("list-count"),
  conversationList: document.getElementById("conversation-list"),
  chatTitle: document.getElementById("chat-title"),
  chatMeta: document.getElementById("chat-meta"),
  chatBody: document.getElementById("chat-body"),
  detailBody: document.getElementById("detail-body"),
  sendBtn: document.getElementById("send-btn"),
  messageInput: document.getElementById("message-input"),
  composerError: document.getElementById("composer-error"),
  quickActions: document.querySelectorAll(".chip"),
};

function setView(view) {
  if (view === "login") {
    els.loginView.classList.remove("hidden");
    els.mainView.classList.add("hidden");
  } else {
    els.loginView.classList.add("hidden");
    els.mainView.classList.remove("hidden");
  }
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Request failed");
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function bootstrap() {
  try {
    const me = await apiFetch("/auth/me");
    state.currentUser = me;
    setView("main");
    initAfterLogin();
  } catch (err) {
    setView("login");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  els.loginError.textContent = "";
  const form = new FormData(els.loginForm);
  const payload = {
    username: String(form.get("username") || "").trim(),
    password: String(form.get("password") || "").trim(),
  };

  try {
    const me = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.currentUser = me;
    setView("main");
    initAfterLogin();
  } catch (err) {
    els.loginError.textContent = "Credenciales invalidas.";
  }
}

async function handleLogout() {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch (err) {
    // Ignore logout errors.
  }
  state.currentUser = null;
  disconnectWs();
  setView("login");
}

function initAfterLogin() {
  els.userChip.textContent = `${state.currentUser.username} (${state.currentUser.role})`;
  state.activeTab = "CHATBOT";
  state.activeConversation = null;
  renderTabs();
  loadConversations();
  connectWs();
  if (state.currentUser.role === "admin") {
    loadAgents();
  }
}

function renderTabs() {
  els.tabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.state === state.activeTab);
  });
}

async function loadConversations() {
  const stateKey = state.activeTab;
  try {
    const data = await apiFetch(`/conversations?state=${stateKey}`);
    state.conversationsByState[stateKey] = data;
    renderConversationList();
  } catch (err) {
    renderConversationList();
  }
}

async function refreshAllLists() {
  await Promise.all(
    Object.keys(state.conversationsByState).map(async (stateKey) => {
      try {
        const data = await apiFetch(`/conversations?state=${stateKey}`);
        state.conversationsByState[stateKey] = data;
      } catch (err) {
        // Keep old list if fetch fails.
      }
    })
  );
  renderConversationList();
}

function renderConversationList() {
  const list = state.conversationsByState[state.activeTab] || [];
  els.listTitle.textContent = `Conversaciones ${labelForState(state.activeTab)}`;
  els.listCount.textContent = String(list.length);
  els.conversationList.innerHTML = "";

  list.forEach((item) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "list-item";
    if (state.activeConversation && item.conversation_id === state.activeConversation.conversation_id) {
      card.classList.add("active");
    }

    const title = document.createElement("h3");
    title.textContent = item.contact_name || item.contact_number || `#${item.conversation_id}`;

    const preview = document.createElement("div");
    preview.className = "muted";
    preview.textContent = item.last_message_text || "Sin mensajes";

    const meta = document.createElement("div");
    meta.className = "list-meta";

    const time = document.createElement("span");
    time.textContent = formatRelative(item.last_activity_at);

    meta.appendChild(time);

    if (item.unread_count > 0) {
      const unread = document.createElement("span");
      unread.className = "unread";
      unread.textContent = String(item.unread_count);
      meta.appendChild(unread);
    }

    card.appendChild(title);
    card.appendChild(preview);
    card.appendChild(meta);

    card.addEventListener("click", () => selectConversation(item.conversation_id));

    els.conversationList.appendChild(card);
  });

  if (list.length === 0) {
    const empty = document.createElement("div");
    empty.className = "muted";
    empty.textContent = "No hay conversaciones en este estado.";
    els.conversationList.appendChild(empty);
  }
}

async function selectConversation(conversationId) {
  if (!conversationId) {
    return;
  }
  try {
    const detail = await apiFetch(`/conversations/${conversationId}`);
    state.activeConversation = detail;
    renderDetails();
    await loadMessages(conversationId, true);
    renderConversationList();
  } catch (err) {
    // ignore
  }
}

async function loadMessages(conversationId, markRead) {
  const query = markRead ? "?mark_read=true" : "";
  const messages = await apiFetch(`/conversations/${conversationId}/messages${query}`);
  renderChat(messages);
}

function renderChat(messages) {
  els.chatBody.innerHTML = "";
  if (!messages || messages.length === 0) {
    els.chatBody.innerHTML = '<p class="muted">Sin mensajes.</p>';
    return;
  }
  messages.forEach((msg) => {
    const bubble = document.createElement("div");
    const outbound = msg.direction === "OUTBOUND";
    bubble.className = `message ${outbound ? "outbound" : "inbound"}`;

    const text = document.createElement("div");
    text.textContent = msg.text || "(sin texto)";

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${msg.sender_type} · ${formatTime(msg.created_at)}`;

    bubble.appendChild(text);
    bubble.appendChild(meta);
    els.chatBody.appendChild(bubble);
  });
  els.chatBody.scrollTop = els.chatBody.scrollHeight;
}

function renderDetails() {
  const detail = state.activeConversation;
  if (!detail) {
    els.detailBody.innerHTML = '<p class="muted">Sin conversacion activa.</p>';
    els.chatTitle.textContent = "Conversacion";
    els.chatMeta.textContent = "Selecciona una conversacion";
    return;
  }

  const title = detail.contact_name || detail.contact_number || `#${detail.conversation_id}`;
  els.chatTitle.textContent = title;
  els.chatMeta.textContent = `Estado: ${labelForState(detail.state)}`;

  const wrapper = document.createElement("div");
  wrapper.className = "details";

  wrapper.appendChild(detailRow("Contacto", detail.contact_number || "-"));
  wrapper.appendChild(detailRow("Estado", labelForState(detail.state)));
  wrapper.appendChild(detailRow("Asignado", detail.assigned_to_username || "Sin asignar"));
  wrapper.appendChild(detailRow("Ultima actividad", formatDateTime(detail.last_activity_at)));

  const actions = document.createElement("div");
  actions.className = "detail-actions";

  if (detail.state === "EN_ESPERA") {
    const takeBtn = document.createElement("button");
    takeBtn.className = "primary";
    takeBtn.textContent = "Tomar conversacion";
    takeBtn.addEventListener("click", () => takeConversation(detail.conversation_id));
    actions.appendChild(takeBtn);
  }

  if (detail.state === "ASIGNADO") {
    const closeBtn = document.createElement("button");
    closeBtn.className = "ghost";
    closeBtn.textContent = "Cerrar conversacion";
    closeBtn.addEventListener("click", () => closeConversation(detail.conversation_id));
    actions.appendChild(closeBtn);
  }

  if (state.currentUser && state.currentUser.role === "admin" && detail.state === "ASIGNADO") {
    const assignSelfBtn = document.createElement("button");
    assignSelfBtn.className = "primary";
    assignSelfBtn.textContent = "Asignarme";
    assignSelfBtn.addEventListener("click", () => reassignConversation(detail.conversation_id, state.currentUser.user_id));
    actions.appendChild(assignSelfBtn);

    const select = document.createElement("select");
    select.id = "agent-select";
    state.agentOptions.forEach((agent) => {
      const option = document.createElement("option");
      option.value = agent.user_id;
      option.textContent = agent.username;
      select.appendChild(option);
    });

    const reassignBtn = document.createElement("button");
    reassignBtn.className = "ghost";
    reassignBtn.textContent = "Reasignar";
    reassignBtn.addEventListener("click", () => {
      const assigneeId = Number(select.value || 0);
      if (assigneeId) {
        reassignConversation(detail.conversation_id, assigneeId);
      }
    });

    const reassignWrapper = document.createElement("div");
    reassignWrapper.className = "detail-card";
    reassignWrapper.appendChild(select);
    reassignWrapper.appendChild(reassignBtn);
    actions.appendChild(reassignWrapper);
  }

  if (actions.children.length > 0) {
    const actionCard = document.createElement("div");
    actionCard.className = "detail-card";
    actionCard.appendChild(actions);
    wrapper.appendChild(actionCard);
  }

  els.detailBody.innerHTML = "";
  els.detailBody.appendChild(wrapper);
}

function detailRow(label, value) {
  const card = document.createElement("div");
  card.className = "detail-card";
  const labelEl = document.createElement("strong");
  labelEl.textContent = label;
  const valueEl = document.createElement("div");
  valueEl.textContent = value;
  card.appendChild(labelEl);
  card.appendChild(valueEl);
  return card;
}

async function sendMessage() {
  if (!state.activeConversation) {
    return;
  }
  const text = els.messageInput.value.trim();
  if (!text) {
    return;
  }
  els.composerError.textContent = "";
  try {
    await apiFetch(`/conversations/${state.activeConversation.conversation_id}/messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    els.messageInput.value = "";
    await loadMessages(state.activeConversation.conversation_id, true);
    await refreshAllLists();
  } catch (err) {
    els.composerError.textContent = "No se pudo enviar el mensaje.";
  }
}

async function takeConversation(conversationId) {
  try {
    await apiFetch(`/conversations/${conversationId}/take`, { method: "POST" });
    await refreshAllLists();
    await selectConversation(conversationId);
  } catch (err) {
    // ignore
  }
}

async function closeConversation(conversationId) {
  try {
    await apiFetch(`/conversations/${conversationId}/close`, { method: "POST" });
    state.activeConversation = null;
    renderDetails();
    await refreshAllLists();
  } catch (err) {
    // ignore
  }
}

async function reassignConversation(conversationId, assigneeId) {
  try {
    await apiFetch(`/conversations/${conversationId}/reassign`, {
      method: "POST",
      body: JSON.stringify({ assignee_user_id: assigneeId }),
    });
    await refreshAllLists();
    await selectConversation(conversationId);
  } catch (err) {
    // ignore
  }
}

async function loadAgents() {
  try {
    const agents = await apiFetch("/auth/users?role=agent");
    state.agentOptions = agents || [];
  } catch (err) {
    state.agentOptions = [];
  }
}

function connectWs() {
  if (state.ws) {
    return;
  }
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${protocol}://${window.location.host}/realtime/ws`;
  const ws = new WebSocket(wsUrl);
  state.ws = ws;

  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      handleRealtimeEvent(payload);
    } catch (err) {
      // ignore
    }
  };

  ws.onclose = () => {
    state.ws = null;
    setTimeout(connectWs, 2000);
  };
}

function disconnectWs() {
  if (state.ws) {
    state.ws.close();
    state.ws = null;
  }
}

async function handleRealtimeEvent(payload) {
  if (!payload || !payload.type) {
    return;
  }
  if (payload.type === "conversation.updated") {
    await refreshAllLists();
    if (state.activeConversation && payload.data.conversation_id === state.activeConversation.conversation_id) {
      await selectConversation(state.activeConversation.conversation_id);
    }
  }
  if (payload.type === "message.new") {
    if (state.activeConversation && payload.data.conversation_id === state.activeConversation.conversation_id) {
      await loadMessages(state.activeConversation.conversation_id, true);
    } else {
      await refreshAllLists();
    }
  }
}

function labelForState(stateKey) {
  switch (stateKey) {
    case "CHATBOT":
      return "Chatbot";
    case "EN_ESPERA":
      return "En espera";
    case "ASIGNADO":
      return "Asignados";
    case "CERRADO":
      return "Cerrado";
    default:
      return stateKey;
  }
}

function formatRelative(value) {
  if (!value) {
    return "";
  }
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) {
    return "";
  }
  const diffSeconds = Math.max(0, Math.floor((Date.now() - time) / 1000));
  if (diffSeconds < 60) {
    return "ahora";
  }
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) {
    return `${diffMinutes}m`;
  }
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h`;
  }
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d`;
}

function formatTime(value) {
  if (!value) {
    return "";
  }
  try {
    return new Intl.DateTimeFormat("es-AR", {
      timeZone: "America/Argentina/Buenos_Aires",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch (err) {
    return "";
  }
}

function formatDateTime(value) {
  if (!value) {
    return "";
  }
  try {
    return new Intl.DateTimeFormat("es-AR", {
      timeZone: "America/Argentina/Buenos_Aires",
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch (err) {
    return "";
  }
}

els.loginForm.addEventListener("submit", handleLogin);

els.logoutBtn.addEventListener("click", handleLogout);

els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    state.activeTab = tab.dataset.state;
    renderTabs();
    loadConversations();
  });
});

els.sendBtn.addEventListener("click", sendMessage);

els.messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

els.quickActions.forEach((button) => {
  button.addEventListener("click", () => {
    const template = button.dataset.template || "";
    els.messageInput.value = template;
    els.messageInput.focus();
  });
});

bootstrap();
