# AI-Medical-Assistant-Robot
# 🤖 AI Medical Assistant Robot for Hospitals

An intelligent medical assistant system designed for hospital environments, integrating **Large Language Models (LLMs)**, **Retrieval-Augmented Generation (RAG)**, speech interaction, and embedded hardware control on **Jetson Nano**.

The system enables patients to communicate naturally with an AI assistant while interacting with a medicine delivery robot capable of opening storage trays and providing healthcare information.

---

## ✨ Features

- 🤖 AI-powered medical assistant
- 🧠 Retrieval-Augmented Generation (RAG)
- 💬 Natural language conversation
- 🎤 Voice interaction
- 🌐 Web-based user interface
- 💊 Medicine information retrieval
- 🚪 Arduino-controlled medicine tray
- 📷 QR code support
- ⚡ Optimized for NVIDIA Jetson Nano

---

## 🏗 System Architecture

```text
                User
                 │
                 ▼
        Web Interface (HTML/CSS/JS)
                 │
                 ▼
          Python Backend Server
                 │
      ┌──────────┴──────────┐
      │                     │
      ▼                     ▼
 Gemini Live API        RAG Engine
      │                     │
      └──────────┬──────────┘
                 ▼
         Response Generation
                 │
                 ▼
        Arduino Serial Control
                 │
                 ▼
        Medicine Tray Hardware
```

---

## 📂 Project Structure

```text
chatbot-y-te-jetson/

├── Arduino/
│   ├── Cua/
│   ├── Cua_Khay/
│   ├── Khay/
│   └── README.md
│
├── RAG/
│   ├── build_embeddings.py
│   ├── dense_retrieval.py
│   ├── rag_engine.py
│   ├── test_rag_engine.py
│   ├── hanhphuc.jsonl
│   └── README.md
│
├── pharmacity_chatbot/
│   ├── web/
│   ├── tests/
│   ├── server.py
│   ├── pharmacity_service.py
│   ├── gemini_live_tools.py
│   ├── requirements.txt
│   └── README.md
│
├── Web_emoji/
│   ├── assets/
│   ├── vendor/
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── server.py
├── requirements.txt
├── PROJECT_GOALS.md
├── .env.example
└── README.md
```

---

## 🛠 Technologies

| Category | Technologies |
|-----------|-------------|
| Programming | Python, JavaScript, Arduino C++ |
| AI | Gemini API |
| Retrieval | RAG |
| Backend | Flask / Python Server |
| Frontend | HTML, CSS, JavaScript |
| Hardware | Jetson Nano, Arduino |
| Communication | Serial, HTTP |

---

## 🚀 Installation

Clone repository

```bash
git clone https://github.com/yourusername/chatbot-y-te-jetson.git
```

Install dependencies

```bash
pip install -r requirements.txt
```

Configure environment variables

```bash
cp .env.example .env
```

Run server

```bash
python server.py
```

---

## 📖 Components

### AI Chatbot

Provides conversational medical assistance using LLMs.

### RAG Module

Retrieves domain-specific knowledge before generating responses, improving factual accuracy.

### Web Interface

Interactive browser-based interface supporting text and voice interaction.

### Arduino Controller

Controls medicine trays and mechanical components through serial communication.

---

## 📸 Screenshots

> Add screenshots of:

- Main interface
- Conversation page
- Robot hardware
- Medicine tray
- Jetson Nano setup

---

## 🔬 Future Work

- ROS2 integration
- Navigation support
- Face recognition
- Multilingual interaction
- Hospital Information System (HIS) integration
- Electronic Medical Record (EMR) support

---

## 👨‍💻 Authors

**UEH Robotics & Artificial Intelligence**

Hospital Service Robot Project

---

## 📄 License

This project is intended for academic and research purposes.
