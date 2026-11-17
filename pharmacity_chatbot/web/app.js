const SEARCH_URL = "/api/pharmacity/search";
const ANSWER_URL = "/api/pharmacity/answer";

const state = {
  originalQuery: "",
  targetIntent: "",
  searchTerm: "",
  products: [],
  busy: false,
  recognition: null,
};

const messagesEl = document.querySelector("#messages");
const chatFormEl = document.querySelector("#chatForm");
const questionInputEl = document.querySelector("#questionInput");
const productAreaEl = document.querySelector("#productArea");
const productGridEl = document.querySelector("#productGrid");
const searchMetaEl = document.querySelector("#searchMeta");
const manualPanelEl = document.querySelector("#manualPanel");
const manualInputEl = document.querySelector("#manualInput");
const manualCancelEl = document.querySelector("#manualCancel");
const manualSubmitEl = document.querySelector("#manualSubmit");
const keyboardEl = document.querySelector("#keyboard");
const voiceButtonEl = document.querySelector("#voiceButton");

init();

function init() {
  buildKeyboard();
  chatFormEl.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = questionInputEl.value.trim();
    if (query) {
      runSearch(query);
    }
  });
  manualSubmitEl.addEventListener("click", submitManualSearch);
  manualCancelEl.addEventListener("click", closeManualPanel);
  manualInputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      submitManualSearch();
    }
  });
  voiceButtonEl.addEventListener("click", startVoiceInput);
}

async function runSearch(query, options = {}) {
  if (state.busy) {
    return;
  }
  state.busy = true;
  closeManualPanel();
  hideProducts();
  if (!options.silentUserMessage) {
    appendMessage(query, "user");
  }
  appendMessage("Đang tìm sản phẩm trên Pharmacity...", "bot", { transient: true });

  try {
    const response = await fetch(SEARCH_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        original_query: options.originalQuery || query,
        target_intent: options.targetIntent || "",
      }),
    });
    const data = await response.json().catch(() => ({}));
    removeTransientMessages();
    if (!response.ok || !data.ok) {
      throw new Error(data.detail || "Không thể tìm thuốc trên Pharmacity.");
    }
    state.originalQuery = data.original_query || query;
    state.targetIntent = data.target_intent || "";
    state.searchTerm = data.search_term || query;
    state.products = Array.isArray(data.products) ? data.products : [];
    if (!state.products.length) {
      appendMessage("Mình chưa tìm thấy sản phẩm phù hợp. Bạn có thể nhập lại tên thuốc chính xác hơn.", "bot");
      openManualPanel();
      return;
    }
    appendMessage("Mình tìm thấy một vài sản phẩm. Bạn chọn đúng loại thuốc cần hỏi nhé.", "bot");
    renderProducts();
  } catch (error) {
    removeTransientMessages();
    appendMessage(error.message || "Có lỗi khi tra cứu Pharmacity.", "bot");
    openManualPanel();
  } finally {
    state.busy = false;
    questionInputEl.value = "";
  }
}

function renderProducts() {
  productGridEl.replaceChildren();
  searchMetaEl.textContent = state.searchTerm ? `Từ khóa: ${state.searchTerm}` : "";
  state.products.slice(0, 4).forEach((product, index) => {
    const card = document.createElement("button");
    card.className = "product-card";
    card.type = "button";
    card.addEventListener("click", () => chooseProduct(product, card));

    const imageWrap = document.createElement("span");
    imageWrap.className = "product-image";
    if (product.image_url) {
      const image = document.createElement("img");
      image.src = product.image_url;
      image.alt = "";
      image.loading = "lazy";
      imageWrap.appendChild(image);
    } else {
      imageWrap.textContent = "Thuốc";
    }

    const name = document.createElement("span");
    name.className = "product-name";
    name.textContent = product.name || `Sản phẩm ${index + 1}`;
    card.append(imageWrap, name);
    productGridEl.appendChild(card);
  });

  const manualCard = document.createElement("button");
  manualCard.className = "product-card manual-card";
  manualCard.type = "button";
  manualCard.innerHTML = "<span class=\"manual-icon\" aria-hidden=\"true\">⌨</span><span class=\"product-name\">Nhập tên thuốc</span>";
  manualCard.addEventListener("click", openManualPanel);
  productGridEl.appendChild(manualCard);
  productAreaEl.hidden = false;
}

