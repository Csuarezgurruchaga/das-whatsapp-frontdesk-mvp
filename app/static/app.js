const state = {
  currentUser: null,
  activeTab: "CHATBOT",
  conversationsByState: {
    CHATBOT: [],
    EN_ESPERA: [],
    ASIGNADO: [],
  },
  activeConversation: null,
  activeMessages: [],
  pendingAttachmentMessages: [],
  agentOptions: [],
  taxonomyTags: [],
  taxonomyEnabled: false,
  ws: null,
};

const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;
const IMAGE_MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const AUDIO_MAX_UPLOAD_BYTES = 16 * 1024 * 1024;
const VIDEO_MAX_UPLOAD_BYTES = 16 * 1024 * 1024;
const DOCUMENT_MAX_UPLOAD_BYTES = MAX_UPLOAD_BYTES;

const SUPPORTED_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "video/mp4",
  "video/3gp",
  "video/3gpp",
  "audio/aac",
  "audio/amr",
  "audio/mp4",
  "audio/ogg",
  "audio/mpeg",
  "text/plain",
  "application/pdf",
  "application/msword",
  "application/vnd.ms-excel",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]);

const EXTENSION_TO_MIME = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".mp4": "video/mp4",
  ".3gp": "video/3gp",
  ".3gpp": "video/3gpp",
  ".aac": "audio/aac",
  ".amr": "audio/amr",
  ".m4a": "audio/mp4",
  ".ogg": "audio/ogg",
  ".mp3": "audio/mpeg",
  ".txt": "text/plain",
  ".pdf": "application/pdf",
  ".doc": "application/msword",
  ".xls": "application/vnd.ms-excel",
  ".ppt": "application/vnd.ms-powerpoint",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
};

const VIEWABLE_MIME_TYPES = new Set([
  "application/pdf",
  "image/jpeg",
  "image/png",
  "text/plain",
]);

