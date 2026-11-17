# 🤖 AI Medical Assistant Robot for Hospitals

The voice and touch assistant of a hospital medicine-delivery robot, running on an **NVIDIA Jetson Nano**. Patients and staff can ask questions by voice or on the touch screen. Answers are grounded in hospital data through **retrieval-augmented generation (RAG)**, and authorized staff can dispense medicine from Arduino-controlled trays.

> Part of the Autonomous Hospital Delivery Robot project. The navigation stack lives in [Hospital-delivery-robot](https://github.com/KHAAA123/Hospital-delivery-robot).

---

## ✨ Features

- 🎤 **Voice conversation** with the Gemini Live API (Vietnamese and English), using short-lived tokens so the API key stays on the server
- 🧠 **Hybrid RAG engine** over 223 hospital records (doctors, schedules, departments, service packages, FAQs, policies)
  - exact and alias matching, local BM25, and reciprocal rank fusion
  - optional **dense retrieval with an ONNX embedding model on the Jetson Nano**, with automatic fallback to lexical search
  - safety gates: no diagnosis or prescriptions, and the RAG engine never triggers the medicine trays
- 💊 **Medicine dispensing**: upload orders from Excel, look up a patient order, open the right tray and door through Arduino
- 🛒 **Pharmacity product Q&A** module
- 🖥 **Touch-first kiosk web UI** with QR scanning and a doctor area
- ✅ **58 unit tests** covering order validation, configuration, Arduino control, dispensing, RAG and login

## 🏗 Architecture

```text
            Patient / staff
                  │  voice · touch · QR
                  ▼
     Kiosk web UI (HTML / CSS / JS)
                  │  HTTP (localhost)
                  ▼
      Python backend (server.py) ─────────────► Gemini Live API
       │            │            │                (ephemeral token)
       ▼            ▼            ▼
   RAG engine   Pharmacity   Medicine dispensing
  (lexical +    module        workflow
   ONNX dense)                   │ serial
                                 ▼
                    Arduino: trays and doors
```

## 📂 Project structure

```text
├── server.py               # Backend: web UI, /robot/api/* endpoints, dispensing workflow, Arduino manager
├── test_server_safety.py   # Backend tests
├── RAG/                    # RAG engine, dense retrieval, dataset (hanhphuc.jsonl), tests
├── pharmacity_chatbot/     # Pharmacity product search and Q&A, tests
├── Web_emoji/              # Kiosk web UI
├── Arduino/                # Firmware for trays (Khay), doors (Cua) and combined (Cua_Khay)
├── docs/
│   ├── SETUP_vi.md         # Detailed Jetson setup guide (Vietnamese)
│   ├── PROJECT_GOALS.md    # Requirements and acceptance criteria
│   └── STYLE_GUIDE.md      # UI style guide
├── requirements.txt
└── .env.example
```

## 🛠 Technologies

| Category | Technologies |
|---|---|
| Languages | Python, JavaScript, Arduino C++ |
| LLM | Gemini API, Gemini Live (voice) |
| Retrieval | BM25, reciprocal rank fusion, ONNX Runtime embeddings |
| Backend | Python standard-library HTTP server |
| Frontend | HTML, CSS, JavaScript |
| Hardware | NVIDIA Jetson Nano, Arduino |
| Data | openpyxl (Excel orders), pyserial |

## 🚀 Installation

```bash
git clone https://github.com/KHAAA123/AI-Medical-Assistant-Robot.git
cd AI-Medical-Assistant-Robot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then set GEMINI_API_KEY, DOCTOR_PASSWORD and ARDUINO_PORT
python server.py         # open http://127.0.0.1:8000
```

Run the tests:

```bash
python -m unittest test_server_safety RAG.test_rag_engine pharmacity_chatbot.tests.test_pharmacity_service
```

See [docs/SETUP_vi.md](docs/SETUP_vi.md) for the full Jetson setup, including serial-port permissions and the optional dense-retrieval model.

## 🔒 Security notes

- API keys and the doctor password are read from `.env` on the server and are never sent to the browser.
- The doctor login is checked by the backend (`/robot/api/doctor/login`).
- The robot-control endpoints do not have their own authentication yet, so the app is bound to `127.0.0.1` by default and should only run on the kiosk itself or a closed network.

## 📚 Data sources

- `RAG/hanhphuc.jsonl`: public information collected from the website of Hanh Phuc Hospital (hanhphuchospital.com). Every record keeps its `source_url`.
- Pharmacity product data is fetched from the public pharmacity.vn website at query time.

This project is an academic prototype and is not affiliated with either organization. It does not give medical advice.

## 🔬 Future work

- ROS 2 integration with the navigation stack
- Server-side authentication for all robot-control endpoints
- Hospital Information System (HIS) and electronic medical record (EMR) integration
- Face recognition for patient check-in

## 👥 Team

UEH Robotics and Artificial Intelligence – Hospital Service Robot Project, University of Economics Ho Chi Minh City (UEH).

## 📄 License

Academic and research use.
