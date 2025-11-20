# ⚖️ NyaySaathi

> **Your AI-Powered Legal Companion for India**  
> *Empowering citizens with verified legal information through RAG-based AI chat, curated learning, and document analysis.*

---

## 🚀 Overview

**NyaySaathi** is a cutting-edge legal assistant designed to demystify Indian law. By combining the power of Large Language Models (LLMs) with a local Retrieval-Augmented Generation (RAG) engine, it provides accurate, citation-backed answers from your own legal corpus.

No complex infrastructure required—runs entirely locally with **FastAPI**, **React**, and **Local Qdrant**.

## ✨ Key Features

- **🤖 AI Legal Chatbot**: Ask questions in natural language (English & Indian languages) and get precise answers based on the Constitution and uploaded laws.
- **📄 Document Ingestion**: Upload PDF, DOCX, or TXT files via the Admin Portal. They are automatically chunked, embedded, and stored locally.
- **🔍 RAG Engine**: Uses **Qdrant (Local)** to retrieve relevant legal context before answering, reducing hallucinations.
- **🎓 NyayShala**: Daily curated legal snippets to improve legal literacy.
- **👓 NyayLens**: Deep dive into specific documents with "Lens" mode.
- **⚡ Real-time Streaming**: Fast, typewriter-style responses using Server-Sent Events (SSE).
- **🛠️ Zero-Docker Setup**: Runs natively on your machine without heavy container requirements.

---

## 🛠️ Tech Stack

### **Backend**
- **Framework**: FastAPI (Python)
- **Vector Database**: Qdrant (Local Mode - no server required)
- **LLM Providers**: Google Gemini 2.0 Flash / OpenAI GPT-4o
- **Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2` / `bge-m3`)
- **Processing**: PyMuPDF, python-docx

### **Frontend**
- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **Animations**: Framer Motion

---

## ⚡ Quick Start Guide

Follow these steps to get the entire system running in minutes.

### 1️⃣ Prerequisites
- **Python 3.10+** installed.
- **Node.js 18+** installed.
- An API Key for **Google Gemini** (Free tier available) or **OpenAI**.

### 2️⃣ Clone the Repository
```bash
git clone https://github.com/vasu-devs/AIU1.git
cd AIU1/NyaySaathi
```

### 3️⃣ Backend Setup
The backend handles the AI logic, database, and file processing.

1.  **Navigate to Backend:**
    ```bash
    cd Backend
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Create a `.env` file in the `Backend` folder:
    ```env
    # LLM Provider (google or openai)
    LLM_PROVIDER=google
    LLM_MODEL=gemini-2.0-flash
    
    # API Keys (Add yours)
    GOOGLE_API_KEY=your_google_api_key_here
    # OPENAI_API_KEY=your_openai_key_here
    
    # App Settings
    API_PREFIX=/api
    CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]
    
    # Local Vector Store (No setup needed)
    QDRANT_PATH=.qdrant_data
    ```

4.  **Start the Server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    *The backend will start at `http://127.0.0.1:8000`.*

### 4️⃣ Frontend Setup
The frontend provides the beautiful chat interface.

1.  **Open a new terminal** and navigate to Frontend:
    ```bash
    cd ../Frontend
    ```

2.  **Install Dependencies:**
    ```bash
    npm install
    ```

3.  **Start the UI:**
    ```bash
    npm run dev
    ```
    *The frontend will start at `http://localhost:5173` (or 5174 if port is busy).*

---

## 📖 How to Use

### 1. Admin Portal (Upload Documents)
- Go to `http://localhost:5173/admin` (or click the Admin icon in the sidebar).
- Login with default credentials:
    - **Email**: `admin@example.com`
    - **Password**: `admin123`
- **Upload**: Select a legal PDF/DOCX (e.g., "Constitution of India").
- **Status**: Watch the status change to "Processing" and then "Ready". The system chunks and indexes the file locally in seconds.

### 2. Chat with NyaySaathi
- Go to the **Home** or **Chat** tab.
- Ask a question like:
    > *"What are my fundamental rights under Article 21?"*
- The AI will search your uploaded documents and provide a cited answer.

### 3. NyayLens
- Navigate to **NyayLens**.
- Select a specific uploaded document to ask questions *only* about that file.

---

## 📂 Project Structure

```
NyaySaathi/
├── Backend/
│   ├── app/
│   │   ├── api/            # API Routes (Chat, Admin, Auth)
│   │   ├── core/           # Config & Security
│   │   ├── services/       # Business Logic (RAG, Ingestion, Vector Store)
│   │   └── utils/          # Helpers (Text Splitting)
│   ├── .qdrant_data/       # Local Vector Database (Auto-created)
│   ├── .data/              # Uploaded files storage
│   └── requirements.txt    # Python dependencies
│
├── Frontend/
│   ├── src/
│   │   ├── components/     # React Components (Chatbot, Admin, etc.)
│   │   ├── lib/            # API Client
│   │   └── App.jsx         # Main Entry
│   └── package.json        # Node dependencies
│
└── README.md               # You are here!
```

---

## 🔧 Troubleshooting

- **Port in use?**
    - If `5173` is busy, Vite will auto-switch to `5174`. The backend is configured to allow both.
- **Qdrant Error?**
    - If you see errors about `Qdrant`, ensure you are **not** running a Docker container for it. The system now uses the local Python client. Delete the `.qdrant_data` folder to reset the database if needed.
- **Ingestion Stuck?**
    - Check the backend terminal logs. Large files might take a moment. The system uses background tasks to process files without blocking the UI.

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.