const els = {
  loginView: document.getElementById("login-view"),
  mainView: document.getElementById("main-view"),
  loginForm: document.getElementById("login-form"),
  loginError: document.getElementById("login-error"),
  taxonomyBtn: document.getElementById("taxonomy-btn"),
  taxonomyModal: document.getElementById("taxonomy-modal"),
  taxonomyModalClose: document.getElementById("taxonomy-modal-close"),
  taxonomyError: document.getElementById("taxonomy-error"),
  taxonomyList: document.getElementById("taxonomy-list"),
  taxonomyCreateForm: document.getElementById("taxonomy-create-form"),
  taxonomyCreateInput: document.getElementById("taxonomy-create-input"),
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
  attachBtn: document.getElementById("attach-btn"),
  attachmentInput: document.getElementById("attachment-input"),
  messageInput: document.getElementById("message-input"),
  composerError: document.getElementById("composer-error"),
  attachmentModal: document.getElementById("attachment-modal"),
  attachmentModalClose: document.getElementById("attachment-modal-close"),
  attachmentModalTitle: document.getElementById("attachment-modal-title"),
  attachmentPreviewFrame: document.getElementById("attachment-preview-frame"),
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
  const isFormData = options.body instanceof FormData;
  const defaultHeaders = isFormData ? {} : { "Content-Type": "application/json" };
  const response = await fetch(path, {
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    throw new Error(await extractErrorDetail(response));
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
  state.activeConversation = null;
  state.activeMessages = [];
  state.pendingAttachmentMessages = [];
  state.taxonomyTags = [];
  state.taxonomyEnabled = false;
  closeTaxonomyModal();
  closeAttachmentPreview();
  disconnectWs();
  setView("login");
}

function initAfterLogin() {
  els.userChip.textContent = `${state.currentUser.username} (${state.currentUser.role})`;
  state.activeTab = "CHATBOT";
  state.activeConversation = null;
  state.activeMessages = [];
  state.pendingAttachmentMessages = [];
  state.taxonomyTags = [];
  state.taxonomyEnabled = false;
  renderTabs();
  loadConversations();
  connectWs();
  if (state.currentUser.role === "admin") {
    loadAgents();
  } else {
    state.agentOptions = [];
  }
  loadTaxonomyState();
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
  state.activeMessages = messages || [];
  renderChat(messages);
}

function renderChat(messages) {
  const currentConversationId = state.activeConversation?.conversation_id;
  const pending = currentConversationId
    ? state.pendingAttachmentMessages.filter(
        (item) => item.conversationId === currentConversationId
      )
    : [];
  const renderedMessages = [...(messages || []), ...pending.map((item) => item.message)];

  els.chatBody.innerHTML = "";
  if (renderedMessages.length === 0) {
    els.chatBody.innerHTML = '<p class="muted">Sin mensajes.</p>';
    return;
  }
  renderedMessages.forEach((msg) => {
    const bubble = document.createElement("div");
    const outbound = msg.direction === "OUTBOUND";
    bubble.className = `message ${outbound ? "outbound" : "inbound"}`;

    const hasAttachment = Boolean(msg.attachment);
    const textValue = (msg.text || "").trim();
    const shouldShowPlainText = !hasAttachment || !textValue.startsWith("[attachment]");

    if (shouldShowPlainText) {
      const text = document.createElement("div");
      text.textContent = msg.text || "(sin texto)";
      bubble.appendChild(text);
    }

    if (hasAttachment) {
      bubble.appendChild(buildAttachmentBubble(msg.attachment));
    }

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${msg.sender_type} · ${formatTime(msg.created_at)}`;

    bubble.appendChild(meta);
    els.chatBody.appendChild(bubble);
  });
  els.chatBody.scrollTop = els.chatBody.scrollHeight;
}

function buildAttachmentBubble(attachment) {
  const wrapper = document.createElement("div");
  wrapper.className = "attachment-bubble";

  const mainLine = document.createElement("div");
  mainLine.className = "attachment-line";
  const icon = document.createElement("span");
  icon.className = "attachment-icon";
  icon.textContent = "📎";
  const filename = document.createElement("span");
  filename.className = "attachment-name";
  filename.textContent = attachment.filename || "adjunto";
  mainLine.appendChild(icon);
  mainLine.appendChild(filename);

  const metaLine = document.createElement("div");
  metaLine.className = "attachment-submeta";
  metaLine.textContent = `${formatFileSize(attachment.size_bytes)} · ${attachment.mime || "-"}`;

  const status = document.createElement("span");
  const statusValue = normalizeAttachmentStatus(attachment.status);
  status.className = `status-pill ${statusValue}`;
  status.textContent = statusLabel(statusValue);

  const lineWithStatus = document.createElement("div");
  lineWithStatus.className = "attachment-line";
  lineWithStatus.appendChild(metaLine);
  lineWithStatus.appendChild(status);

  wrapper.appendChild(mainLine);
  wrapper.appendChild(lineWithStatus);

  if (attachment.attachment_id && statusValue !== "uploading") {
    const actionRow = document.createElement("div");
    actionRow.className = "attachment-actions";

    if (isViewableMime(attachment.mime)) {
      const viewBtn = document.createElement("button");
      viewBtn.type = "button";
      viewBtn.className = "ghost";
      viewBtn.textContent = "Ver";
      viewBtn.addEventListener("click", () => openAttachmentPreview(attachment));
      actionRow.appendChild(viewBtn);
    }

    const downloadBtn = document.createElement("button");
    downloadBtn.type = "button";
    downloadBtn.className = "ghost";
    downloadBtn.textContent = "Descargar";
    downloadBtn.addEventListener("click", () => downloadAttachment(attachment));
    actionRow.appendChild(downloadBtn);

    wrapper.appendChild(actionRow);
  }

  return wrapper;
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
  wrapper.appendChild(buildConversationTagsCard(detail));

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

function canManageTaxonomy() {
  const role = state.currentUser?.role;
  return role === "admin" || role === "supervisor";
}

function canEditTaxonomy() {
  return state.currentUser?.role === "admin";
}

function buildConversationTagsCard(detail) {
  const card = document.createElement("div");
  card.className = "detail-card";

  const heading = document.createElement("strong");
  heading.textContent = "Etiquetas";
  card.appendChild(heading);

  const assignedTags = Array.isArray(detail.tags) ? detail.tags : [];
  const activeAssignedTags = assignedTags.filter((tag) => !tag.is_archived);
  const archivedAssignedTags = assignedTags.filter((tag) => tag.is_archived);

  if (assignedTags.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Sin etiquetas.";
    card.appendChild(empty);
  } else {
    const pills = document.createElement("div");
    pills.className = "tag-pills";
    assignedTags.forEach((tag) => {
      const pill = document.createElement("span");
      pill.className = `tag-pill${tag.is_archived ? " archived" : ""}`;
      pill.textContent = tag.name;
      pills.appendChild(pill);
    });
    card.appendChild(pills);
  }

  const canEditConversationTags =
    state.currentUser &&
    (state.currentUser.role === "agent" || state.currentUser.role === "admin") &&
    state.taxonomyEnabled;
  if (!canEditConversationTags) {
    return card;
  }

  const options = Array.isArray(detail.available_tags)
    ? detail.available_tags.filter((tag) => !tag.is_archived)
    : [];
  if (options.length === 0) {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "No hay etiquetas disponibles.";
    card.appendChild(note);
    return card;
  }

  const selector = document.createElement("div");
  selector.className = "tag-selector";

  const selectedTagIds = new Set(activeAssignedTags.map((tag) => Number(tag.tag_id)));
  options.forEach((tag) => {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = String(tag.tag_id);
    checkbox.checked = selectedTagIds.has(Number(tag.tag_id));
    label.appendChild(checkbox);
    label.append(` ${tag.name}`);
    selector.appendChild(label);
  });

  const applyBtn = document.createElement("button");
  applyBtn.type = "button";
  applyBtn.className = "ghost";
  applyBtn.textContent = "Guardar etiquetas";
  applyBtn.addEventListener("click", async () => {
    const selected = Array.from(selector.querySelectorAll('input[type="checkbox"]:checked')).map(
      (node) => Number(node.value)
    );
    await setConversationTags(detail.conversation_id, selected);
  });

  card.appendChild(selector);
  card.appendChild(applyBtn);

  if (archivedAssignedTags.length > 0) {
    const archived = document.createElement("p");
    archived.className = "muted";
    archived.textContent = `Archivadas: ${archivedAssignedTags.map((tag) => tag.name).join(", ")}`;
    card.appendChild(archived);
  }

  return card;
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

function removePendingAttachmentMessage(tempId) {
  state.pendingAttachmentMessages = state.pendingAttachmentMessages.filter(
    (item) => item.tempId !== tempId
  );
}

function addPendingAttachmentMessage(file, resolvedMime) {
  const currentConversation = state.activeConversation;
  if (!currentConversation) {
    return null;
  }
  const tempId = `pending-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const pendingMessage = {
    message_id: tempId,
    direction: "OUTBOUND",
    sender_type: "AGENT",
    text: `[attachment] ${file.name || "adjunto"}`,
    created_at: new Date().toISOString(),
    attachment: {
      attachment_id: tempId,
      filename: file.name || "adjunto",
      mime: resolvedMime,
      size_bytes: Number(file.size) || 0,
      status: "uploading",
    },
  };

  state.pendingAttachmentMessages.push({
    tempId,
    conversationId: currentConversation.conversation_id,
    message: pendingMessage,
  });
  renderChat(state.activeMessages);
  return tempId;
}

async function sendAttachment() {
  const activeConversationId = state.activeConversation?.conversation_id;
  if (!activeConversationId) {
    return;
  }
  const selectedFile = els.attachmentInput.files?.[0];
  if (!selectedFile) {
    return;
  }

  els.composerError.textContent = "";

  let resolvedMime = "";
  try {
    resolvedMime = resolveAttachmentMime(selectedFile);
    validateAttachmentSize(selectedFile.size, resolvedMime);
  } catch (err) {
    els.composerError.textContent = err instanceof Error ? err.message : "Adjunto invalido.";
    els.attachmentInput.value = "";
    return;
  }

  const tempId = addPendingAttachmentMessage(selectedFile, resolvedMime);
  els.attachBtn.disabled = true;
  els.sendBtn.disabled = true;

  try {
    const formData = new FormData();
    formData.append("file", selectedFile, selectedFile.name || "adjunto");
    await apiFetch(`/conversations/${activeConversationId}/attachments`, {
      method: "POST",
      body: formData,
    });
    els.attachmentInput.value = "";
    await loadMessages(activeConversationId, true);
    await refreshAllLists();
  } catch (err) {
    els.composerError.textContent =
      err instanceof Error && err.message ? err.message : "No se pudo enviar el adjunto.";
    try {
      await loadMessages(activeConversationId, true);
      await refreshAllLists();
    } catch (reloadErr) {
      removePendingAttachmentMessage(tempId);
      renderChat(state.activeMessages);
    }
  } finally {
    removePendingAttachmentMessage(tempId);
    renderChat(state.activeMessages);
    els.attachBtn.disabled = false;
    els.sendBtn.disabled = false;
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

async function loadTaxonomyState() {
  state.taxonomyEnabled = false;
  state.taxonomyTags = [];
  if (!canManageTaxonomy()) {
    els.taxonomyBtn.classList.add("hidden");
    return;
  }
  try {
    const tags = await apiFetch("/conversations/taxonomy/tags?include_archived=true");
    state.taxonomyTags = Array.isArray(tags) ? tags : [];
    state.taxonomyEnabled = true;
    els.taxonomyBtn.classList.remove("hidden");
  } catch (err) {
    els.taxonomyBtn.classList.add("hidden");
  }
}

async function refreshTaxonomyTags() {
  if (!canManageTaxonomy()) {
    return;
  }
  try {
    const tags = await apiFetch("/conversations/taxonomy/tags?include_archived=true");
    state.taxonomyTags = Array.isArray(tags) ? tags : [];
    state.taxonomyEnabled = true;
  } catch (err) {
    state.taxonomyTags = [];
    state.taxonomyEnabled = false;
    throw err;
  }
}

async function setConversationTags(conversationId, tagIds) {
  els.composerError.textContent = "";
  try {
    await apiFetch(`/conversations/${conversationId}/tags`, {
      method: "PUT",
      body: JSON.stringify({ tag_ids: tagIds }),
    });
    await selectConversation(conversationId);
  } catch (err) {
    els.composerError.textContent =
      err instanceof Error && err.message ? err.message : "No se pudieron guardar las etiquetas.";
  }
}

function renderTaxonomyModal() {
  const canEdit = canEditTaxonomy();
  els.taxonomyCreateForm.classList.toggle("hidden", !canEdit);
  els.taxonomyList.innerHTML = "";

  if (!state.taxonomyEnabled) {
    const unavailable = document.createElement("p");
    unavailable.className = "muted";
    unavailable.textContent = "Taxonomia no disponible.";
    els.taxonomyList.appendChild(unavailable);
    return;
  }

  if (state.taxonomyTags.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No hay etiquetas definidas.";
    els.taxonomyList.appendChild(empty);
    return;
  }

  state.taxonomyTags.forEach((tag) => {
    const row = document.createElement("div");
    row.className = "taxonomy-row";

    const name = document.createElement("span");
    name.className = `tag-pill${tag.is_archived ? " archived" : ""}`;
    name.textContent = tag.name;
    row.appendChild(name);

    if (canEdit) {
      const renameInput = document.createElement("input");
      renameInput.type = "text";
      renameInput.value = tag.name;
      renameInput.maxLength = 64;
      renameInput.className = "taxonomy-input";
      row.appendChild(renameInput);

      const renameBtn = document.createElement("button");
      renameBtn.type = "button";
      renameBtn.className = "ghost";
      renameBtn.textContent = "Renombrar";
      renameBtn.addEventListener("click", async () => {
        await updateTaxonomyTag(tag.tag_id, { name: renameInput.value });
      });
      row.appendChild(renameBtn);

      const archiveBtn = document.createElement("button");
      archiveBtn.type = "button";
      archiveBtn.className = "ghost";
      archiveBtn.textContent = tag.is_archived ? "Activar" : "Archivar";
      archiveBtn.addEventListener("click", async () => {
        await updateTaxonomyTag(tag.tag_id, { is_archived: !tag.is_archived });
      });
      row.appendChild(archiveBtn);
    }

    els.taxonomyList.appendChild(row);
  });
}

async function updateTaxonomyTag(tagId, payload) {
  els.taxonomyError.textContent = "";
  try {
    await apiFetch(`/conversations/taxonomy/tags/${tagId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    await refreshTaxonomyTags();
    renderTaxonomyModal();
    if (state.activeConversation) {
      await selectConversation(state.activeConversation.conversation_id);
    }
  } catch (err) {
    els.taxonomyError.textContent =
      err instanceof Error && err.message ? err.message : "No se pudo actualizar la etiqueta.";
  }
}

async function createTaxonomyTag(event) {
  event.preventDefault();
  if (!canEditTaxonomy()) {
    return;
  }
  els.taxonomyError.textContent = "";
  const name = String(els.taxonomyCreateInput.value || "").trim();
  if (!name) {
    els.taxonomyError.textContent = "Ingresa un nombre para la etiqueta.";
    return;
  }
  try {
    await apiFetch("/conversations/taxonomy/tags", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    els.taxonomyCreateInput.value = "";
    await refreshTaxonomyTags();
    renderTaxonomyModal();
    if (state.activeConversation) {
      await selectConversation(state.activeConversation.conversation_id);
    }
  } catch (err) {
    els.taxonomyError.textContent =
      err instanceof Error && err.message ? err.message : "No se pudo crear la etiqueta.";
  }
}

async function openTaxonomyModal() {
  els.taxonomyError.textContent = "";
  try {
    await refreshTaxonomyTags();
    renderTaxonomyModal();
    els.taxonomyModal.classList.remove("hidden");
  } catch (err) {
    els.taxonomyError.textContent =
      err instanceof Error && err.message ? err.message : "Taxonomia no disponible.";
    renderTaxonomyModal();
    els.taxonomyModal.classList.remove("hidden");
  }
}

function closeTaxonomyModal() {
  if (els.taxonomyModal.classList.contains("hidden")) {
    return;
  }
  els.taxonomyModal.classList.add("hidden");
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

function extractExtension(filename) {
  const value = String(filename || "").toLowerCase().trim();
  const lastDot = value.lastIndexOf(".");
  if (lastDot <= 0 || lastDot === value.length - 1) {
    return "";
  }
  return value.slice(lastDot);
}

function resolveAttachmentMime(file) {
  const reportedMime = String(file.type || "").trim().toLowerCase();
  if (reportedMime && reportedMime !== "application/octet-stream") {
    if (!SUPPORTED_MIME_TYPES.has(reportedMime)) {
      throw new Error(`Tipo de archivo no soportado: ${reportedMime}`);
    }
    return reportedMime;
  }
  const inferred = EXTENSION_TO_MIME[extractExtension(file.name)];
  if (!inferred || !SUPPORTED_MIME_TYPES.has(inferred)) {
    throw new Error("No se pudo inferir un tipo de archivo permitido.");
  }
  return inferred;
}

function mediaLimitForMime(mime) {
  if (mime.startsWith("image/")) {
    return IMAGE_MAX_UPLOAD_BYTES;
  }
  if (mime.startsWith("audio/")) {
    return AUDIO_MAX_UPLOAD_BYTES;
  }
  if (mime.startsWith("video/")) {
    return VIDEO_MAX_UPLOAD_BYTES;
  }
  return DOCUMENT_MAX_UPLOAD_BYTES;
}

function validateAttachmentSize(sizeBytes, mime) {
  const size = Number(sizeBytes) || 0;
  if (size <= 0) {
    throw new Error("El adjunto no puede estar vacio.");
  }
  if (size > MAX_UPLOAD_BYTES) {
    throw new Error("El adjunto supera el limite global de 100MB.");
  }
  const mediaLimit = mediaLimitForMime(mime);
  if (size > mediaLimit) {
    throw new Error(`El adjunto supera el limite para ${mime} (${formatFileSize(mediaLimit)}).`);
  }
}

function normalizeAttachmentStatus(status) {
  const value = String(status || "").toLowerCase();
  if (value === "sent" || value === "failed" || value === "uploading") {
    return value;
  }
  return "uploading";
}

function statusLabel(status) {
  if (status === "sent") {
    return "SENT";
  }
  if (status === "failed") {
    return "FAILED";
  }
  return "UPLOADING";
}

function formatFileSize(sizeBytes) {
  const size = Number(sizeBytes) || 0;
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function isViewableMime(mime) {
  return VIEWABLE_MIME_TYPES.has(String(mime || "").toLowerCase());
}

function buildAttachmentUrl(attachment, mode) {
  const conversationId = state.activeConversation?.conversation_id;
  if (!conversationId) {
    throw new Error("No hay una conversacion seleccionada.");
  }
  const attachmentId = encodeURIComponent(attachment.attachment_id);
  return `/conversations/${conversationId}/attachments/${attachmentId}/${mode}`;
}

function downloadAttachment(attachment) {
  try {
    const downloadUrl = buildAttachmentUrl(attachment, "download");
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.target = "_blank";
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (err) {
    els.composerError.textContent =
      err instanceof Error && err.message ? err.message : "No se pudo iniciar la descarga.";
  }
}

function openAttachmentPreview(attachment) {
  if (!isViewableMime(attachment.mime)) {
    els.composerError.textContent = "Este tipo de archivo no admite vista previa.";
    return;
  }
  try {
    const previewUrl = buildAttachmentUrl(attachment, "view");
    els.attachmentModalTitle.textContent = attachment.filename || "Vista previa";
    els.attachmentPreviewFrame.src = previewUrl;
    els.attachmentModal.classList.remove("hidden");
  } catch (err) {
    els.composerError.textContent =
      err instanceof Error && err.message ? err.message : "No se pudo abrir la vista previa.";
  }
}

function closeAttachmentPreview() {
  els.attachmentPreviewFrame.src = "about:blank";
  els.attachmentModal.classList.add("hidden");
}

async function extractErrorDetail(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
        return payload.detail;
      }
    } catch (err) {
      // Fall through and return text.
    }
  }
  const text = await response.text();
  return text || "Request failed";
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

els.taxonomyBtn.addEventListener("click", () => {
  openTaxonomyModal();
});

els.taxonomyCreateForm.addEventListener("submit", createTaxonomyTag);

els.taxonomyModalClose.addEventListener("click", closeTaxonomyModal);

els.taxonomyModal.addEventListener("click", (event) => {
  if (event.target === els.taxonomyModal) {
    closeTaxonomyModal();
  }
});

els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    state.activeTab = tab.dataset.state;
    renderTabs();
    loadConversations();
  });
});

els.sendBtn.addEventListener("click", sendMessage);

els.attachBtn.addEventListener("click", () => {
  if (!state.activeConversation) {
    els.composerError.textContent = "Selecciona una conversacion para adjuntar archivos.";
    return;
  }
  els.composerError.textContent = "";
  els.attachmentInput.click();
});

els.attachmentInput.addEventListener("change", () => {
  sendAttachment();
});

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

els.attachmentModalClose.addEventListener("click", closeAttachmentPreview);

els.attachmentModal.addEventListener("click", (event) => {
  if (event.target === els.attachmentModal) {
    closeAttachmentPreview();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.attachmentModal.classList.contains("hidden")) {
    closeAttachmentPreview();
    return;
  }
  if (event.key === "Escape" && !els.taxonomyModal.classList.contains("hidden")) {
    closeTaxonomyModal();
  }
});

bootstrap();
