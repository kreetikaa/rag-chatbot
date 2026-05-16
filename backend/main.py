import os
import uuid
import shutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
CHROMA_DIR = Path("chroma_db")
sessions = {}

class ChatRequest(BaseModel):
    session_id: str
    question: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/session/create")
def create_session():
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "files": [],
        "vectorstore": None,
        "chunk_count": 0,
        "history": [],
    }
    return {"session_id": session_id}

@app.post("/upload/{session_id}")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    file_path = session_dir / file.filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif suffix in (".txt", ".md"):
        loader = TextLoader(str(file_path), encoding="utf-8")
    else:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files supported")

    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
    )
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    chroma_path = str(CHROMA_DIR / session_id)

    if sessions[session_id]["vectorstore"] is None:
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=chroma_path,
        )
    else:
        sessions[session_id]["vectorstore"].add_documents(chunks)
        vectorstore = sessions[session_id]["vectorstore"]

    sessions[session_id]["vectorstore"] = vectorstore
    sessions[session_id]["files"].append(file.filename)
    sessions[session_id]["chunk_count"] += len(chunks)

    return {
        "filename": file.filename,
        "chunks_created": len(chunks),
        "total_chunks": sessions[session_id]["chunk_count"],
    }

@app.post("/chat")
def chat(req: ChatRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["vectorstore"] is None:
        raise HTTPException(status_code=400, detail="No documents uploaded yet")

    vectorstore = session["vectorstore"]
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(req.question)

    context = "\n\n".join([doc.page_content for doc in docs])

    history_text = ""
    for h in session["history"][-6:]:
        history_text += f"User: {h['question']}\nAssistant: {h['answer']}\n"

    prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. Answer the question based on the context below.
If the answer is not in the context, say "I don't know based on the provided documents."

Previous conversation:
{history}

Context from documents:
{context}

Question: {question}

Answer:""")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "history": history_text,
        "context": context,
        "question": req.question,
    })

    session["history"].append({
        "question": req.question,
        "answer": answer,
    })

    sources = []
    for doc in docs:
        meta = doc.metadata
        src = meta.get("source", "Unknown")
        page = meta.get("page", None)
        label = Path(src).name
        if page is not None:
            label += f" (page {page + 1})"