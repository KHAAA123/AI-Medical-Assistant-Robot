const state = {
  activeScreen: "home",
  medicineCode: "",
  qrStream: null,
  qrDetector: null,
  qrAnimationFrame: null,
  qrBusy: false,
  qrLastScanTime: 0,
  dispenseAbortController: null,
  conversationId: null,
  recognition: null,
  voiceOpen: false,
  voiceBusy: false,
  voiceListening: false,
  voiceSpeaking: false,
  voiceEventSource: null,
  voiceWebSocket: null,
  voiceMediaStream: null,
  voiceAudioContext: null,
  voiceAudioInputSource: null,
  voiceAudioProcessor: null,
  voiceAudioSilenceGain: null,
  voiceOutputNextTime: 0,
  geminiLiveReady: false,
  geminiLiveModel: null,
  voicePermissionBlocked: false,
  voiceSessionId: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
  voiceGreetingAudio: null,
  voiceGreetingFinished: true,
  voicePreferredVoice: null,
  voiceWarmupDone: false,
  pendingGeminiToolCalls: {},
  pendingVoiceMedicineSelection: false,
  pendingVoiceMedicineConfirmation: false,
  medicineSelectionOpen: false,
  medicineRetryOpen: false,
  medicineOptions: [],
  pharmacityOriginalQuery: "",
  pharmacityTargetIntent: "",
  pharmacitySearchTerm: "",
  currentMedicineOrder: null,
  currentDispenseSession: null,
  dispenseStatusTimer: null,
  pickupCountdownTimer: null,
  pickupCountdownWarned: false,
  medicineDispenseBusy: false,
  doctorSettings: null,
  doctorAuthenticated: false,
  doctorDoorStates: [
    { door: 1, state: "UNKNOWN" },
    { door: 2, state: "UNKNOWN" },
    { door: 3, state: "UNKNOWN" },
  ],
  doctorArduinoConnected: false,
  doctorArduinoBusy: false,
  doctorArduinoConfigured: false,
  doctorArduinoConnectionState: "unconfigured",
  doctorArduinoPort: "",
  doctorStatusPollTimer: null,
  doctorDoorHomeBusy: false,
  doctorTrayBusy: false,
  doctorHomeTrayBusy: false,
  doctorTrayPosition: 1,
  doctorTrayCalibrated: false,
  doctorTrayEnabled: false,
  doctorTrayHardwareBusy: false,
  medicineOrders: [],
  doctorUploadBusy: false,
  voiceReconnectAttempts: 0,
  voiceReconnectTimer: null,
};

const screens = {
  home: document.querySelector("#homeScreen"),
  guideList: document.querySelector("#guideListScreen"),
  guideDetail: document.querySelector("#guideDetailScreen"),
  medicine: document.querySelector("#medicineChoiceScreen"),
  manual: document.querySelector("#manualScreen"),
  qr: document.querySelector("#qrScreen"),
  medicineConfirm: document.querySelector("#medicineConfirmScreen"),
  medicinePickup: document.querySelector("#medicinePickupScreen"),
  map: document.querySelector("#mapScreen"),
  doctorLogin: document.querySelector("#doctorLoginScreen"),
  doctor: document.querySelector("#doctorScreen"),
  loading: document.querySelector("#loadingScreen"),
};

const clockTextEl = document.querySelector("#clockText");
const dateTextEl = document.querySelector("#dateText");
const guideButtonEl = document.querySelector("#guideButton");
const doctorButtonEl = document.querySelector("#doctorButton");
const mapButtonEl = document.querySelector("#mapButton");
const medicineButtonEl = document.querySelector("#medicineButton");
const voiceButtonEl = document.querySelector("#voiceButton");
const manualMedicineButtonEl = document.querySelector("#manualMedicineButton");
const qrMedicineButtonEl = document.querySelector("#qrMedicineButton");
const guideDetailTitleEl = document.querySelector("#guideDetailTitle");
const medicineCodeDisplayEl = document.querySelector("#medicineCodeDisplay");
const medicineErrorEl = document.querySelector("#medicineError");
const manualErrorEl = document.querySelector("#manualError");
const qrVideoEl = document.querySelector("#qrVideo");
const qrCanvasEl = document.querySelector("#qrCanvas");
const qrStatusEl = document.querySelector("#qrStatus");
const qrFallbackButtonEl = document.querySelector("#qrFallbackButton");
const cameraPlaceholderEl = document.querySelector("#cameraPlaceholder");
const medicineConfirmNameEl = document.querySelector("#medicineConfirmName");
const medicineConfirmBedEl = document.querySelector("#medicineConfirmBed");
const medicineConfirmPositionEl = document.querySelector("#medicineConfirmPosition");
const medicineConfirmPrescriptionEl = document.querySelector("#medicineConfirmPrescription");
const medicineConfirmInstructionsEl = document.querySelector("#medicineConfirmInstructions");
const medicineConfirmErrorEl = document.querySelector("#medicineConfirmError");
const confirmDispenseButtonEl = document.querySelector("#confirmDispenseButton");
const cancelDispenseButtonEl = document.querySelector("#cancelDispenseButton");
const medicinePickupNameEl = document.querySelector("#medicinePickupName");
const medicinePickupBedEl = document.querySelector("#medicinePickupBed");
const medicinePickupPositionEl = document.querySelector("#medicinePickupPosition");
const medicinePickupInstructionsEl = document.querySelector("#medicinePickupInstructions");
const medicinePickupErrorEl = document.querySelector("#medicinePickupError");
const completeDispenseButtonEl = document.querySelector("#completeDispenseButton");
const retryDispenseButtonEl = document.querySelector("#retryDispenseButton");
const pickupCountdownValueEl = document.querySelector("#pickupCountdownValue");
const pickupCountdownLabelEl = document.querySelector("#pickupCountdownLabel");
const voiceOverlayEl = document.querySelector("#voiceOverlay");
const voiceEmojiEl = document.querySelector("#voiceEmoji");
const newVoiceSessionButtonEl = document.querySelector("#newVoiceSessionButton");
const closeVoiceButtonEl = document.querySelector("#closeVoiceButton");
const voiceStatusEl = document.querySelector("#voiceStatus");
const voiceTranscriptEl = document.querySelector("#voiceTranscript");
const medicineClassGridEl = document.querySelector("#medicineClassGrid");
const medicineRetryPanelEl = document.querySelector("#medicineRetryPanel");
const medicineRetryInputEl = document.querySelector("#medicineRetryInput");
const medicineRetrySearchButtonEl = document.querySelector("#medicineRetrySearchButton");
const medicineRetryCancelButtonEl = document.querySelector("#medicineRetryCancelButton");
const voiceMedicineConfirmEl = document.querySelector("#voiceMedicineConfirm");
const voiceMedicineConfirmButtonEl = document.querySelector("#voiceMedicineConfirmButton");
const voiceMedicineCancelButtonEl = document.querySelector("#voiceMedicineCancelButton");
const doctorLoginFormEl = document.querySelector("#doctorLoginForm");
const doctorLoginUsernameInputEl = document.querySelector("#doctorLoginUsernameInput");
const doctorLoginPasswordInputEl = document.querySelector("#doctorLoginPasswordInput");
const doctorLoginErrorEl = document.querySelector("#doctorLoginError");
const doctorSettingsButtonEl = document.querySelector("#doctorSettingsButton");
const settingsPanelEl = document.querySelector("#settingsPanel");
const closeSettingsButtonEl = document.querySelector("#closeSettingsButton");
const doctorSettingsFormEl = document.querySelector("#doctorSettingsForm");
const apiProviderSelectEl = document.querySelector("#apiProviderSelect");
const apiModelSelectEl = document.querySelector("#apiModelSelect");
const apiBaseUrlInputEl = document.querySelector("#apiBaseUrlInput");
const volumeRangeEl = document.querySelector("#volumeRange");
const volumeValueEl = document.querySelector("#volumeValue");
const arduinoPortInputEl = document.querySelector("#arduinoPortInput");
const arduinoBaudRateInputEl = document.querySelector("#arduinoBaudRateInput");
const arduinoTimeoutInputEl = document.querySelector("#arduinoTimeoutInput");
const doctorSettingsErrorEl = document.querySelector("#doctorSettingsError");
const excelUploadButtonEl = document.querySelector("#excelUploadButton");
const excelUploadInputEl = document.querySelector("#excelUploadInput");
const excelUploadStatusEl = document.querySelector("#excelUploadStatus");
const excelUploadErrorEl = document.querySelector("#excelUploadError");
const excelTemplateDownloadButtonEl = document.querySelector("#excelTemplateDownloadButton");
const trayDoorButtons = document.querySelectorAll("[data-tray-door]");
const homeDoorsButtonEl = document.querySelector("#homeDoorsButton");
const homeTrayButtonEl = document.querySelector("#homeTrayButton");
const rotateTrayButtonEl = document.querySelector("#rotateTrayButton");
const doctorTrayPositionStatusEl = document.querySelector("#doctorTrayPositionStatus");
const doctorTrayPositionBadgeEl = document.querySelector("#doctorTrayPositionBadge");
const doctorArduinoStatusEl = document.querySelector("#doctorArduinoStatus");
const doctorMedicineRowsEl = document.querySelector("#doctorMedicineRows");
const trayCalibrationCardEl = document.querySelector("#trayCalibrationCard");
const trayCalibrationTitleEl = document.querySelector("#trayCalibrationTitle");
const trayCalibrationHintEl = document.querySelector("#trayCalibrationHint");
const calibrateTrayButtonEl = document.querySelector("#calibrateTrayButton");

const DOCTOR_SETTINGS_STORAGE_KEY = "robotDoctorSettings";
const DOCTOR_TRAY_POSITION_MAX = 8;
const MEDICINE_TEMPLATE_URL = "/robot/api/medicine/template";
const MEDICINE_ORDERS_URL = "/robot/api/medicine/orders";
const MEDICINE_UPLOAD_URL = "/robot/api/medicine/orders/upload";
const MEDICINE_LOOKUP_URL = "/robot/api/medicine/lookup";
const MEDICINE_DISPENSE_URL = "/robot/api/medicine/dispense";
const MEDICINE_DISPENSE_COMPLETE_URL = "/robot/api/medicine/dispense/complete";
const MEDICINE_DISPENSE_STATUS_URL = "/robot/api/medicine/dispense/status";
const MEDICINE_DISPENSE_RESOLVE_URL = "/robot/api/medicine/dispense/resolve";
const MEDICINE_SETUP_CHECK_URL = "/robot/api/medicine/setup/check";
const MEDICINE_SETUP_TRAY_URL = "/robot/api/medicine/setup/tray";
const QR_SCAN_INTERVAL_MS = 150;
const ARDUINO_STATUS_URL = "/robot/api/arduino/status";
const ARDUINO_SETTINGS_URL = "/robot/api/arduino/settings";
const ARDUINO_HOME_URL = "/robot/api/arduino/home";
const ARDUINO_DOOR_URL = "/robot/api/arduino/door";
const ARDUINO_TRAY_CALIBRATE_URL = "/robot/api/arduino/tray/calibrate";
const ARDUINO_TRAY_RELEASE_URL = "/robot/api/arduino/tray/release";
// Lệnh phần cứng (mở/đóng khay) phải có giới hạn thời gian để UI không treo vô
// hạn nếu backend/serial Arduino không phản hồi.
const HARDWARE_REQUEST_TIMEOUT_MS = 35000;
const HARDWARE_HOME_TIMEOUT_MS = 70000;
const ARDUINO_STATUS_POLL_MS = 3000;
// Tự kết nối lại Gemini Live khi WebSocket rớt giữa chừng (mạng chập chờn trên
// kiosk). Có giới hạn số lần + backoff để tránh bão reconnect.
const VOICE_MAX_RECONNECT_ATTEMPTS = 3;
const VOICE_RECONNECT_BASE_MS = 800;
const VOICE_GREETING_AUDIO_URL = "/assets/audio/greeting-vi-en.mp3";
const VOICE_UTTERANCE_CONFIG = {
  lang: "vi-VN",
  rate: 0.95,
  pitch: 1,
};
const GEMINI_EPHEMERAL_TOKEN_URL = "/robot/api/gemini/ephemeral-token";
const GEMINI_LIVE_WS_URL =
  "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained";
const RAG_ANSWER_URL = "/robot/api/rag/answer";
const PHARMACITY_SEARCH_URL = "/robot/api/pharmacity/search";
const PHARMACITY_ANSWER_URL = "/robot/api/pharmacity/answer";
const API_MODEL_OPTIONS = {
  chatgpt: [
    { value: "gpt-4o-mini", label: "gpt-4o-mini" },
    { value: "gpt-4.1-mini", label: "gpt-4.1-mini" },
  ],
  gemini: [
    { value: "gemini-2.5-flash", label: "gemini-2.5-flash" },
    { value: "gemini-2.5-pro", label: "gemini-2.5-pro" },
  ],
};

const GUIDE_TITLES = new Set([
  "Hướng dẫn lấy thuốc",
  "Hướng dẫn đàm thoại với AI",
  "Hướng dẫn quét mã QR",
  "Hướng dẫn nhập mã lấy thuốc",
]);

init();

