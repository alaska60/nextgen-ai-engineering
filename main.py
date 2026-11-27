import os
import base64
import httpx

from io import BytesIO
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="NEXTGEN AI BRAIN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-20b")
VISION_MODEL = "qwen/qwen3.8-27b"


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {
        "name": "NEXTGEN AI BRAIN",
        "status": "online"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/chat")
async def chat(data: ChatRequest):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(500, "AI key is not configured")

    if not data.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI CREATOR. "
                    "Understand Cebuano and English. "
                    "Help with coding, games, apps, "
                    "creative projects and analysis. "
                    "Be honest about limitations."
                )
            },
            {
                "role": "user",
                "content": data.message
            }
        ],
        "temperature": 0.5,
        "max_completion_tokens": 2000
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=payload
            )

        if response.status_code != 200:
            raise HTTPException(
                502,
                f"Groq error {response.status_code}: "
                f"{response.text[:300]}"
            )

        result = response.json()

        return {
            "reply": result["choices"][0]["message"]["content"],
            "model": MODEL
        }

    except httpx.RequestError:
        raise HTTPException(
            503,
            "Could not connect to AI provider"
        )


@app.post("/api/analyze-image")
async def analyze_image(
    image: UploadFile = File(...),
    prompt: str = Form(
        "Describe this image clearly and briefly."
    )
):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(500, "AI key is not configured")

    allowed_types = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]

    if image.content_type not in allowed_types:
        raise HTTPException(
            400,
            "Only JPG, PNG and WEBP images are supported."
        )

    image_data = await image.read()

    if not image_data:
        raise HTTPException(400, "Image is empty.")

    if len(image_data) > 10 * 1024 * 1024:
        raise HTTPException(
            413,
            "Image must be 10 MB or smaller."
        )

    encoded_image = base64.b64encode(
        image_data
    ).decode("utf-8")

    image_url = (
        f"data:{image.content_type};base64,{encoded_image}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.5,
        "max_completion_tokens": 300
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=payload
            )

        if response.status_code != 200:
            raise HTTPException(
                502,
                f"Image AI error {response.status_code}: "
                f"{response.text[:300]}"
            )

        result = response.json()

        return {
            "reply": result["choices"][0]["message"]["content"],
            "model": VISION_MODEL,
            "filename": image.filename
        }

    except httpx.RequestError:
        raise HTTPException(
            503,
            "Could not connect to image AI provider"
        )


@app.post("/api/analyze-file")
async def analyze_file(file: UploadFile = File(...)):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(500, "AI key is not configured")

    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()

    allowed_extensions = [
        ".txt",
        ".pdf",
        ".docx",
        ".xlsx"
    ]

    if extension not in allowed_extensions:
        raise HTTPException(
            400,
            "Supported files: TXT, PDF, DOCX and XLSX."
        )

    data = await file.read()

    if not data:
        raise HTTPException(400, "File is empty.")

    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(
            413,
            "File must be 10 MB or smaller."
        )

    try:

        if extension == ".txt":
            content = data.decode("utf-8-sig")

        elif extension == ".pdf":
            reader = PdfReader(BytesIO(data))

            content = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        elif extension == ".docx":
            document = Document(BytesIO(data))

            content = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

        elif extension == ".xlsx":
            workbook = load_workbook(
                BytesIO(data),
                read_only=True,
                data_only=True
            )

            rows = []

            for sheet in workbook.worksheets:
                rows.append(f"Sheet: {sheet.title}")

                for row in sheet.iter_rows(values_only=True):
                    rows.append(
                        " | ".join(
                            str(value) if value is not None else ""
                            for value in row
                        )
                    )

            content = "\n".join(rows)
            workbook.close()

    except Exception:
        raise HTTPException(
            400,
            "Could not read this file. Please check the file format."
        )

    if not content.strip():
        raise HTTPException(
            400,
            "No readable text found in this file."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI CREATOR. "
                    "Analyze uploaded documents and files. "
                    "Understand Cebuano and English. "
                    "Explain the contents clearly."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Analyze this file: {filename}\n\n"
                    f"File contents:\n{content[:12000]}"
                )
            }
        ],
        "temperature": 0.5,
        "max_completion_tokens": 1500
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=payload
            )

        if response.status_code != 200:
            raise HTTPException(
                502,
                f"File AI error {response.status_code}: "
                f"{response.text[:300]}"
            )

        result = response.json()

        return {
            "reply": result["choices"][0]["message"]["content"],
            "filename": filename,
            "model": MODEL
        }

    except httpx.RequestError:
        raise HTTPException(
            503,
            "Could not connect to AI provider"
        )
