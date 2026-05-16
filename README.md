# 🧠 DocMind — RAG Document Chatbot

An AI-powered chatbot that lets you upload any PDF or text file 
and ask questions about it using natural language.

## 🛠️ Built With
- **LangChain** — AI pipeline
- **ChromaDB** — Vector database
- **FastAPI** — Backend API
- **OpenAI GPT-4o-mini** — Language model
- **HTML/CSS/JS** — Frontend UI

## ✨ Features
- Upload PDF or TXT files
- Ask questions in natural language
- Get answers with source citations
- Conversation memory
- Beautiful dark pink & blue UI

  
  Project Structure
  rag-doc-qa/
├── backend/
│   ├── main.py          # FastAPI app — /upload and /query endpoints
│   ├── ingestor.py      # PDF loading + recursive chunking
│   ├── embedder.py      # Embedding + ChromaDB persistence
│   ├── retriever.py     # Vector similarity search (top-k)
│   └── chain.py         # LangChain RAG chain with custom prompt
├── frontend/
│   └── app.py           # Streamlit UI
├── vectorstore/         # ChromaDB data (auto-created, gitignored)
├── uploads/             # Uploaded PDFs (gitignored)
├── .env.example
├── requirements.txt
└── README.md

## 🚀 How to Run
1. Clone the repo
2. Create `.env` file with your `OPENAI_API_KEY`
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn backend.main:app --reload`
5. Open `frontend/index.html` in browser