function init() {
  setupOptionalIcons();
  setupSpeechSynthesisWarmup();
  updateClock();
  window.setInterval(updateClock, 1000);
  initDoctorPanel();
  restoreActiveDispenseSession();

  guideButtonEl.addEventListener("click", () => showScreen("guideList"));
  doctorButtonEl.addEventListener("click", openDoctorArea);
  mapButtonEl.addEventListener("click", () => showScreen("map"));
  medicineButtonEl.addEventListener("click", () => {
    clearMedicineErrors();
    showScreen("medicine");
  });
  voiceButtonEl.addEventListener("click", openVoiceMode);
  newVoiceSessionButtonEl.addEventListener("click", resetVoiceConversation);
  closeVoiceButtonEl.addEventListener("click", closeVoiceMode);
  voiceMedicineConfirmButtonEl?.addEventListener("click", confirmVoiceMedicineDispense);
  voiceMedicineCancelButtonEl?.addEventListener("click", clearVoiceMedicineConfirmation);
  medicineRetrySearchButtonEl?.addEventListener("click", submitMedicineRetrySearch);
  medicineRetryCancelButtonEl?.addEventListener("click", () => closeMedicineRetryPanel({ restoreGrid: true }));
  medicineRetryInputEl?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      submitMedicineRetrySearch();
    }
  });
  confirmDispenseButtonEl?.addEventListener("click", dispenseCurrentMedicineOrder);
  cancelDispenseButtonEl?.addEventListener("click", returnHome);
  completeDispenseButtonEl?.addEventListener("click", completeCurrentMedicineDispense);
  retryDispenseButtonEl?.addEventListener("click", openDoctorArea);

  manualMedicineButtonEl.addEventListener("click", () => {
    resetMedicineCode();
    showScreen("manual");
  });
  qrMedicineButtonEl.addEventListener("click", () => {
    clearMedicineErrors();
    showScreen("qr");
    startQrScanner();
  });
  qrFallbackButtonEl.addEventListener("click", () => {
    stopQrScanner();
    resetMedicineCode();
    showScreen("manual");
  });

  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", returnHome);
  });

  document.querySelectorAll("[data-guide-title]").forEach((button) => {
    button.addEventListener("click", () => {
      const title = button.dataset.guideTitle || "Hướng dẫn lấy thuốc";
      guideDetailTitleEl.textContent = GUIDE_TITLES.has(title) ? title : "Hướng dẫn lấy thuốc";
      showScreen("guideDetail");
    });
  });

  document.querySelectorAll("[data-digit]").forEach((button) => {
    button.addEventListener("click", () => appendMedicineDigit(button.dataset.digit || ""));
  });

  document.querySelector("[data-action='delete']").addEventListener("click", deleteMedicineDigit);
  document.querySelector("[data-action='confirm']").addEventListener("click", confirmManualMedicineCode);
  updateMedicineCodeDisplay();
}

function setupOptionalIcons() {
  document.querySelectorAll("[data-optional-icon]").forEach((image) => {
    const hideMissingIcon = () => {
      image.hidden = true;
    };
    image.addEventListener("error", hideMissingIcon, { once: true });
    if (image.complete && image.naturalWidth === 0) {
      hideMissingIcon();
    }
  });
}

function setupSpeechSynthesisWarmup() {
  if (!("speechSynthesis" in window)) {
    return;
  }

  primeSpeechSynthesis();
  window.speechSynthesis.addEventListener?.("voiceschanged", primeSpeechSynthesis);

  const warmupOnUserGesture = () => primeSpeechSynthesis({ speak: true });
  window.addEventListener("pointerdown", warmupOnUserGesture, { once: true, passive: true });
  window.addEventListener("keydown", warmupOnUserGesture, { once: true });
}

function primeSpeechSynthesis({ speak = false } = {}) {
  if (!("speechSynthesis" in window)) {
    return;
  }

  const voices = window.speechSynthesis.getVoices();
  state.voicePreferredVoice = selectVietnameseVoice(voices);
  if (!speak || state.voiceWarmupDone) {
    return;
  }

  state.voiceWarmupDone = true;
  const warmupUtterance = createVoiceUtterance(" ");
  warmupUtterance.volume = 0;
  window.speechSynthesis.speak(warmupUtterance);
}

function selectVietnameseVoice(voices) {
  if (!Array.isArray(voices) || voices.length === 0) {
    return hasVietnameseVoice(state.voicePreferredVoice) ? state.voicePreferredVoice : null;
  }

  return (
    voices.find((voice) => voice.lang?.toLowerCase() === "vi-vn" && voice.localService) ||
    voices.find((voice) => voice.lang?.toLowerCase().startsWith("vi") && voice.localService) ||
    voices.find((voice) => voice.lang?.toLowerCase() === "vi-vn") ||
    voices.find((voice) => voice.lang?.toLowerCase().startsWith("vi")) ||
    (hasVietnameseVoice(state.voicePreferredVoice) ? state.voicePreferredVoice : null) ||
    null
  );
}

function hasVietnameseVoice(voice) {
  return Boolean(voice?.lang?.toLowerCase().startsWith("vi"));
}

function createVoiceUtterance(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = VOICE_UTTERANCE_CONFIG.lang;
  utterance.rate = VOICE_UTTERANCE_CONFIG.rate;
  utterance.pitch = VOICE_UTTERANCE_CONFIG.pitch;
  if (state.voicePreferredVoice) {
    utterance.voice = state.voicePreferredVoice;
  }
  return utterance;
}

function cancelSpeechSynthesis() {
  if (
    "speechSynthesis" in window &&
    (window.speechSynthesis.speaking || window.speechSynthesis.pending)
  ) {
    window.speechSynthesis.cancel();
  }
}

function updateClock() {
  const now = new Date();
  clockTextEl.textContent = new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(now);
  dateTextEl.textContent = new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(now);
  clockTextEl.setAttribute(
    "aria-label",
    new Intl.DateTimeFormat("vi-VN", {
      weekday: "long",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(now),
  );
}

function showScreen(name) {
  Object.values(screens).forEach((screen) => screen.classList.remove("is-active"));
  screens[name].classList.add("is-active");
  state.activeScreen = name;
  if (name === "doctor") {
    loadArduinoStatus({ refresh: true });
  }
}

async function returnHome() {
  if (state.activeScreen === "medicinePickup" && state.currentDispenseSession?.status === "open") {
    const closed = await completeCurrentMedicineDispense({ navigateHome: false });
    if (!closed) return;
  }
  if (state.activeScreen === "doctor") {
    const closed = await homeAllDoctorDoors();
    if (!closed) return;
  }
  stopQrScanner();
  abortDispenseRequest();
  stopDispenseStatusPolling();
  stopPickupCountdown();
  clearMedicineErrors();
  state.currentMedicineOrder = null;
  state.currentDispenseSession = null;
  state.medicineDispenseBusy = false;
  closeDoctorSettings();
  showScreen("home");
}

function initDoctorPanel() {
  state.doctorSettings = loadDoctorSettings();
  applyDoctorSettingsToForm();
  renderDoctorStatus();
  renderDoctorMedicineList();

  doctorLoginFormEl.addEventListener("submit", handleDoctorLogin);
  doctorLoginUsernameInputEl.addEventListener("input", clearDoctorLoginError);
  doctorLoginPasswordInputEl.addEventListener("input", clearDoctorLoginError);
  doctorSettingsButtonEl.addEventListener("click", openDoctorSettings);
  closeSettingsButtonEl.addEventListener("click", closeDoctorSettings);
  settingsPanelEl.addEventListener("click", (event) => {
    if (event.target === settingsPanelEl) {
      closeDoctorSettings();
    }
  });
  doctorSettingsFormEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const nextSettings = collectDoctorSettingsFromForm();
    clearDoctorSettingsError();
    state.doctorSettings = nextSettings;
    saveDoctorSettings(state.doctorSettings);
    const arduinoSettingsSaved = await syncArduinoSettings(nextSettings);
    if (!arduinoSettingsSaved) {
      return;
    }
    renderDoctorStatus();
    closeDoctorSettings();
  });
  volumeRangeEl.addEventListener("input", updateVolumeLabel);
  apiProviderSelectEl.addEventListener("change", () => {
    populateApiModelOptions(apiProviderSelectEl.value);
  });

  excelUploadButtonEl.addEventListener("click", () => excelUploadInputEl.click());
  excelUploadInputEl.addEventListener("change", handleExcelUpload);
  excelTemplateDownloadButtonEl.addEventListener("click", downloadExcelTemplate);
  trayDoorButtons.forEach((button) => {
    button.addEventListener("click", () => toggleDoctorTrayDoor(Number(button.dataset.trayDoor)));
  });
  homeDoorsButtonEl?.addEventListener("click", homeAllDoctorDoors);
  calibrateTrayButtonEl?.addEventListener("click", () => {
    if (state.doctorTrayCalibrated && state.doctorTrayEnabled) releaseTrayForAlignment();
    else calibrateTrayAtK1();
  });
  homeTrayButtonEl?.addEventListener("click", moveDoctorTrayHome);
  rotateTrayButtonEl.addEventListener("click", rotateDoctorTray);

  loadDoctorData();
  loadArduinoStatus({ refresh: true });
  startArduinoStatusPolling();
}

function getDefaultDoctorSettings() {
  return {
    apiProvider: "chatgpt",
    apiModel: "gpt-4o-mini",
    apiBaseUrl: "",
    volume: 70,
    arduinoPort: "",
    arduinoBaudRate: 9600,
    arduinoTimeout: 30000,
  };
}

function loadDoctorSettings() {
  const defaults = getDefaultDoctorSettings();
  try {
    const saved = window.localStorage.getItem(DOCTOR_SETTINGS_STORAGE_KEY);
    if (!saved) {
      return defaults;
    }
    // Drop credentials saved by older versions; they now live only in the server's .env.
    const { apiKey, doctorUsername, doctorPassword, ...rest } = JSON.parse(saved);
    return { ...defaults, ...rest };
  } catch (error) {
    console.warn("Cannot load doctor settings", error);
    return defaults;
  }
}

