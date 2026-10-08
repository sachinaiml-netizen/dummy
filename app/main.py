from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader

from .assistant import DEFAULT_DOCS, KnowledgeDoc, answer_query
from .risk import assess_risk
from .schemas import ProjectTelemetry, RiskResponse

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="ProjectIQ — AI Knowledge Assistant",
    version="2.1.0",
    description="Project risk assessment plus a document-grounded AI assistant demo.",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

knowledge_base = list(DEFAULT_DOCS)


class QueryRequest(BaseModel):
    question: str


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/risk", response_model=RiskResponse)
def risk(project: ProjectTelemetry) -> RiskResponse:
    result = assess_risk(project)
    return RiskResponse(project_id=project.project_id, **result)


@app.post("/assistant/query")
def assistant_query(payload: QueryRequest):
    return answer_query(payload.question, knowledge_base)


@app.post("/assistant/upload")
async def assistant_upload(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return {"status": "error", "message": "Please upload a PDF file."}

    contents = await file.read()
    reader = PdfReader(BytesIO(contents))
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(pages).strip()

    if not text:
        return {"status": "error", "message": "No readable text was found in the PDF."}

    knowledge_base.append(KnowledgeDoc(name=file.filename or "Uploaded PDF", text=text))
    return {
        "status": "ok",
        "filename": file.filename,
        "pages": len(reader.pages),
        "characters_indexed": len(text),
    }