async function chooseProduct(product, selectedCard) {
  if (state.busy) {
    return;
  }
  state.busy = true;
  setProductDisabled(true, selectedCard);
  appendMessage(`Bạn đã chọn: ${product.name}`, "user");
  appendMessage("Đang lấy thông tin chi tiết từ Pharmacity...", "bot", { transient: true });

  try {
    const response = await fetch(ANSWER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        original_query: state.originalQuery,
        target_intent: state.targetIntent,
        product,
      }),
    });
    const data = await response.json().catch(() => ({}));
    removeTransientMessages();
    if (!response.ok || !data.ok) {
      throw new Error(data.detail || "Không thể lấy thông tin thuốc.");
    }
    hideProducts();
    appendMessage(data.answer, "bot", data.source_url ? { sourceUrl: data.source_url } : {});
    speak(data.answer);
  } catch (error) {
    removeTransientMessages();
    appendMessage(error.message || "Mình chưa lấy được thông tin chi tiết.", "bot");
    setProductDisabled(false);
  } finally {
    state.busy = false;
  }
}

function setProductDisabled(disabled, selectedCard = null) {
  productGridEl.querySelectorAll("button").forEach((button) => {
    button.disabled = disabled;
    button.classList.toggle("selected", button === selectedCard);
  });
}

function hideProducts() {
  productAreaEl.hidden = true;
  productGridEl.replaceChildren();
}

function openManualPanel() {
  manualPanelEl.hidden = false;
  manualInputEl.value = state.searchTerm || "";
  manualInputEl.focus();
}

function closeManualPanel() {
  manualPanelEl.hidden = true;
}

function submitManualSearch() {
  const query = manualInputEl.value.trim();
  if (!query) {
    manualInputEl.focus();
    return;
  }
  runSearch(query, {
    originalQuery: state.originalQuery || query,
    targetIntent: state.targetIntent,
    silentUserMessage: false,
  });
}

function buildKeyboard() {
  const rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"];
  rows.forEach((row) => {
    const rowEl = document.createElement("div");
    rowEl.className = "keyboard-row";
    row.split("").forEach((letter) => {
      rowEl.appendChild(keyButton(letter, () => appendManualText(letter)));
    });
    keyboardEl.appendChild(rowEl);
  });
  const actionRow = document.createElement("div");
  actionRow.className = "keyboard-row action-row";
  actionRow.append(
    keyButton("Xóa", () => {
      manualInputEl.value = manualInputEl.value.slice(0, -1);
      manualInputEl.focus();
    }),
    keyButton("Cách", () => appendManualText(" ")),
    keyButton("Tìm", submitManualSearch)
  );
  keyboardEl.appendChild(actionRow);
}

function keyButton(label, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

function appendManualText(text) {
  manualInputEl.value += text;
  manualInputEl.focus();
}

function appendMessage(text, role, options = {}) {
  const message = document.createElement("article");
  message.className = `message ${role}`;
  if (options.transient) {
    message.dataset.transient = "true";
  }
  message.textContent = text;
  if (options.sourceUrl) {
    const source = document.createElement("a");
    source.href = options.sourceUrl;
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    source.textContent = "Nguồn Pharmacity";
    message.appendChild(document.createElement("br"));
    message.appendChild(source);
  }
  messagesEl.appendChild(message);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function removeTransientMessages() {
  messagesEl.querySelectorAll("[data-transient='true']").forEach((node) => node.remove());
}

function speak(text) {
  if (!("speechSynthesis" in window) || !text) {
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "vi-VN";
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
}

function startVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    appendMessage("Trình duyệt này chưa hỗ trợ nhập giọng nói. Bạn nhập câu hỏi bằng bàn phím nhé.", "bot");
    return;
  }
  if (state.recognition) {
    state.recognition.stop();
    state.recognition = null;
    return;
  }
  const recognition = new SpeechRecognition();
  state.recognition = recognition;
  recognition.lang = "vi-VN";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  voiceButtonEl.classList.add("listening");
  recognition.addEventListener("result", (event) => {
    const transcript = event.results?.[0]?.[0]?.transcript || "";
    questionInputEl.value = transcript;
    if (transcript.trim()) {
      runSearch(transcript.trim());
    }
  });
  recognition.addEventListener("end", () => {
    voiceButtonEl.classList.remove("listening");
    state.recognition = null;
  });
  recognition.addEventListener("error", () => {
    voiceButtonEl.classList.remove("listening");
    state.recognition = null;
    appendMessage("Mình chưa nghe được giọng nói. Bạn thử lại hoặc nhập bằng bàn phím.", "bot");
  });
  recognition.start();
}