function saveDoctorSettings(settings) {
  try {
    window.localStorage.setItem(DOCTOR_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch (error) {
    console.warn("Cannot save doctor settings", error);
  }
}

function applyDoctorSettingsToForm() {
  const settings = state.doctorSettings || getDefaultDoctorSettings();
  const provider = API_MODEL_OPTIONS[settings.apiProvider] ? settings.apiProvider : "chatgpt";
  apiProviderSelectEl.value = provider;
  populateApiModelOptions(provider, settings.apiModel);
  apiBaseUrlInputEl.value = settings.apiBaseUrl || "";
  volumeRangeEl.value = String(settings.volume ?? 70);
  arduinoPortInputEl.value = settings.arduinoPort || "";
  arduinoBaudRateInputEl.value = "9600";
  arduinoTimeoutInputEl.value = String(settings.arduinoTimeout || 30000);
  clearDoctorSettingsError();
  updateVolumeLabel();
}

function collectDoctorSettingsFromForm() {
  return {
    apiProvider: apiProviderSelectEl.value,
    apiModel: apiModelSelectEl.value,
    apiBaseUrl: apiBaseUrlInputEl.value.trim(),
    volume: Number(volumeRangeEl.value || 70),
    arduinoPort: arduinoPortInputEl.value.trim(),
    arduinoBaudRate: 9600,
    arduinoTimeout: Number(arduinoTimeoutInputEl.value || 30000),
  };
}

function openDoctorArea() {
  clearDoctorLoginError();
  if (state.doctorAuthenticated) {
    showScreen("doctor");
    return;
  }
  doctorLoginFormEl.reset();
  showScreen("doctorLogin");
  doctorLoginUsernameInputEl.focus();
}

async function handleDoctorLogin(event) {
  event.preventDefault();
  const username = doctorLoginUsernameInputEl.value.trim();
  const password = doctorLoginPasswordInputEl.value;
  let detail = "Tên đăng nhập hoặc mật khẩu không đúng.";
  try {
    const response = await fetch("/robot/api/doctor/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (response.ok) {
      state.doctorAuthenticated = true;
      clearDoctorLoginError();
      doctorLoginFormEl.reset();
      showScreen("doctor");
      return;
    }
    if (response.status === 503) {
      detail = "Chưa cấu hình tài khoản bác sĩ trên server (DOCTOR_PASSWORD trong file .env).";
    }
  } catch (error) {
    console.warn("Doctor login request failed", error);
    detail = "Không kết nối được server để đăng nhập.";
  }
  doctorLoginErrorEl.textContent = detail;
  doctorLoginErrorEl.hidden = false;
  doctorLoginPasswordInputEl.value = "";
  doctorLoginPasswordInputEl.focus();
}

function clearDoctorLoginError() {
  doctorLoginErrorEl.textContent = "";
  doctorLoginErrorEl.hidden = true;
}

function clearDoctorSettingsError() {
  if (!doctorSettingsErrorEl) {
    return;
  }
  doctorSettingsErrorEl.textContent = "";
  doctorSettingsErrorEl.hidden = true;
}

function updateVolumeLabel() {
  volumeValueEl.textContent = `${volumeRangeEl.value || 0}%`;
}

function populateApiModelOptions(provider, selectedModel = "") {
  const options = API_MODEL_OPTIONS[provider] || API_MODEL_OPTIONS.chatgpt;
  apiModelSelectEl.innerHTML = options
    .map((option) => `<option value="${option.value}">${option.label}</option>`)
    .join("");
  const modelExists = options.some((option) => option.value === selectedModel);
  apiModelSelectEl.value = modelExists ? selectedModel : options[0].value;
}

function getDoctorDoorState(index) {
  if (index === 2) return "CLOSED";
  const door = state.doctorDoorStates[index];
  return String(door?.state || "UNKNOWN").toUpperCase();
}

function getDoorStateLabel(doorState) {
  if (doorState === "CLOSED") return "Đóng";
  if (doorState === "OPEN") return "Mở";
  if (doorState === "BETWEEN") return "Giữa hành trình";
  if (doorState === "CONFLICT") return "Lỗi CTHT";
  return "Chưa rõ";
}

function getDoctorDoorName(index) {
  return index === 2 ? "Cửa vật tư y tế" : `Cửa ${index + 1}`;
}

function getTrayCalibrationBlockReason() {
  if (!state.doctorArduinoConnected) {
    return "Arduino chưa sẵn sàng hoặc chưa kết nối.";
  }
  if (state.doctorTrayCalibrated) {
    return "Mốc K1 đã được xác nhận.";
  }
  if (state.doctorArduinoBusy || state.doctorTrayBusy || state.doctorHomeTrayBusy || state.doctorTrayHardwareBusy) {
    return "Hệ thống đang xử lý lệnh phần cứng. Vui lòng chờ.";
  }

  return "";
}

function renderArduinoInlineStatus() {
  const port = state.doctorArduinoPort || state.doctorSettings?.arduinoPort?.trim();
  if (!state.doctorArduinoConfigured) {
    doctorArduinoStatusEl.textContent = port ? `Arduino: ${port} · chờ kết nối` : "Arduino: chờ cấu hình port";
    return;
  }
  if (state.doctorArduinoConnected) {
    const suffix = state.doctorArduinoBusy ? "đang xử lý" : state.doctorArduinoConnectionState === "hardware_error" ? "lỗi CTHT" : "sẵn sàng";
    doctorArduinoStatusEl.textContent = `Arduino: ${port || "đã cấu hình"} · 9600 · ${suffix}`;
    return;
  }
  doctorArduinoStatusEl.textContent =
    state.doctorArduinoConnectionState === "connecting"
      ? `Arduino: ${port || "đã cấu hình"} · đang kết nối`
      : `Arduino: ${port || "đã cấu hình"} · lỗi kết nối`;
}

function openDoctorSettings() {
  applyDoctorSettingsToForm();
  settingsPanelEl.hidden = false;
  apiProviderSelectEl.focus();
}

function closeDoctorSettings() {
  if (settingsPanelEl) {
    settingsPanelEl.hidden = true;
    clearDoctorSettingsError();
  }
}

function renderDoctorStatus() {
  trayDoorButtons.forEach((button, index) => {
    const doorState = getDoctorDoorState(index);
    const isOpen = doorState === "OPEN";
    const isClosed = doorState === "CLOSED";
    const isBetween = doorState === "BETWEEN";
    const isConflict = doorState === "CONFLICT";
    const isKnown = isOpen || isClosed || isBetween || isConflict;
    const isBusy = button.classList.contains("is-busy");
    const label = index === 2 ? "cửa vật tư y tế" : `cửa khay ${index + 1}`;
    const isSupplyDoorLocked = index === 2;
    const canControl = !isSupplyDoorLocked && state.doctorArduinoConnected && !isConflict && (isOpen || isClosed || isBetween);
    button.classList.toggle("is-active", isOpen);
    button.classList.toggle("is-disabled", !canControl);
    button.setAttribute("aria-pressed", String(isOpen));
    button.setAttribute("aria-label", isSupplyDoorLocked ? `${label} đang tạm khóa và được giả lập là đóng` : `${isOpen || isBetween ? "Đóng" : "Mở"} ${label}`);
    button.disabled = isBusy || !canControl;
    const status = button.querySelector("strong");
    if (status) {
      status.textContent = isBusy ? "Đang xử lý" : getDoorStateLabel(doorState);
    }
    const hint = button.querySelector("small");
    if (hint) {
      hint.textContent = isSupplyDoorLocked
        ? "Tạm khóa"
        : isBusy
        ? "Vui lòng chờ"
        : !state.doctorArduinoConnected
          ? "Chờ Arduino"
          : isConflict
            ? "Kiểm tra CTHT"
            : isBetween
              ? "Chạm để đóng"
              : isOpen
                ? "Chạm để đóng"
                : isClosed
                  ? "Chạm để mở"
                  : isKnown
                    ? "Chờ trạng thái"
                    : "Đang đọc";
    }
  });

  if (homeDoorsButtonEl) {
    homeDoorsButtonEl.disabled = state.doctorDoorHomeBusy || !state.doctorArduinoConnected;
    homeDoorsButtonEl.textContent = state.doctorDoorHomeBusy ? "Đang đóng..." : "Đóng tất cả";
  }

  const allDoorsClosed = state.doctorDoorStates.every((door) => String(door.state).toUpperCase() === "CLOSED");
  const trayCommandBusy = state.doctorArduinoBusy || state.doctorTrayBusy || state.doctorHomeTrayBusy || state.doctorTrayHardwareBusy;
  const canMoveTray = state.doctorArduinoConnected && state.doctorTrayCalibrated && state.doctorTrayEnabled && allDoorsClosed && !trayCommandBusy;
  rotateTrayButtonEl.classList.toggle("is-busy", state.doctorTrayBusy);
  rotateTrayButtonEl.disabled = !canMoveTray;
  rotateTrayButtonEl.setAttribute("aria-busy", String(state.doctorTrayBusy));
  rotateTrayButtonEl.querySelector("strong").textContent = state.doctorTrayBusy ? "Đang xoay..." : "Xoay khay";
  rotateTrayButtonEl.setAttribute("aria-label", state.doctorTrayBusy ? "Đang xoay khay" : "Xoay khay");
  if (homeTrayButtonEl) {
    homeTrayButtonEl.classList.toggle("is-busy", state.doctorHomeTrayBusy);
    homeTrayButtonEl.disabled = !canMoveTray;
    homeTrayButtonEl.setAttribute("aria-busy", String(state.doctorHomeTrayBusy));
    homeTrayButtonEl.querySelector("strong").textContent = state.doctorHomeTrayBusy ? "Đang về..." : "Về vị trí 1";
    homeTrayButtonEl.setAttribute("aria-label", state.doctorHomeTrayBusy ? "Đang về vị trí 1" : "Về vị trí 1");
  }
  if (doctorTrayPositionBadgeEl) {
    doctorTrayPositionBadgeEl.textContent = state.doctorTrayCalibrated ? String(state.doctorTrayPosition) : "?";
  }
  doctorTrayPositionStatusEl.textContent = state.doctorTrayCalibrated
    ? `Vị trí ${state.doctorTrayPosition} trong ${DOCTOR_TRAY_POSITION_MAX}`
    : "Cần xác nhận mốc K1";
  const calibrationBlockReason = getTrayCalibrationBlockReason();
  trayCalibrationCardEl.dataset.calibrated = String(state.doctorTrayCalibrated);
  trayCalibrationCardEl.dataset.blocked = String(Boolean(calibrationBlockReason));
  const trayLocked = state.doctorTrayCalibrated && state.doctorTrayEnabled;
  trayCalibrationTitleEl.textContent = trayLocked ? "Đã khóa khay tại mốc K1" : "Khay đang thả · chưa xác nhận K1";
  trayCalibrationHintEl.textContent = trayLocked && state.doctorArduinoConnected
    ? `Driver đang giữ khay; firmware báo vị trí ${state.doctorTrayPosition}.`
    : calibrationBlockReason || "Xoay chậm khay bằng tay đến K1 rồi nhấn xác nhận để khóa.";
  calibrateTrayButtonEl.disabled = trayLocked ? trayCommandBusy : Boolean(calibrationBlockReason);
  calibrateTrayButtonEl.textContent = trayLocked
    ? "Căn chỉnh lại"
    : trayCommandBusy
      ? "Đang xử lý..."
      : "Xác nhận K1";
  calibrateTrayButtonEl.setAttribute("aria-describedby", "trayCalibrationHint");
  calibrateTrayButtonEl.title = calibrationBlockReason || "Xác nhận cơ cấu đang ở đúng mốc K1";
  renderArduinoInlineStatus();
}

async function handleExcelUpload() {
  const file = excelUploadInputEl.files?.[0];
  clearDoctorUploadError();
  if (!file) {
    excelUploadStatusEl.textContent = "Chưa chọn file tra cứu";
    return;
  }
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    showDoctorUploadError("Chỉ hỗ trợ file .xlsx đúng mẫu.");
    excelUploadInputEl.value = "";
    return;
  }
  state.doctorUploadBusy = true;
  excelUploadButtonEl.disabled = true;
  excelUploadStatusEl.textContent = `Đang upload: ${file.name}`;
  try {
    const response = await fetch(`${MEDICINE_UPLOAD_URL}?filename=${encodeURIComponent(file.name)}`, {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      },
      body: await file.arrayBuffer(),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(data.errors) && data.errors.length ? data.errors.join("\n") : data.detail;
      throw new Error(detail || "Upload file Excel không thành công.");
    }
    state.medicineOrders = Array.isArray(data.orders) ? data.orders : [];
    state.doctorTrayPosition = Number(data.current_setup_slot || 1);
    excelUploadStatusEl.textContent = data.message || `Đã upload: ${file.name}`;
    renderDoctorStatus();
    renderDoctorMedicineList();
  } catch (error) {
    showDoctorUploadError(error.message || "Upload file Excel không thành công.");
    await loadDoctorData();
  } finally {
    state.doctorUploadBusy = false;
    excelUploadButtonEl.disabled = false;
    excelUploadInputEl.value = "";
  }
}

async function toggleDoctorTrayDoor(index) {
  if (!Number.isInteger(index) || index < 0 || index > 2) {
    return;
  }
  const button = trayDoorButtons[index];
  const doorName = index === 2 ? "cửa vật tư y tế" : `cửa khay ${index + 1}`;
  if (index === 2) {
    showDoctorUploadError("Cửa vật tư y tế đang tạm khóa và được giả lập là đóng.");
    return;
  }
  const doorState = getDoctorDoorState(index);
  if (!state.doctorArduinoConnected) {
    showDoctorUploadError("Arduino chưa sẵn sàng hoặc chưa kết nối.");
    return;
  }
  if (doorState === "CONFLICT") {
    showDoctorUploadError(`${doorName} đang lỗi CTHT. Kiểm tra công tắc mở/đóng trước khi chạy motor.`);
    return;
  }
  const action = doorState === "CLOSED" ? "OPEN" : doorState === "OPEN" || doorState === "BETWEEN" ? "CLOSE" : "";
  if (!action) {
    showDoctorUploadError(`Chưa đọc được trạng thái ${doorName}. Vui lòng chờ Arduino cập nhật.`);
    await loadArduinoStatus({ refresh: true });
    return;
  }
  button.classList.add("is-busy");
  button.disabled = true;
  renderDoctorStatus();
  try {
    const response = await fetchWithTimeout(ARDUINO_DOOR_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ door: index + 1, action }),
    }, HARDWARE_REQUEST_TIMEOUT_MS);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Không gửi được lệnh ${doorName}.`);
    }
    applyArduinoStatus(data.status || {});
    clearDoctorUploadError();
  } catch (error) {
    showDoctorUploadError(error.message || `Không gửi được lệnh ${doorName}.`);
    await loadArduinoStatus({ refresh: true });
  } finally {
    button.classList.remove("is-busy");
    button.disabled = false;
    renderDoctorStatus();
  }
}

async function homeAllDoctorDoors() {
  if (!state.doctorArduinoConnected || state.doctorDoorHomeBusy) {
    return false;
  }
  state.doctorDoorHomeBusy = true;
  homeDoorsButtonEl?.classList.add("is-busy");
  renderDoctorStatus();
  try {
    const response = await fetchWithTimeout(
      ARDUINO_HOME_URL,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      },
      HARDWARE_HOME_TIMEOUT_MS,
    );
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không đóng tất cả cửa được.");
    }
    applyArduinoStatus(data.status || {});
    clearDoctorUploadError();
    return true;
  } catch (error) {
    showDoctorUploadError(error.message || "Không đóng tất cả cửa được.");
    await loadArduinoStatus({ refresh: true });
    return false;
  } finally {
    state.doctorDoorHomeBusy = false;
    homeDoorsButtonEl?.classList.remove("is-busy");
    renderDoctorStatus();
  }
}

async function calibrateTrayAtK1() {
  const blockReason = getTrayCalibrationBlockReason();
  if (blockReason) {
    showDoctorUploadError(blockReason);
    renderDoctorStatus();
    return false;
  }
  state.doctorTrayBusy = true;
  renderDoctorStatus();
  try {
    const response = await fetchWithTimeout(
      ARDUINO_TRAY_CALIBRATE_URL,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ slot: 1 }) },
      HARDWARE_REQUEST_TIMEOUT_MS,
    );
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Không xác nhận được mốc K1.");
    applyArduinoStatus(data.status || {});
    clearDoctorUploadError();
    return true;
  } catch (error) {
    showDoctorUploadError(error.message || "Không xác nhận được mốc K1.");
    await loadArduinoStatus({ refresh: true });
    return false;
  } finally {
    state.doctorTrayBusy = false;
    renderDoctorStatus();
  }
}

async function releaseTrayForAlignment() {
  if (!state.doctorArduinoConnected || state.doctorTrayBusy) return false;
  state.doctorTrayBusy = true;
  renderDoctorStatus();
  try {
    const response = await fetchWithTimeout(
      ARDUINO_TRAY_RELEASE_URL,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) },
      HARDWARE_REQUEST_TIMEOUT_MS,
    );
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Không thả được khay.");
    applyArduinoStatus(data.status || {});
    clearDoctorUploadError();
    return true;
  } catch (error) {
    showDoctorUploadError(error.message || "Không thả được khay.");
    await loadArduinoStatus({ refresh: true });
    return false;
  } finally {
    state.doctorTrayBusy = false;
    renderDoctorStatus();
  }
}

function downloadExcelTemplate() {
  const link = document.createElement("a");
  link.href = MEDICINE_TEMPLATE_URL;
  link.download = "mau-tra-cuu-thuoc.xlsx";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

async function moveDoctorTrayHome() {
  if (state.doctorHomeTrayBusy || state.doctorTrayBusy) {
    return;
  }
  state.doctorHomeTrayBusy = true;
  renderDoctorStatus();
  try {
    await sendSetupTrayCommand(1);
    clearDoctorUploadError();
  } catch (error) {
    showDoctorUploadError(error.message || "Không đưa khay về vị trí 1 được.");
  } finally {
    state.doctorHomeTrayBusy = false;
    renderDoctorStatus();
  }
}

async function rotateDoctorTray() {
  if (state.doctorTrayBusy || state.doctorHomeTrayBusy) {
    return;
  }
  const blocked = getUncheckedOrdersAtSlot(state.doctorTrayPosition);
  if (blocked.length) {
    showDoctorUploadError(
      `Cần tick setup xong ${blocked.map((order) => order.position).join(", ")} trước khi xoay khay.`,
    );
    return;
  }
  state.doctorTrayBusy = true;
  renderDoctorStatus();
  const nextSlot = state.doctorTrayPosition >= DOCTOR_TRAY_POSITION_MAX ? 1 : state.doctorTrayPosition + 1;
  try {
    await sendSetupTrayCommand(nextSlot);
    clearDoctorUploadError();
  } catch (error) {
    showDoctorUploadError(error.message || "Không xoay khay được.");
  } finally {
    state.doctorTrayBusy = false;
    renderDoctorStatus();
  }
}

function renderDoctorMedicineList() {
  const renderRows = (trayNumber) => {
    const rows = state.medicineOrders
      .filter((order) => Number(order.tray) === trayNumber)
      .sort((a, b) => Number(a.slot) - Number(b.slot));
    const body = rows.length
      ? `
          <div class="doctor-medicine-list" role="list" aria-label="Danh sách thuốc khay ${trayNumber}">
            ${rows
              .map(
                (item) => `
                  <div class="doctor-medicine-row" role="listitem" data-order-status="${escapeHtml(item.dispense_status || "pending_setup")}">
                    <span class="order-index">${escapeHtml(item.position)}</span>
                    <span class="customer-name">
                      <strong>${escapeHtml(item.name)}</strong>
                      <small>${escapeHtml(item.id)} · ${escapeHtml(item.bed)} · Cửa ${escapeHtml(item.door)}</small>
                    </span>
                    <span class="order-controls">
                      <span class="order-state-badge">${escapeHtml(getOrderStatusLabel(item.dispense_status))}</span>
                      <input class="setup-check" aria-label="Setup xong ${escapeHtml(item.position)}" type="checkbox" data-position="${escapeHtml(item.position)}" ${item.setup_done ? "checked" : ""} ${["dispensing", "dispensed", "interrupted"].includes(item.dispense_status) ? "disabled" : ""} />
                      ${["dispensed", "interrupted"].includes(item.dispense_status) ? `<button class="order-resolve-button" type="button" data-resolve-patient="${escapeHtml(item.id)}" data-resolve-action="ALLOW_RETRY">Cho lấy lại</button>` : ""}
                      ${item.dispense_status === "interrupted" ? `<button class="order-resolve-button" type="button" data-resolve-patient="${escapeHtml(item.id)}" data-resolve-action="MARK_DISPENSED">Đã cấp</button>` : ""}
                    </span>
                  </div>
                `,
              )
              .join("")}
          </div>
        `
      : `<p class="doctor-empty-list">Chưa có đơn thuốc cho khay ${trayNumber}.</p>`;
    return `
      <section class="doctor-medicine-column" aria-label="Khay ${trayNumber}">
        <header class="doctor-medicine-column-title">
          <strong>Khay ${trayNumber}</strong>
          <span>${rows.length} đơn</span>
        </header>
        ${body}
      </section>
    `;
  };

  doctorMedicineRowsEl.innerHTML = [1, 2].map(renderRows).join("");

  doctorMedicineRowsEl.querySelectorAll("[data-position]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => updateSetupCheck(checkbox.dataset.position, checkbox.checked, checkbox));
  });
  doctorMedicineRowsEl.querySelectorAll("[data-resolve-patient]").forEach((button) => {
    button.addEventListener("click", () => resolveDispenseOrder(button.dataset.resolvePatient, button.dataset.resolveAction));
  });
}

function getOrderStatusLabel(status) {
  return ({
    pending_setup: "Chờ setup",
    ready: "Sẵn sàng",
    dispensing: "Đang cấp",
    dispensed: "Đã lấy",
    interrupted: "Cần xác minh",
  })[status] || "Chưa rõ";
}

async function resolveDispenseOrder(patientId, action) {
  try {
    const response = await fetch(MEDICINE_DISPENSE_RESOLVE_URL, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id: patientId, action }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Không xử lý được trạng thái đơn.");
    await loadDoctorData();
    clearDoctorUploadError();
  } catch (error) {
    showDoctorUploadError(error.message || "Không xử lý được trạng thái đơn.");
  }
}

async function loadDoctorData() {
  try {
    const response = await fetch(MEDICINE_ORDERS_URL, { cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không tải được danh sách đơn thuốc.");
    }
    state.medicineOrders = Array.isArray(data.orders) ? data.orders : [];
    state.doctorTrayPosition = Number(data.current_setup_slot || 1);
    excelUploadStatusEl.textContent = data.uploaded_file_name
      ? `Đang dùng: ${data.uploaded_file_name}`
      : "Chưa chọn file tra cứu";
    renderDoctorStatus();
    renderDoctorMedicineList();
  } catch (error) {
    showDoctorUploadError(error.message || "Không tải được danh sách đơn thuốc.");
  }
}

function startArduinoStatusPolling() {
  if (state.doctorStatusPollTimer) {
    return;
  }
  state.doctorStatusPollTimer = window.setInterval(() => {
    if (state.activeScreen === "doctor") {
      loadArduinoStatus({ refresh: true });
    }
  }, ARDUINO_STATUS_POLL_MS);
}

function applyArduinoStatus(arduino) {
  const payload = arduino || {};
  state.doctorArduinoConfigured = Boolean(payload.configured);
  state.doctorArduinoConnected = Boolean(payload.connected);
  state.doctorArduinoBusy = Boolean(payload.busy);
  state.doctorTrayCalibrated = Boolean(payload.tray_calibrated);
  state.doctorTrayEnabled = Boolean(payload.tray_enabled);
  state.doctorTrayHardwareBusy = Boolean(payload.tray_busy);
  if (Number.isInteger(Number(payload.tray_position)) && Number(payload.tray_position) >= 1 && Number(payload.tray_position) <= 8) {
    state.doctorTrayPosition = Number(payload.tray_position);
  }
  state.doctorArduinoConnectionState = payload.connection_state || "unconfigured";
  state.doctorArduinoPort = payload.port || "";
  if (Array.isArray(payload.door_states) && payload.door_states.length >= 3) {
    state.doctorDoorStates = payload.door_states.slice(0, 3).map((door, index) => ({
      door: Number(door.door || index + 1),
      state: String(door.state || "UNKNOWN").toUpperCase(),
    }));
    state.doctorDoorStates[2] = { door: 3, state: "CLOSED" };
  }
  renderDoctorStatus();
}

async function loadArduinoStatus({ refresh = false } = {}) {
  try {
    const response = await fetch(`${ARDUINO_STATUS_URL}${refresh ? "?refresh=1" : ""}`, { cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không đọc được trạng thái Arduino.");
    }
    applyArduinoStatus(data.arduino || {});
  } catch (error) {
    state.doctorArduinoConnected = false;
    state.doctorArduinoConnectionState = "error";
    doctorArduinoStatusEl.textContent = "Arduino: lỗi trạng thái";
    renderDoctorStatus();
  }
}

async function syncArduinoSettings(settings) {
  try {
    const response = await fetch(ARDUINO_SETTINGS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        port: settings.arduinoPort,
        baud_rate: settings.arduinoBaudRate,
        timeout_ms: settings.arduinoTimeout,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không lưu được cấu hình Arduino.");
    }
    applyArduinoStatus(data.arduino || {});
    await loadArduinoStatus({ refresh: true });
    return true;
  } catch (error) {
    doctorSettingsErrorEl.textContent = error.message || "Không lưu được cấu hình Arduino.";
    doctorSettingsErrorEl.hidden = false;
    return false;
  }
}

function showDoctorUploadError(message) {
  if (!excelUploadErrorEl) {
    return;
  }
  excelUploadErrorEl.textContent = message;
  excelUploadErrorEl.hidden = false;
}

function clearDoctorUploadError() {
  if (!excelUploadErrorEl) {
    return;
  }
  excelUploadErrorEl.textContent = "";
  excelUploadErrorEl.hidden = true;
}

async function sendSetupTrayCommand(slot) {
  const response = await fetch(MEDICINE_SETUP_TRAY_URL, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slot }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Không gửi được lệnh vị trí khay.");
  }
  state.doctorTrayPosition = Number(data.slot || slot);
  return data;
}

function getUncheckedOrdersAtSlot(slot) {
  return state.medicineOrders.filter(
    (order) => Number(order.slot) === Number(slot) && !order.setup_done,
  );
}

async function updateSetupCheck(position, done, checkbox) {
  const order = state.medicineOrders.find((item) => item.position === position);
  if (order) {
    order.setup_done = done;
    order.dispense_status = done ? "ready" : "pending_setup";
  }
  try {
    const response = await fetch(MEDICINE_SETUP_CHECK_URL, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position, done }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không cập nhật được checklist.");
    }
    clearDoctorUploadError();
    renderDoctorMedicineList();
  } catch (error) {
    if (order) {
      order.setup_done = !done;
      order.dispense_status = order.setup_done ? "ready" : "pending_setup";
    }
    checkbox.checked = !done;
    showDoctorUploadError(error.message || "Không cập nhật được checklist.");
    renderDoctorMedicineList();
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function validateMedicineOrder(order, expectedPatientId = "") {
  const errorResult = (message) => ({
    ok: false,
    order: null,
    message: message || "Dữ liệu đơn thuốc không đầy đủ. Vui lòng liên hệ nhân viên y tế.",
  });
  if (!order || typeof order !== "object" || Array.isArray(order)) {
    return errorResult();
  }

  const id = String(order.id || order.patient_id || "").trim();
  const patientId = String(order.patient_id || order.id || "").trim();
  if (!id || !patientId || id !== patientId) {
    return errorResult("Dữ liệu đơn thuốc thiếu ID bệnh nhân hợp lệ.");
  }
  const expectedId = String(expectedPatientId || "").trim();
  if (expectedId && id !== expectedId) {
    return errorResult("Đơn thuốc trả về không khớp với ID bệnh nhân đang xử lý.");
  }

  const requiredTextFields = ["name", "bed", "position", "prescription", "instructions"];
  const normalizedText = {};
  for (const key of requiredTextFields) {
    const value = String(order[key] || "").trim();
    if (!value) {
      return errorResult();
    }
    normalizedText[key] = value;
  }

  const position = normalizedText.position.toUpperCase();
  const positionMatch = /^K([12])_([1-8])$/.exec(position);
  const tray = Number(order.tray);
  const slot = Number(order.slot);
  const door = Number(order.door);
  if (
    !positionMatch ||
    !Number.isInteger(tray) ||
    !Number.isInteger(slot) ||
    !Number.isInteger(door) ||
    tray !== Number(positionMatch[1]) ||
    ![1, 2].includes(door) ||
    slot !== Number(positionMatch[2])
  ) {
    return errorResult("Vị trí khay của đơn thuốc không hợp lệ hoặc không nhất quán.");
  }

  return {
    ok: true,
    message: "",
    order: {
      ...order,
      id,
      patient_id: id,
      ...normalizedText,
      position,
      tray,
      slot,
      door,
      setup_done: Boolean(order.setup_done),
      dispense_status: String(order.dispense_status || (order.setup_done ? "ready" : "pending_setup")),
      setup_done: Boolean(order.setup_done),
    },
  };
}

function clearMedicineErrors() {
  medicineErrorEl.hidden = true;
  medicineErrorEl.textContent = "";
  manualErrorEl.hidden = true;
  manualErrorEl.textContent = "";
  if (medicineConfirmErrorEl) {
    medicineConfirmErrorEl.hidden = true;
    medicineConfirmErrorEl.textContent = "";
  }
  if (medicinePickupErrorEl) {
    medicinePickupErrorEl.hidden = true;
    medicinePickupErrorEl.textContent = "";
  }
}

function showMedicineError(message) {
  medicineErrorEl.textContent = message;
  medicineErrorEl.hidden = false;
  showScreen("medicine");
}

function resetMedicineCode() {
  state.medicineCode = "";
  clearMedicineErrors();
  updateMedicineCodeDisplay();
}

function appendMedicineDigit(digit) {
  if (!/^\d$/.test(digit) || state.medicineCode.length >= 16) {
    return;
  }
  state.medicineCode += digit;
  clearMedicineErrors();
  updateMedicineCodeDisplay();
}

function deleteMedicineDigit() {
  state.medicineCode = state.medicineCode.slice(0, -1);
  updateMedicineCodeDisplay();
}

function updateMedicineCodeDisplay() {
  medicineCodeDisplayEl.textContent = state.medicineCode;
}

async function confirmManualMedicineCode() {
  if (!state.medicineCode) {
    manualErrorEl.textContent = "Vui lòng nhập mã lấy thuốc.";
    manualErrorEl.hidden = false;
    return;
  }
  await submitMedicineCode(state.medicineCode, "manual");
}

async function submitMedicineCode(rawCode, source) {
  const code = String(rawCode || "").trim();
  if (!code) {
    showMedicineError("Không đọc được mã lấy thuốc. Vui lòng thử lại.");
    return;
  }

  stopQrScanner();
  clearMedicineErrors();
  showScreen("loading");

  const abortController = new AbortController();
  state.dispenseAbortController = abortController;

  try {
    const response = await fetch(MEDICINE_LOOKUP_URL, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id: code, source }),
      signal: abortController.signal,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không tìm thấy đơn thuốc.");
    }
    if (data.ok !== true) {
      throw new Error(data.detail || "API không xác nhận đơn thuốc hợp lệ.");
    }
    const validation = validateMedicineOrder(data.order, code);
    if (!validation.ok) {
      throw new Error(validation.message);
    }
    state.currentMedicineOrder = validation.order;
    state.medicineCode = "";
    updateMedicineCodeDisplay();
    renderMedicineOrderDetails(validation.order);
    const ready = validation.order.setup_done && validation.order.dispense_status === "ready";
    confirmDispenseButtonEl.disabled = !ready;
    if (!ready) {
      medicineConfirmErrorEl.textContent = validation.order.dispense_status === "dispensed"
        ? "Đơn thuốc này đã được lấy. Vui lòng liên hệ bác sĩ nếu cần cấp lại."
        : validation.order.dispense_status === "interrupted"
          ? "Đơn thuốc đang cần bác sĩ xác minh."
          : "Đơn thuốc chưa được bác sĩ setup xong.";
      medicineConfirmErrorEl.hidden = false;
    }
    showScreen("medicineConfirm");
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }
    state.currentMedicineOrder = null;
    showMedicineError(error.message || "Không xác thực được ID bệnh nhân. Vui lòng thử lại.");
  } finally {
    if (state.dispenseAbortController === abortController) {
      state.dispenseAbortController = null;
    }
  }
}

function renderMedicineOrderDetails(order) {
  const current = order || state.currentMedicineOrder || {};
  const positionText = current.position || "--";
  medicineConfirmNameEl.textContent = current.name || "--";
  medicineConfirmBedEl.textContent = current.bed || "--";
  medicineConfirmPositionEl.textContent = positionText;
  medicineConfirmPrescriptionEl.textContent = current.prescription || "--";
  medicineConfirmInstructionsEl.textContent = current.instructions || "--";
  medicinePickupNameEl.textContent = current.name || "--";
  medicinePickupBedEl.textContent = current.bed || "--";
  medicinePickupPositionEl.textContent = positionText;
  medicinePickupInstructionsEl.textContent = current.instructions || "--";
  clearMedicineErrors();
}

async function dispenseCurrentMedicineOrder() {
  if (!state.currentMedicineOrder || state.medicineDispenseBusy) {
    return;
  }
  state.medicineDispenseBusy = true;
  confirmDispenseButtonEl.disabled = true;
  retryDispenseButtonEl.hidden = true;
  medicineConfirmErrorEl.hidden = true;
  try {
    const response = await fetchWithTimeout(MEDICINE_DISPENSE_URL, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id: state.currentMedicineOrder.id }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không mở được khay thuốc.");
    }
    if (data.ok !== true) {
      throw new Error(data.detail || "API không xác nhận thao tác lấy thuốc.");
    }
    const validation = validateMedicineOrder(data.order, state.currentMedicineOrder.id);
    if (!validation.ok) {
      throw new Error(validation.message);
    }
    state.currentMedicineOrder = validation.order;
    state.currentDispenseSession = data.session || null;
    renderMedicineOrderDetails(validation.order);
    closeVoiceMode();
    showScreen("medicinePickup");
    startPickupCountdown();
    startDispenseStatusPolling();
    return true;
  } catch (error) {
    medicineConfirmErrorEl.textContent = error.message || "Không mở được khay thuốc. Vui lòng thử lại.";
    medicineConfirmErrorEl.hidden = false;
    return false;
  } finally {
    state.medicineDispenseBusy = false;
    confirmDispenseButtonEl.disabled = false;
  }
}

async function completeCurrentMedicineDispense({ navigateHome = true } = {}) {
  if (!state.currentMedicineOrder || !state.currentDispenseSession?.id || state.medicineDispenseBusy) {
    return false;
  }
  state.medicineDispenseBusy = true;
  completeDispenseButtonEl.disabled = true;
  medicinePickupErrorEl.hidden = true;
  try {
    const response = await fetchWithTimeout(MEDICINE_DISPENSE_COMPLETE_URL, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.currentDispenseSession.id }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Không đóng được cửa khay.");
    }
    if (data.ok !== true) {
      throw new Error(data.detail || "API không xác nhận đã hoàn tất lấy thuốc.");
    }
    const validation = validateMedicineOrder(data.order, state.currentMedicineOrder.id);
    if (!validation.ok) {
      throw new Error(validation.message);
    }
    state.currentMedicineOrder = null;
    state.currentDispenseSession = data.session || { ...state.currentDispenseSession, status: "completed" };
    stopDispenseStatusPolling();
    stopPickupCountdown();
    if (navigateHome) {
      pickupCountdownLabelEl.textContent = "Đã đóng cửa";
      window.setTimeout(() => returnHome(), 900);
    }
    return true;
  } catch (error) {
    medicinePickupErrorEl.textContent = error.message || "Không đóng được cửa khay. Vui lòng thử lại.";
    medicinePickupErrorEl.hidden = false;
    retryDispenseButtonEl.hidden = false;
    return false;
  } finally {
    state.medicineDispenseBusy = false;
    completeDispenseButtonEl.disabled = false;
  }
}

function startPickupCountdown() {
  stopPickupCountdown();
  state.pickupCountdownWarned = false;
  updatePickupCountdown();
  state.pickupCountdownTimer = window.setInterval(updatePickupCountdown, 250);
}

function stopPickupCountdown() {
  if (state.pickupCountdownTimer) window.clearInterval(state.pickupCountdownTimer);
  state.pickupCountdownTimer = null;
  completeDispenseButtonEl.classList.remove("is-warning", "is-complete");
}

function updatePickupCountdown() {
  const deadline = Date.parse(state.currentDispenseSession?.auto_close_at || "");
  if (!Number.isFinite(deadline)) return;
  const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
  pickupCountdownValueEl.textContent = String(remaining);
  pickupCountdownLabelEl.textContent = remaining > 0 ? "Chạm để đóng ngay" : "Đang tự đóng...";
  completeDispenseButtonEl.classList.toggle("is-warning", remaining <= 5 && remaining > 0);
  completeDispenseButtonEl.disabled = remaining === 0 || state.medicineDispenseBusy;
  if (remaining <= 5 && remaining > 0 && !state.pickupCountdownWarned) {
    state.pickupCountdownWarned = true;
    if ("speechSynthesis" in window) {
      window.speechSynthesis.speak(new SpeechSynthesisUtterance("Cửa sẽ tự đóng sau năm giây."));
    }
  }
}

function startDispenseStatusPolling() {
  stopDispenseStatusPolling();
  state.dispenseStatusTimer = window.setInterval(pollDispenseStatus, 1000);
}

async function restoreActiveDispenseSession() {
  try {
    const sessionResponse = await fetch(MEDICINE_DISPENSE_STATUS_URL, { cache: "no-store" });
    if (!sessionResponse.ok) return;
    const sessionData = await sessionResponse.json();
    const session = sessionData.session;
    if (!session || !["open", "closing", "interrupted"].includes(session.status)) return;
    const orderResponse = await fetch(MEDICINE_LOOKUP_URL, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id: session.patient_id, source: "recovery" }),
    });
    const orderData = await orderResponse.json().catch(() => ({}));
    const validation = validateMedicineOrder(orderData.order, session.patient_id);
    if (!orderResponse.ok || !validation.ok) return;
    state.currentMedicineOrder = validation.order;
    state.currentDispenseSession = session;
    renderMedicineOrderDetails(validation.order);
    showScreen("medicinePickup");
    if (session.status === "interrupted") {
      medicinePickupErrorEl.textContent = "Phiên lấy thuốc bị gián đoạn. Vui lòng gọi nhân viên hỗ trợ.";
      medicinePickupErrorEl.hidden = false;
      retryDispenseButtonEl.hidden = false;
      completeDispenseButtonEl.disabled = true;
    } else {
      startPickupCountdown();
      startDispenseStatusPolling();
    }
  } catch (_error) {
    // Trang chu van dung duoc; backend watchdog se xu ly cua neu phien con mo.
  }
}

function stopDispenseStatusPolling() {
  if (state.dispenseStatusTimer) window.clearInterval(state.dispenseStatusTimer);
  state.dispenseStatusTimer = null;
}

async function pollDispenseStatus() {
  const sessionId = state.currentDispenseSession?.id;
  if (!sessionId) return;
  try {
    const response = await fetch(`${MEDICINE_DISPENSE_STATUS_URL}?session_id=${encodeURIComponent(sessionId)}`, { cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.session) return;
    state.currentDispenseSession = data.session;
    if (data.session.status === "completed") {
      stopDispenseStatusPolling();
      stopPickupCountdown();
      pickupCountdownValueEl.textContent = "✓";
      pickupCountdownLabelEl.textContent = "Đã đóng cửa";
      completeDispenseButtonEl.classList.add("is-complete");
      window.setTimeout(() => returnHome(), 900);
    } else if (data.session.status === "interrupted") {
      stopDispenseStatusPolling();
      stopPickupCountdown();
      medicinePickupErrorEl.textContent = "Không đóng được cửa. Vui lòng gọi nhân viên hỗ trợ.";
      medicinePickupErrorEl.hidden = false;
      retryDispenseButtonEl.hidden = false;
      completeDispenseButtonEl.disabled = true;
    }
  } catch (_error) {
    // Backend watchdog van la nguon dong cua chinh; lan poll sau se thu lai.
  }
}

function abortDispenseRequest() {
  if (!state.dispenseAbortController) {
    return;
  }
  state.dispenseAbortController.abort();
  state.dispenseAbortController = null;
}

async function startQrScanner() {
  stopQrScanner();
  qrFallbackButtonEl.hidden = true;
  qrStatusEl.textContent = "Đưa mã QR vào giữa khung camera";
  qrStatusEl.style.color = "var(--ink)";
  cameraPlaceholderEl.textContent = "CAMERA";

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showQrFallback("Camera cần localhost hoặc HTTPS. Hãy mở webapp bằng http://localhost:8000 trên Jetson hoặc HTTPS.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 640 },
        height: { ideal: 480 },
      },
      audio: false,
    });
    state.qrStream = stream;
    qrVideoEl.srcObject = stream;
    await qrVideoEl.play();
    qrVideoEl.parentElement.classList.add("has-video");

    if ("BarcodeDetector" in window) {
      try {
        state.qrDetector = new window.BarcodeDetector({ formats: ["qr_code"] });
      } catch (error) {
        state.qrDetector = null;
      }
    }

    if (!state.qrDetector && !window.jsQR) {
      showQrFallback("Không tải được bộ nhận diện QR. Vui lòng kiểm tra file QR local trên Jetson.");
      stopQrScanner();
      return;
    }

    state.qrBusy = false;
    state.qrLastScanTime = 0;
    scanQrFrame();
  } catch (error) {
    showQrFallback(getQrCameraErrorMessage(error));
    stopQrScanner();
  }
}

async function scanQrFrame(timestamp = 0) {
  if (state.qrBusy || !qrVideoEl.srcObject) {
    return;
  }
  const now = timestamp || performance.now();
  if (now - state.qrLastScanTime < QR_SCAN_INTERVAL_MS) {
    scheduleNextQrScan();
    return;
  }

  state.qrLastScanTime = now;
  state.qrBusy = true;
  try {
    let value = "";
    if (state.qrDetector) {
      const codes = await state.qrDetector.detect(qrVideoEl);
      value = codes[0]?.rawValue?.trim() || "";
    }
    if (!value) {
      value = scanQrWithCanvasFallback();
    }
    if (value) {
      await submitMedicineCode(value, "qr");
      return;
    }
  } catch (error) {
    const fallbackValue = scanQrWithCanvasFallback();
    if (fallbackValue) {
      await submitMedicineCode(fallbackValue, "qr");
      return;
    }
  } finally {
    state.qrBusy = false;
  }

  scheduleNextQrScan();
}

function scheduleNextQrScan() {
  if (qrVideoEl.srcObject) {
    state.qrAnimationFrame = window.requestAnimationFrame(scanQrFrame);
  }
}

function scanQrWithCanvasFallback() {
  if (!window.jsQR || !qrVideoEl.videoWidth || !qrVideoEl.videoHeight) {
    return "";
  }
  const context = qrCanvasEl.getContext("2d", { willReadFrequently: true });
  qrCanvasEl.width = qrVideoEl.videoWidth;
  qrCanvasEl.height = qrVideoEl.videoHeight;
  context.drawImage(qrVideoEl, 0, 0, qrCanvasEl.width, qrCanvasEl.height);
  const imageData = context.getImageData(0, 0, qrCanvasEl.width, qrCanvasEl.height);
  const result = window.jsQR(imageData.data, imageData.width, imageData.height);
  return result?.data?.trim() || "";
}

function getQrCameraErrorMessage(error) {
  const name = error?.name || "";
  if (!window.isSecureContext) {
    return "Camera cần localhost hoặc HTTPS. Hãy mở webapp bằng http://localhost:8000 trên Jetson hoặc HTTPS.";
  }
  if (name === "NotAllowedError" || name === "SecurityError") {
    return "Camera đang bị chặn. Trong Firefox, bấm biểu tượng camera hoặc ổ khóa trên thanh địa chỉ và cho phép Camera.";
  }
  if (name === "NotFoundError" || name === "OverconstrainedError") {
    return "Không tìm thấy camera. Kiểm tra camera USB/CSI trên Jetson rồi thử lại.";
  }
  if (name === "NotReadableError" || name === "AbortError") {
    return "Không đọc được camera. Kiểm tra camera có đang được ứng dụng khác sử dụng không.";
  }
  return "Không mở được camera. Kiểm tra quyền Camera trong Firefox và kết nối camera trên Jetson.";
}

function showQrFallback(message) {
  qrStatusEl.textContent = message;
  qrStatusEl.style.color = "var(--danger)";
  qrFallbackButtonEl.hidden = false;
}

function stopQrScanner() {
  if (state.qrAnimationFrame) {
    window.cancelAnimationFrame(state.qrAnimationFrame);
    state.qrAnimationFrame = null;
  }
  if (state.qrStream) {
    state.qrStream.getTracks().forEach((track) => track.stop());
    state.qrStream = null;
  }
  qrVideoEl.pause();
  qrVideoEl.removeAttribute("src");
  qrVideoEl.srcObject = null;
  qrVideoEl.parentElement.classList.remove("has-video");
  state.qrDetector = null;
  state.qrBusy = false;
  state.qrLastScanTime = 0;
}

async function openVoiceMode() {
  state.voiceOpen = true;
  voiceOverlayEl.hidden = false;
  clearMedicineSelectionOverlay();
  clearVoiceMedicineConfirmation();
  voiceTranscriptEl.textContent = "";
  startVoiceGreeting();
  await startGeminiLiveVoice();
}

function closeVoiceMode() {
  state.voiceOpen = false;
  state.voiceReconnectAttempts = 0;
  state.voiceListening = false;
  state.voiceSpeaking = false;
  state.voiceBusy = false;
  clearMedicineSelectionOverlay();
  clearVoiceMedicineConfirmation();
  stopVoiceGreeting();
  stopGeminiLiveVoice();
  voiceOverlayEl.hidden = true;
}

async function resetVoiceConversation() {
  if (!state.voiceOpen || state.voiceBusy) {
    return;
  }
  state.conversationId = null;
  state.voiceReconnectAttempts = 0;
  state.voiceSessionId = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
  state.pendingVoiceMedicineSelection = false;
  state.pendingVoiceMedicineConfirmation = false;
  state.medicineSelectionOpen = false;
  state.medicineRetryOpen = false;
  state.medicineOptions = [];
  state.pharmacityOriginalQuery = "";
  state.pharmacityTargetIntent = "";
  state.pharmacitySearchTerm = "";
  clearMedicineSelectionOverlay();
  clearVoiceMedicineConfirmation();
  voiceTranscriptEl.textContent = "";
  stopVoiceGreeting();
  stopGeminiLiveVoice();
  startVoiceGreeting();
  await startGeminiLiveVoice();
}

function startVoiceGreeting() {
  stopVoiceGreeting();
  if (!state.voiceOpen) {
    return;
  }

  const audio = new Audio(VOICE_GREETING_AUDIO_URL);
  audio.preload = "auto";
  state.voiceGreetingAudio = audio;
  state.voiceGreetingFinished = false;
  state.voiceListening = false;
  state.voiceSpeaking = true;
  voiceTranscriptEl.textContent = "";
  setVoiceState("speaking", "Đang chào bạn");

  const finishGreeting = () => finishVoiceGreeting(audio);
  audio.addEventListener("ended", finishGreeting, { once: true });
  audio.addEventListener("error", finishGreeting, { once: true });
  const playback = audio.play();
  if (playback?.catch) {
    playback.catch((error) => {
      console.warn("Cannot play the prerecorded voice greeting", error);
      finishGreeting();
    });
  }
}

function finishVoiceGreeting(audio) {
  if (state.voiceGreetingAudio !== audio) {
    return;
  }
  state.voiceGreetingAudio = null;
  state.voiceGreetingFinished = true;
  state.voiceSpeaking = false;
  syncVoiceInputState();
}

function stopVoiceGreeting() {
  const audio = state.voiceGreetingAudio;
  state.voiceGreetingAudio = null;
  state.voiceGreetingFinished = true;
  if (!audio) {
    return;
  }
  audio.pause();
  try {
    audio.currentTime = 0;
  } catch {
    // Firefox may reject seeking before the media metadata has loaded.
  }
}

function syncVoiceInputState() {
  if (!state.voiceOpen) {
    return;
  }
  if (!state.voiceGreetingFinished) {
    state.voiceListening = false;
    state.voiceSpeaking = true;
    setVoiceState("speaking", "Đang chào bạn");
    return;
  }
  state.voiceSpeaking = false;
  if (state.geminiLiveReady && state.voiceMediaStream && !state.voicePermissionBlocked) {
    state.voiceListening = true;
    setVoiceState("listening", "Đang nghe");
    return;
  }
  state.voiceListening = false;
  if (state.voiceBusy || state.voiceWebSocket) {
    setVoiceState("processing", "Đang kết nối Gemini Live");
  }
}

function setVoiceConnectionState(kind, text) {
  if (state.voiceOpen && !state.voiceGreetingFinished && kind !== "error") {
    syncVoiceInputState();
    return;
  }
  setVoiceState(kind, text);
}

function clearVoiceReconnectTimer() {
  if (state.voiceReconnectTimer) {
    window.clearTimeout(state.voiceReconnectTimer);
    state.voiceReconnectTimer = null;
  }
}

// Lên lịch reconnect Gemini Live với exponential backoff. Trả về true nếu đã lên
// lịch (còn lượt thử), false nếu hết lượt → caller hiển thị lỗi cuối cùng.
function scheduleVoiceReconnect() {
  if (state.voiceReconnectAttempts >= VOICE_MAX_RECONNECT_ATTEMPTS) {
    return false;
  }
  state.voiceReconnectAttempts += 1;
  const attempt = state.voiceReconnectAttempts;
  const delay = VOICE_RECONNECT_BASE_MS * 2 ** (attempt - 1);
  setVoiceConnectionState("processing", `Đang kết nối lại Gemini Live (${attempt}/${VOICE_MAX_RECONNECT_ATTEMPTS})`);
  clearVoiceReconnectTimer();
  state.voiceReconnectTimer = window.setTimeout(() => {
    state.voiceReconnectTimer = null;
    if (!state.voiceOpen || state.voiceBusy) {
      return;
    }
    stopGeminiLiveVoice();
    startGeminiLiveVoice();
  }, delay);
  return true;
}

async function startGeminiLiveVoice() {
  if (!state.voiceOpen) {
    return;
  }
  state.voicePermissionBlocked = false;
  if (!window.WebSocket || !navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
    setVoiceState("error", "Trình duyệt chưa hỗ trợ WebSocket, Web Audio hoặc microphone");
    return;
  }

  state.voiceBusy = true;
  setVoiceConnectionState("processing", "Đang lấy token Gemini");
  try {
    const session = await requestGeminiEphemeralToken();
    const websocket = new WebSocket(
      `${GEMINI_LIVE_WS_URL}?access_token=${encodeURIComponent(session.token)}`
    );
    state.voiceWebSocket = websocket;
    state.geminiLiveModel = session.model;

    websocket.addEventListener("message", async (event) => {
      try {
        const message = await parseGeminiLivePayload(event.data);
        handleGeminiLiveMessage(message).catch((error) => {
          console.warn("Cannot handle Gemini Live event", error);
          setVoiceState("error", error.message || "Lỗi xử lý Gemini Live");
        });
      } catch (error) {
        console.warn("Cannot parse Gemini Live event", error);
      }
    });
    websocket.addEventListener("close", (event) => {
      if (state.voiceWebSocket !== websocket || !state.voiceOpen || state.voicePermissionBlocked) {
        return;
      }
      state.voiceWebSocket = null;
      // WebSocket rớt ngoài ý muốn: thử kết nối lại có giới hạn trước khi báo lỗi.
      if (scheduleVoiceReconnect()) {
        return;
      }
      setVoiceState("error", "Lỗi Gemini Live");
      if (event.reason) {
        voiceTranscriptEl.textContent = event.reason.slice(0, 220);
      } else {
        voiceTranscriptEl.textContent =
          "Mất kết nối Gemini Live. Vui lòng kiểm tra mạng rồi bấm Cuộc hội thoại mới.";
      }
    });

    await new Promise((resolve, reject) => {
      websocket.addEventListener("open", () => {
        sendGeminiLiveMessage(buildGeminiSetupMessage(session.model, session.voice));
        setVoiceConnectionState("processing", "Đang cấu hình Gemini Live");
        resolve();
      }, { once: true });
      websocket.addEventListener("error", () => {
        reject(new Error("Không thể kết nối Gemini Live WebSocket"));
      }, { once: true });
    });

    setVoiceConnectionState("processing", "Đang xin quyền microphone");
    await startGeminiAudioInput();
  } catch (error) {
    console.warn("Cannot start Gemini Live voice", error);
    stopGeminiLiveVoice();
    if (state.voiceOpen) {
      if (error.message === "MICROPHONE_PERMISSION_DENIED") {
        showMicrophonePermissionHelp();
      } else if (error.message === "MICROPHONE_NOT_FOUND") {
        setVoiceState("error", "Không tìm thấy microphone");
        voiceTranscriptEl.textContent = "Không tìm thấy thiết bị microphone. Vui lòng kiểm tra microphone rồi bấm Cuộc hội thoại mới.";
      } else {
        setVoiceState("error", error.message || "Không thể khởi động Gemini Live");
        voiceTranscriptEl.textContent = "Không thể khởi động đàm thoại giọng nói. Vui lòng kiểm tra kết nối và microphone rồi thử lại.";
      }
    }
  } finally {
    state.voiceBusy = false;
  }
}

function stopGeminiLiveVoice() {
  clearVoiceReconnectTimer();
  if (state.voiceAudioProcessor) {
    try {
      state.voiceAudioProcessor.disconnect();
    } catch {
      // Ignore cleanup errors.
    }
  }
  if (state.voiceAudioInputSource) {
    try {
      state.voiceAudioInputSource.disconnect();
    } catch {
      // Ignore cleanup errors.
    }
  }
  if (state.voiceAudioSilenceGain) {
    try {
      state.voiceAudioSilenceGain.disconnect();
    } catch {
      // Ignore cleanup errors.
    }
  }
  if (state.voiceMediaStream) {
    state.voiceMediaStream.getTracks().forEach((track) => track.stop());
  }
  if (state.voiceWebSocket) {
    const websocket = state.voiceWebSocket;
    state.voiceWebSocket = null;
    try {
      websocket.close();
    } catch {
      // Ignore cleanup errors.
    }
  }
  if (state.voiceAudioContext) {
    try {
      state.voiceAudioContext.close();
    } catch {
      // Ignore cleanup errors.
    }
  }
  state.voiceMediaStream = null;
  state.voiceAudioContext = null;
  state.voiceAudioInputSource = null;
  state.voiceAudioProcessor = null;
  state.voiceAudioSilenceGain = null;
  state.voiceOutputNextTime = 0;
  state.geminiLiveReady = false;
  state.voicePermissionBlocked = false;
  state.pendingGeminiToolCalls = {};
  state.voiceListening = false;
  state.voiceSpeaking = false;
}

async function requestGeminiEphemeralToken() {
  const response = await fetch(GEMINI_EPHEMERAL_TOKEN_URL, { method: "POST" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Không thể tạo Gemini ephemeral token.");
  }
  if (!data.token || !data.model) {
    throw new Error("Gemini token response thiếu token hoặc model.");
  }
  return data;
}

function buildGeminiSetupMessage(model, voiceName = "Kore") {
  return {
    setup: {
      model: model.startsWith("models/") ? model : `models/${model}`,
      generationConfig: {
        responseModalities: ["AUDIO"],
        temperature: 0.2,
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: {
              voiceName: voiceName || "Kore",
            },
          },
        },
      },
      systemInstruction: {
        parts: [
          {
            text:
              "Bạn là KungKung, trợ lý voice song ngữ Việt-Anh cho webapp robot y tế của Bệnh viện Hạnh Phúc. " +
              "Ở đầu mỗi cuộc hội thoại, hãy xác định ngôn ngữ từ phát ngôn có ý nghĩa đầu tiên của người dùng rồi khóa ngôn ngữ trả lời là tiếng Việt hoặc tiếng Anh. " +
              "Nếu phát ngôn đầu tiên quá ngắn, chỉ là tên riêng, hoặc trộn tiếng Việt với tiếng Anh, mặc định khóa tiếng Việt. " +
              "Sau khi đã khóa, luôn trả lời bằng ngôn ngữ đó dù người dùng dùng ngôn ngữ còn lại; chỉ đổi khi người dùng yêu cầu rõ ràng và phải giữ nguyên ngữ cảnh hội thoại. " +
              "Khi trả lời tiếng Việt, giữ nguyên bằng tiếng Anh các thuật ngữ chuyên môn, tên kỹ thuật, tên sản phẩm, tên thương hiệu và chữ viết tắt đã được chuẩn hóa. Khi trả lời tiếng Anh, dùng tiếng Anh tự nhiên. " +
              "Trả lời ngắn, rõ, thân thiện cho bệnh nhân và người nhà. " +
              "Trước khi gọi rag_answer hoặc pharmacity_search cho câu hỏi tiếng Anh, hãy dịch nội dung tra cứu sang tiếng Việt nhưng giữ nguyên tên riêng, tên thuốc, số liệu và mã định danh; tham số query gửi vào tool phải là tiếng Việt. " +
              "Khi người dùng hỏi thông tin bệnh viện, khoa, bác sĩ, lịch khám, gói dịch vụ, tiện ích, chính sách hoặc lấy thuốc/thiết bị, hãy gọi tool rag_answer trước rồi chỉ dựa trên kết quả tool để trả lời. " +
              "Không trả lời kiến thức tổng quát ngoài phạm vi Bệnh viện Hạnh Phúc và tra cứu sản phẩm thuốc. Nếu câu hỏi ngoài phạm vi, hãy nói rõ giới hạn, gợi ý các chủ đề được hỗ trợ và không nhắc hotline. " +
              "Kết quả tool có thể bằng tiếng Việt; hãy chuyển sang ngôn ngữ đang khóa một cách trung thành và không thêm dữ kiện. Nếu rag_answer trả grounded=false, phải giữ đúng ý nghĩa trường answer; chỉ được dịch sang ngôn ngữ đang khóa, không bổ sung hoặc diễn giải thành thông tin mới. " +
              "Khi người dùng hỏi về thuốc hoặc sản phẩm thuốc cụ thể như tên thuốc, cách dùng, công dụng, thành phần, lưu ý, chống chỉ định, tác dụng phụ hoặc giá thuốc, hãy gọi tool pharmacity_search. " +
              "Không từ chối câu hỏi tra cứu thông tin thuốc có tên sản phẩm; hãy chờ người dùng chọn sản phẩm trên màn hình, sau đó trả lời ngắn dựa trên dữ liệu Pharmacity đã crawl. " +
              "Không chẩn đoán bệnh, không kê đơn, không tự điều chỉnh liều và không xác nhận thuốc phù hợp với triệu chứng cá nhân. " +
              "Nếu người dùng hỏi nên uống thuốc gì cho triệu chứng mà không nêu sản phẩm cụ thể, hãy từ chối kê đơn và khuyên hỏi bác sĩ hoặc dược sĩ. Chỉ nhắc hotline khi tool đã đưa hotline trong trường answer. " +
              "Nếu tool trả requires_hardware_confirmation=true, hãy nói người dùng xác nhận trên màn hình; không tự khẳng định đã lấy thuốc hoặc đã điều khiển thiết bị.",
          },
        ],
      },
      tools: [
        {
          functionDeclarations: [
            {
              name: "rag_answer",
              description:
                "Tra cứu dữ liệu bệnh viện bằng RAG. Gọi trước khi trả lời mọi câu hỏi về bệnh viện, dịch vụ, lịch khám hoặc lấy thuốc/thiết bị.",
              parameters: {
                type: "object",
                properties: {
                  query: {
                    type: "string",
                    description:
                      "Nội dung tra cứu bằng tiếng Việt. Nếu người dùng nói tiếng Anh, dịch câu hỏi sang tiếng Việt nhưng giữ nguyên tên riêng, số liệu và mã định danh trước khi gọi tool.",
                  },
                },
                required: ["query"],
              },
            },
            {
              name: "pharmacity_search",
              description:
                "Tra cứu thuốc hoặc sản phẩm thuốc trên Pharmacity. Gọi khi người dùng hỏi về tên thuốc cụ thể, cách dùng, công dụng, thành phần, lưu ý, tác dụng phụ, chống chỉ định hoặc giá thuốc.",
              parameters: {
                type: "object",
                properties: {
                  query: {
                    type: "string",
                    description:
                      "Nội dung tra cứu thuốc bằng tiếng Việt. Nếu người dùng nói tiếng Anh, dịch câu hỏi sang tiếng Việt nhưng giữ nguyên tên thuốc, thương hiệu, số liệu và mã định danh trước khi gọi tool.",
                  },
                },
                required: ["query"],
              },
            },
          ],
        },
      ],
      inputAudioTranscription: {},
      outputAudioTranscription: {},
    },
  };
}

function sendGeminiLiveMessage(payload) {
  if (!state.voiceWebSocket || state.voiceWebSocket.readyState !== WebSocket.OPEN) {
    return false;
  }
  state.voiceWebSocket.send(JSON.stringify(payload));
  return true;
}

async function parseGeminiLivePayload(data) {
  if (typeof data === "string") {
    return JSON.parse(data);
  }
  if (data instanceof Blob) {
    return JSON.parse(await data.text());
  }
  if (data instanceof ArrayBuffer) {
    return JSON.parse(new TextDecoder("utf-8").decode(data));
  }
  throw new Error("Định dạng message Gemini Live không được hỗ trợ.");
}

async function startGeminiAudioInput() {
  const audioContext = await ensureVoiceAudioContext();
  await ensureMicrophonePermission();
  const mediaStream = await withTimeout(
    getVoiceMediaStream(),
    10000,
    "Không nhận được quyền microphone kịp thời"
  );
  const source = audioContext.createMediaStreamSource(mediaStream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  const silenceGain = audioContext.createGain();
  silenceGain.gain.value = 0;

  processor.onaudioprocess = (event) => {
    if (!state.voiceOpen || !state.geminiLiveReady || !state.voiceGreetingFinished) {
      return;
    }
    const samples = event.inputBuffer.getChannelData(0);
    const audioData = float32ToPcm16Base64(samples, audioContext.sampleRate, 16000);
    sendGeminiLiveMessage({
      realtimeInput: {
        audio: {
          data: audioData,
          mimeType: "audio/pcm;rate=16000",
        },
      },
    });
  };

  source.connect(processor);
  processor.connect(silenceGain);
  silenceGain.connect(audioContext.destination);

  state.voiceMediaStream = mediaStream;
  state.voiceAudioInputSource = source;
  state.voiceAudioProcessor = processor;
  state.voiceAudioSilenceGain = silenceGain;
  syncVoiceInputState();
}

async function ensureMicrophonePermission() {
  if (!navigator.permissions?.query) {
    return;
  }
  try {
    const permission = await navigator.permissions.query({ name: "microphone" });
    if (permission.state === "denied") {
      throw new Error("MICROPHONE_PERMISSION_DENIED");
    }
  } catch (error) {
    if (error.message === "MICROPHONE_PERMISSION_DENIED") {
      throw error;
    }
  }
}

async function getVoiceMediaStream() {
  try {
    return await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });
  } catch (error) {
    if (["NotAllowedError", "PermissionDeniedError"].includes(error.name)) {
      throw new Error("MICROPHONE_PERMISSION_DENIED");
    }
    if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      throw new Error("MICROPHONE_NOT_FOUND");
    }
    throw error;
  }
}

function showMicrophonePermissionHelp() {
  state.voicePermissionBlocked = true;
  setVoiceState("error", "Chưa cấp quyền microphone");
  voiceTranscriptEl.textContent =
    "Microphone đang bị chặn. Bấm biểu tượng ổ khóa hoặc camera trên thanh địa chỉ, cho phép Microphone, rồi bấm Cuộc hội thoại mới.";
}

async function ensureVoiceAudioContext() {
  if (!state.voiceAudioContext) {
    state.voiceAudioContext = new AudioContext();
  }
  if (state.voiceAudioContext.state === "suspended") {
    await Promise.race([
      state.voiceAudioContext.resume().catch(() => {}),
      delay(600),
    ]);
  }
  return state.voiceAudioContext;
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function withTimeout(promise, ms, message) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(message)), ms);
  });
  try {
    return await Promise.race([promise, timeout]);
  } finally {
    window.clearTimeout(timeoutId);
  }
}

// fetch có timeout thật sự: hủy request qua AbortController khi quá hạn để không
// giữ kết nối treo (quan trọng với lệnh điều khiển Arduino).
async function fetchWithTimeout(url, options = {}, ms = HARDWARE_REQUEST_TIMEOUT_MS, timeoutMessage = "Hết thời gian chờ thiết bị phản hồi.") {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw new Error(timeoutMessage);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function handleGeminiLiveMessage(message) {
  if (!message || !state.voiceOpen) {
    return;
  }
  if (message.setupComplete) {
    state.geminiLiveReady = true;
    state.voiceReconnectAttempts = 0; // kết nối khỏe lại → làm mới hạn mức reconnect
    syncVoiceInputState();
    return;
  }
  if (message.toolCall) {
    await handleGeminiToolCall(message.toolCall);
    return;
  }
  if (message.toolCallCancellation?.ids) {
    message.toolCallCancellation.ids.forEach((id) => delete state.pendingGeminiToolCalls[id]);
    return;
  }
  if (message.error) {
    setVoiceState("error", message.error.message || "Lỗi Gemini Live");
    return;
  }
  const serverContent = message.serverContent;
  if (!serverContent) {
    return;
  }
  const inputText = serverContent.inputTranscription?.text;
  if (inputText) {
    voiceTranscriptEl.textContent = inputText;
    setVoiceState("processing", "Đang xử lý");
  }
  const outputText = serverContent.outputTranscription?.text;
  if (outputText) {
    voiceTranscriptEl.textContent = outputText;
  }
  const parts = serverContent.modelTurn?.parts || [];
  for (const part of parts) {
    const inlineData = part.inlineData || part.inline_data;
    const audioData = inlineData?.data;
    if (audioData) {
      await playGeminiPcmAudio(audioData);
    }
  }
  if (serverContent.turnComplete) {
    const audioContext = state.voiceAudioContext;
    const delayMs = audioContext ? Math.max(0, state.voiceOutputNextTime - audioContext.currentTime) * 1000 : 0;
    window.setTimeout(() => {
      if (state.voiceOpen && !state.pendingVoiceMedicineConfirmation && !state.pendingVoiceMedicineSelection) {
        state.voiceSpeaking = false;
        state.voiceListening = true;
        setVoiceState("listening", "Đang nghe");
      }
    }, delayMs + 80);
  }
}

async function handleGeminiToolCall(toolCall) {
  const functionCalls = toolCall.functionCalls || toolCall.function_calls || [];
  if (!functionCalls.length) {
    return;
  }
  const functionResponses = [];
  for (const functionCall of functionCalls) {
    const callId = functionCall.id || `${functionCall.name}-${Date.now()}`;
    if (state.pendingGeminiToolCalls[callId]) {
      continue;
    }
    state.pendingGeminiToolCalls[callId] = true;
    if (!["rag_answer", "pharmacity_search"].includes(functionCall.name)) {
      functionResponses.push({
        id: callId,
        name: functionCall.name || "unsupported_tool",
        response: { error: "Unsupported tool" },
      });
      continue;
    }
    const args = functionCall.args || {};
    const query = String(args.query || voiceTranscriptEl.textContent || "").trim();

    if (functionCall.name === "pharmacity_search") {
      setVoiceState("processing", "Đang tìm thuốc trên Pharmacity");
      let payload;
      try {
        payload = await requestPharmacitySearch(query);
      } catch (error) {
        payload = {
          ok: false,
          detail: error.message || "Không thể tra cứu Pharmacity.",
          products: [],
        };
        setVoiceState("error", payload.detail);
      }

      const products = Array.isArray(payload.products) ? payload.products : [];
      // Người dùng có thể đã đóng voice trong lúc chờ kết quả; không thao tác UI đã đóng.
      if (!state.voiceOpen) {
        continue;
      }
      if (products.length) {
        voiceTranscriptEl.textContent = `Tôi tìm thấy ${products.length} sản phẩm cho "${payload.search_term || query}". Bạn chọn đúng thuốc trên màn hình nhé.`;
        openMedicineSelectionOverlay(products, payload);
      } else {
        state.pharmacityOriginalQuery = payload.original_query || query;
        state.pharmacityTargetIntent = payload.target_intent || "";
        state.pharmacitySearchTerm = payload.search_term || query;
        state.pendingVoiceMedicineSelection = true;
        state.medicineSelectionOpen = false;
        voiceTranscriptEl.textContent =
          "Tôi chưa tìm thấy sản phẩm phù hợp trên Pharmacity. Bạn nhập lại tên thuốc nhé.";
        openMedicineRetryPanel({ prefill: payload.search_term || query });
      }

      functionResponses.push({
        id: callId,
        name: "pharmacity_search",
        response: {
          result: {
            ok: Boolean(payload.ok),
            status: products.length ? "waiting_for_user_selection" : "no_results",
            original_query: payload.original_query || query,
            search_term: payload.search_term || query,
            target_intent: payload.target_intent || "",
            product_count: products.length,
          },
        },
      });
      continue;
    }

    setVoiceState("processing", "Đang tra cứu dữ liệu bệnh viện");
    let payload;
    try {
      payload = await requestRagAnswer(query);
    } catch (error) {
      payload = {
        answer: error.message || "Không thể tra cứu dữ liệu bệnh viện.",
        requires_hardware_confirmation: false,
        contexts: [],
      };
      setVoiceState("error", payload.answer);
    }
    // Bỏ qua thao tác UI nếu voice đã bị đóng trong lúc chờ kết quả.
    if (!state.voiceOpen) {
      continue;
    }
    if (payload.answer) {
      voiceTranscriptEl.textContent = payload.answer;
    }
    if (payload.requires_hardware_confirmation) {
      openVoiceMedicineConfirmation(payload.answer);
    }
    functionResponses.push({
      id: callId,
      name: "rag_answer",
      response: { result: payload },
    });
  }
  if (functionResponses.length) {
    submitGeminiToolResponse(functionResponses);
  }
}

function submitGeminiToolResponse(functionResponses) {
  sendGeminiLiveMessage({
    toolResponse: {
      functionResponses,
    },
  });
}

async function playGeminiPcmAudio(audioBase64) {
  const audioContext = await ensureVoiceAudioContext();
  const samples = base64ToInt16Array(audioBase64);
  if (!samples.length) {
    return;
  }
  const audioBuffer = audioContext.createBuffer(1, samples.length, 24000);
  const channel = audioBuffer.getChannelData(0);
  for (let index = 0; index < samples.length; index += 1) {
    channel[index] = Math.max(-1, Math.min(1, samples[index] / 32768));
  }
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  const startAt = Math.max(audioContext.currentTime, state.voiceOutputNextTime || audioContext.currentTime);
  source.start(startAt);
  state.voiceOutputNextTime = startAt + audioBuffer.duration;
  state.voiceSpeaking = true;
  state.voiceListening = false;
  setVoiceState("speaking", "Đang trả lời");
}

function float32ToPcm16Base64(samples, inputSampleRate, outputSampleRate) {
  const pcmSamples = inputSampleRate === outputSampleRate
    ? samples
    : downsampleFloat32Array(samples, inputSampleRate, outputSampleRate);
  const buffer = new ArrayBuffer(pcmSamples.length * 2);
  const view = new DataView(buffer);
  for (let index = 0; index < pcmSamples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, pcmSamples[index]));
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return arrayBufferToBase64(buffer);
}

function downsampleFloat32Array(samples, inputSampleRate, outputSampleRate) {
  if (outputSampleRate >= inputSampleRate) {
    return samples;
  }
  const ratio = inputSampleRate / outputSampleRate;
  const outputLength = Math.floor(samples.length / ratio);
  const output = new Float32Array(outputLength);
  for (let outputIndex = 0; outputIndex < outputLength; outputIndex += 1) {
    const inputIndex = Math.floor(outputIndex * ratio);
    output[outputIndex] = samples[inputIndex] || 0;
  }
  return output;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return window.btoa(binary);
}

function base64ToInt16Array(base64) {
  const binary = window.atob(base64);
  const buffer = new ArrayBuffer(binary.length);
  const bytes = new Uint8Array(buffer);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Int16Array(buffer);
}

async function requestRagAnswer(query) {
  const response = await fetch(RAG_ANSWER_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      voice: true,
      top_k: 5,
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Không thể tra cứu RAG.");
  }
  return data;
}

async function requestPharmacitySearch(query, options = {}) {
  const response = await fetch(PHARMACITY_SEARCH_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      original_query: options.originalQuery || query,
      target_intent: options.targetIntent || "",
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.detail || "Không thể tra cứu Pharmacity.");
  }
  return data;
}

async function requestPharmacityAnswer(product, context = {}) {
  const response = await fetch(PHARMACITY_ANSWER_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      original_query: context.originalQuery || state.pharmacityOriginalQuery || product.name || "",
      target_intent: context.targetIntent || state.pharmacityTargetIntent || "",
      product,
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.detail || "Không thể lấy thông tin thuốc từ Pharmacity.");
  }
  return data;
}

function openVoiceMedicineConfirmation(message = "") {
  state.pendingVoiceMedicineConfirmation = true;
  if (message) {
    voiceTranscriptEl.textContent = message;
  }
  if (voiceMedicineConfirmEl) {
    voiceMedicineConfirmEl.hidden = false;
  }
  setVoiceState("idle", "Cần xác nhận trên màn hình");
}

function clearVoiceMedicineConfirmation() {
  state.pendingVoiceMedicineConfirmation = false;
  if (voiceMedicineConfirmEl) {
    voiceMedicineConfirmEl.hidden = true;
  }
}

async function confirmVoiceMedicineDispense() {
  if (!state.pendingVoiceMedicineConfirmation || state.voiceBusy) {
    return;
  }
  if (!state.currentMedicineOrder?.id) {
    setVoiceState("error", "Vui lòng nhập hoặc quét ID bệnh nhân trước.");
    return;
  }
  state.voiceBusy = true;
  setVoiceState("processing", "Đang gửi xác nhận lấy thuốc");
  try {
    state.voiceBusy = false;
    const opened = await dispenseCurrentMedicineOrder();
    if (!opened) throw new Error(medicineConfirmErrorEl.textContent || "Không thể mở khay thuốc.");
    clearVoiceMedicineConfirmation();
  } catch (error) {
    setVoiceState("error", error.message || "Không thể gửi xác nhận lấy thuốc");
  } finally {
    state.voiceBusy = false;
  }
}

function openMedicineSelectionOverlay(options, meta = {}) {
  const visibleOptions = Array.isArray(options) ? options.slice(0, 4) : [];
  state.pendingVoiceMedicineSelection = true;
  state.medicineSelectionOpen = true;
  state.medicineRetryOpen = false;
  state.medicineOptions = visibleOptions;
  state.pharmacityOriginalQuery = meta.original_query || state.pharmacityOriginalQuery || "";
  state.pharmacityTargetIntent = meta.target_intent || state.pharmacityTargetIntent || "";
  state.pharmacitySearchTerm = meta.search_term || state.pharmacitySearchTerm || "";
  clearMedicineRetryPanel({ clearInput: false });

  if (!medicineClassGridEl || visibleOptions.length === 0) {
    clearMedicineSelectionOverlay();
    setVoiceState("error", "Tôi chưa tìm được danh sách thuốc phù hợp. Bạn vui lòng thử hỏi lại.");
    return;
  }

  medicineClassGridEl.replaceChildren();
  visibleOptions.forEach((option, optionIndex) => {
    const button = document.createElement("button");
    button.className = "medicine-class-card";
    button.type = "button";
    button.dataset.index = String(option.index || optionIndex + 1);
    button.dataset.sku = option.sku || "";

    const media = document.createElement("span");
    media.className = "medicine-class-media";

    if (option.image_url) {
      const image = document.createElement("img");
      image.src = option.image_url;
      image.alt = "";
      image.loading = "lazy";
      media.appendChild(image);
    } else {
      const placeholder = document.createElement("span");
      placeholder.className = "medicine-class-placeholder";
      placeholder.textContent = "Thuốc";
      media.appendChild(placeholder);
    }

    const name = document.createElement("span");
    name.className = "medicine-class-name";
    name.textContent = option.name || `Thuốc ${option.index || optionIndex + 1}`;

    button.append(media, name);
    button.addEventListener("click", () => selectMedicineClassOption(option, button));
    medicineClassGridEl.appendChild(button);
  });

  const retryButton = document.createElement("button");
  retryButton.className = "medicine-class-card medicine-retry-card";
  retryButton.type = "button";
  retryButton.setAttribute("aria-label", "Không đúng thuốc, nhập tên thuốc khác");

  const retryLabel = document.createElement("span");
  retryLabel.className = "medicine-retry-card-title";
  retryLabel.textContent = "Không đúng thuốc";

  const retryHint = document.createElement("span");
  retryHint.className = "medicine-retry-card-hint";
  retryHint.textContent = "Nhập lại tên thuốc cần tìm";

  retryButton.append(retryLabel, retryHint);
  retryButton.addEventListener("click", () => openMedicineRetryPanel());
  medicineClassGridEl.appendChild(retryButton);

  medicineClassGridEl.hidden = false;
  setVoiceState("idle", "Chọn thuốc cần hỏi");
}

function clearMedicineSelectionOverlay() {
  state.pendingVoiceMedicineSelection = false;
  state.medicineSelectionOpen = false;
  state.medicineRetryOpen = false;
  state.medicineOptions = [];
  state.pharmacityOriginalQuery = "";
  state.pharmacityTargetIntent = "";
  state.pharmacitySearchTerm = "";
  clearMedicineRetryPanel();
  if (!medicineClassGridEl) {
    return;
  }
  medicineClassGridEl.hidden = true;
  medicineClassGridEl.replaceChildren();
}

async function selectMedicineClassOption(option, selectedButton) {
  if (!state.voiceOpen || state.voiceBusy || !state.pendingVoiceMedicineSelection) {
    return;
  }

  const selectedIndex = Number(option.index || selectedButton?.dataset.index);
  if (!Number.isFinite(selectedIndex) || selectedIndex < 1) {
    setVoiceState("error", "Tôi chưa chọn được thuốc này. Bạn vui lòng thử lại.");
    return;
  }

  state.voiceBusy = true;
  setVoiceState("processing", "Đang kiểm tra thuốc");
  setMedicineSelectionDisabled(true, selectedButton);
  const answerContext = {
    originalQuery: state.pharmacityOriginalQuery || voiceTranscriptEl.textContent || option.name || "",
    targetIntent: state.pharmacityTargetIntent || "",
  };
  const aiStartedAt = performance.now();
  let aiMetricLogged = false;

  try {
    const data = await requestPharmacityAnswer(option, answerContext);
    logVoiceMetric("ai_response", performance.now() - aiStartedAt, "Thời gian phản hồi của AI khi chọn thuốc");
    aiMetricLogged = true;
    clearMedicineSelectionOverlay();
    voiceTranscriptEl.textContent = "Tôi đã lấy được dữ liệu Pharmacity, đang soạn câu trả lời.";
    const sent = sendPharmacityAnswerToGeminiLive(data, answerContext);
    if (!sent) {
      showPharmacityTextFallback(data);
    }
  } catch (error) {
    if (!aiMetricLogged) {
      logVoiceMetric("ai_response", performance.now() - aiStartedAt, "Thời gian phản hồi của AI khi chọn thuốc");
    }
    setMedicineSelectionDisabled(false);
    setVoiceState("error", "Xin lỗi, tôi chưa lấy được thông tin thuốc. Bạn vui lòng thử lại.");
  } finally {
    state.voiceBusy = false;
  }
}

function openMedicineRetryPanel({ prefill = "" } = {}) {
  state.pendingVoiceMedicineSelection = true;
  state.medicineSelectionOpen = false;
  state.medicineRetryOpen = true;
  if (medicineClassGridEl) {
    medicineClassGridEl.hidden = true;
  }
  if (!medicineRetryPanelEl) {
    setVoiceState("error", "Chưa có ô nhập lại tên thuốc");
    return;
  }
  medicineRetryPanelEl.hidden = false;
  if (medicineRetryInputEl) {
    medicineRetryInputEl.value = prefill || state.pharmacitySearchTerm || "";
    window.setTimeout(() => {
      medicineRetryInputEl.focus();
      medicineRetryInputEl.select();
    }, 0);
  }
  setVoiceState("idle", "Nhập lại tên thuốc");
}

function closeMedicineRetryPanel({ restoreGrid = false } = {}) {
  clearMedicineRetryPanel({ clearInput: false });
  if (restoreGrid && state.pendingVoiceMedicineSelection && state.medicineOptions.length && medicineClassGridEl) {
    state.medicineSelectionOpen = true;
    medicineClassGridEl.hidden = false;
    setVoiceState("idle", "Chọn thuốc cần hỏi");
    return;
  }
  if (!state.medicineOptions.length) {
    clearMedicineSelectionOverlay();
    voiceTranscriptEl.textContent = "Bạn có thể hỏi lại hoặc nói rõ tên thuốc cần tìm.";
    setVoiceState(state.geminiLiveReady ? "listening" : "idle", state.geminiLiveReady ? "Đang nghe" : "Sẵn sàng nghe");
    return;
  }
  if (state.pendingVoiceMedicineSelection) {
    setVoiceState("idle", "Chọn thuốc cần hỏi");
  }
}

function clearMedicineRetryPanel({ clearInput = true } = {}) {
  state.medicineRetryOpen = false;
  if (medicineRetryPanelEl) {
    medicineRetryPanelEl.hidden = true;
  }
  if (clearInput && medicineRetryInputEl) {
    medicineRetryInputEl.value = "";
  }
}

async function submitMedicineRetrySearch() {
  if (!state.voiceOpen || state.voiceBusy || !state.pendingVoiceMedicineSelection) {
    return;
  }
  const query = String(medicineRetryInputEl?.value || "").trim();
  if (!query) {
    setVoiceState("error", "Bạn nhập tên thuốc cần tìm");
    return;
  }

  const originalQuery = state.pharmacityOriginalQuery || query;
  const targetIntent = state.pharmacityTargetIntent || "";
  state.voiceBusy = true;
  setVoiceState("processing", "Đang tìm lại thuốc");
  if (medicineRetrySearchButtonEl) {
    medicineRetrySearchButtonEl.disabled = true;
  }
  if (medicineRetryCancelButtonEl) {
    medicineRetryCancelButtonEl.disabled = true;
  }

  try {
    const payload = await requestPharmacitySearch(query, { originalQuery, targetIntent });
    const products = Array.isArray(payload.products) ? payload.products : [];
    state.pharmacityOriginalQuery = payload.original_query || originalQuery;
    state.pharmacityTargetIntent = payload.target_intent || targetIntent;
    state.pharmacitySearchTerm = payload.search_term || query;

    if (!products.length) {
      voiceTranscriptEl.textContent = "Tôi chưa tìm thấy sản phẩm phù hợp. Bạn sửa lại tên thuốc rồi bấm Tìm lại.";
      setVoiceState("error", "Chưa tìm thấy thuốc");
      openMedicineRetryPanel({ prefill: query });
      return;
    }

    voiceTranscriptEl.textContent = `Tôi tìm thấy ${products.length} sản phẩm cho "${payload.search_term || query}". Bạn chọn đúng thuốc trên màn hình nhé.`;
    openMedicineSelectionOverlay(products, payload);
  } catch (error) {
    voiceTranscriptEl.textContent = error.message || "Không thể tìm lại thuốc trên Pharmacity.";
    setVoiceState("error", "Không thể tìm lại thuốc");
    openMedicineRetryPanel({ prefill: query });
  } finally {
    if (medicineRetrySearchButtonEl) {
      medicineRetrySearchButtonEl.disabled = false;
    }
    if (medicineRetryCancelButtonEl) {
      medicineRetryCancelButtonEl.disabled = false;
    }
    state.voiceBusy = false;
  }
}

function sendPharmacityAnswerToGeminiLive(data, context = {}) {
  if (!state.geminiLiveReady) {
    return false;
  }
  const prompt = buildPharmacityLiveAnswerPrompt(data, context);
  state.voiceListening = false;
  state.voiceSpeaking = false;
  setVoiceState("processing", "Đang trả lời");
  const sent = sendGeminiLiveMessage({
    clientContent: {
      turns: [
        {
          role: "user",
          parts: [{ text: prompt }],
        },
      ],
      turnComplete: true,
    },
  });
  if (!sent) {
    setVoiceState("idle", "Sẵn sàng nghe");
  }
  return sent;
}

function buildPharmacityLiveAnswerPrompt(data, context = {}) {
  const product = data.product || {};
  const extractedFields = data.extracted_fields || {};
  const fallbackAnswer = data.answer || "";
  const sourceUrl = data.source_url || product.detail_url || "";
  const fieldsText = JSON.stringify(extractedFields, null, 2).slice(0, 9000);
  return [
    "Người dùng đã chọn sản phẩm thuốc từ danh sách Pharmacity. Hãy trả lời và phát audio bằng ngôn ngữ đang khóa của cuộc hội thoại.",
    "Nếu ngôn ngữ đang khóa là tiếng Việt, giữ nguyên bằng tiếng Anh các thuật ngữ chuyên môn, tên kỹ thuật, tên sản phẩm, tên thương hiệu và chữ viết tắt đã được chuẩn hóa.",
    `Câu hỏi gốc: ${context.originalQuery || ""}`,
    `Mục tiêu câu hỏi: ${context.targetIntent || "tra cứu thông tin thuốc"}`,
    `Sản phẩm đã chọn: ${product.name || ""}`,
    `Nguồn Pharmacity: ${sourceUrl}`,
    "Dữ liệu đã crawl từ Pharmacity:",
    fieldsText || "(Không có trường chi tiết có cấu trúc)",
    fallbackAnswer ? `Câu trả lời fallback của backend: ${fallbackAnswer}` : "",
    "Yêu cầu an toàn: chỉ dùng dữ liệu Pharmacity ở trên; trả lời ngắn tối đa 4 câu; không chẩn đoán, không kê đơn, không đổi liều, không xác nhận thuốc phù hợp với triệu chứng cá nhân. Nếu dữ liệu cho thấy thuốc kê đơn hoặc cần tư vấn, nhắc người dùng hỏi bác sĩ hoặc dược sĩ.",
  ]
    .filter(Boolean)
    .join("\n\n");
}

function showPharmacityTextFallback(data) {
  const answer = data.answer || "Tôi đã lấy được dữ liệu Pharmacity nhưng chưa thể phát câu trả lời bằng Gemini Live.";
  voiceTranscriptEl.textContent = answer;
  setVoiceState("idle", "Sẵn sàng nghe");
}

function setMedicineSelectionDisabled(disabled, selectedButton = null) {
  if (!medicineClassGridEl) {
    return;
  }
  medicineClassGridEl.querySelectorAll(".medicine-class-card").forEach((button) => {
    button.disabled = disabled;
    button.classList.toggle("is-selected", button === selectedButton);
  });
}

function logVoiceMetric(metric, elapsedMs, label = "") {
  const payload = {
    metric,
    elapsed_ms: Number(elapsedMs.toFixed(2)),
  };
  if (state.conversationId) {
    payload.conversation_id = state.conversationId;
  }
  if (label) {
    payload.label = label;
  }

  const metricLabels = {
    ai_response: "AI response time",
    voice_start_latency: "Voice start latency",
    voice_response: "Voice playback duration",
  };
  const messageLabel = label || metricLabels[metric] || metric;
  console.info(`${messageLabel}: ${payload.elapsed_ms} ms (${(payload.elapsed_ms / 1000).toFixed(2)} s)`);

  fetch("/robot/api/voice-metrics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
}

function setVoiceState(kind, text) {
  const supportedStates = new Set(["idle", "listening", "processing", "speaking", "error"]);
  const resolvedState = supportedStates.has(kind) ? kind : "idle";
  voiceOverlayEl.dataset.state = resolvedState;
  voiceStatusEl.textContent = text;
  setEmojiExpression(resolvedState);
}

function voiceExpressionForState(voiceState) {
  const expressionByState = {
    idle: "neutral",
    listening: "happy",
    processing: "neutral",
    speaking: "happy",
    error: "sad",
  };
  return expressionByState[voiceState] || "neutral";
}

function setEmojiExpression(voiceState = "idle") {
  if (!voiceEmojiEl) {
    return;
  }
  voiceEmojiEl.dataset.expression = voiceExpressionForState(voiceState);
}
