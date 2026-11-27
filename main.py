import os
import base64
import csv
import httpx
import ast
import operator
import json

from io import BytesIO, StringIO
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

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


class PluginRequest(BaseModel):
    plugin: str
    input: str


# =====================================
# HOME AND HEALTH
# =====================================

@app.get("/")
def home():
    return {
        "name": "NEXTGEN AI BRAIN",
        "status": "online",
        "plugins": True
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# =====================================
# AI CHAT
# =====================================

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


# =====================================
# AI IMAGE ANALYSIS
# =====================================

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


# =====================================
# AI FILE ANALYSIS
# =====================================

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
        ".xlsx",
        ".pptx",
        ".csv"
    ]

    if extension not in allowed_extensions:
        raise HTTPException(
            400,
            "Supported files: TXT, PDF, DOCX, XLSX, PPTX and CSV."
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

        elif extension == ".pptx":
            presentation = Presentation(BytesIO(data))

            slides_text = []

            for slide_number, slide in enumerate(
                presentation.slides, start=1
            ):
                slides_text.append(f"Slide {slide_number}:")

                for shape in slide.shapes:
                    if shape.has_text_frame:
                        slides_text.append(shape.text)

                    if shape.has_table:
                        for row in shape.table.rows:
                            slides_text.append(
                                " | ".join(
                                    cell.text for cell in row.cells
                                )
                            )

            content = "\n".join(slides_text)

        elif extension == ".csv":
            decoded = data.decode("utf-8-sig")
            reader = csv.reader(StringIO(decoded))

            content = "\n".join(
                " | ".join(row)
                for row in reader
            )

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


# =====================================
# NEXTGEN AI PLUGINS
# =====================================

@app.get("/api/plugins")
def list_plugins():

    return {
        "plugins": [
            {
                "id": "calculator",
                "name": "Calculator",
                "description": "Perform mathematical calculations."
            },
            {
                "id": "text_analyzer",
                "name": "Text Analyzer",
                "description": "Count words, characters and lines."
            },
            {
                "id": "json_formatter",
                "name": "JSON Formatter",
                "description": "Format and validate JSON data."
            }
        ]
    }


@app.post("/api/plugins/run")
def run_plugin(data: PluginRequest):

    if len(data.input) > 10000:
        raise HTTPException(
            413,
            "Plugin input is too large."
        )

    # -----------------------------
    # CALCULATOR PLUGIN
    # -----------------------------

    if data.plugin == "calculator":

        allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos
        }

        def calculate(node):

            if isinstance(node, ast.Constant):
                if type(node.value) not in (int, float):
                    raise ValueError("Only numbers are allowed.")

                if abs(node.value) > 1000000000:
                    raise ValueError("Number is too large.")

                return node.value

            if isinstance(node, ast.BinOp):

                op = allowed_operators.get(type(node.op))

                if op is None:
                    raise ValueError("Unsupported operation.")

                left = calculate(node.left)
                right = calculate(node.right)

                if isinstance(node.op, ast.Pow):
                    if abs(right) > 10:
                        raise ValueError("Exponent is too large.")

                answer = op(left, right)

                if abs(answer) > 1e100:
                    raise ValueError("Result is too large.")

                return answer

            if isinstance(node, ast.UnaryOp):

                op = allowed_operators.get(type(node.op))

                if op is None:
                    raise ValueError("Unsupported operation.")

                return op(calculate(node.operand))

            raise ValueError("Invalid mathematical expression.")

        try:

            if not data.input.strip():
                raise ValueError("Enter a calculation first.")

            tree = ast.parse(data.input, mode="eval")
            answer = calculate(tree.body)

            return {
                "plugin": "calculator",
                "result": answer
            }

        except Exception as error:
            raise HTTPException(400, str(error))

    # -----------------------------
    # TEXT ANALYZER PLUGIN
    # -----------------------------

    elif data.plugin == "text_analyzer":

        text = data.input

        return {
            "plugin": "text_analyzer",
            "characters": len(text),
            "words": len(text.split()),
            "lines": len(text.splitlines())
        }

    # -----------------------------
    # JSON FORMATTER PLUGIN
    # -----------------------------

    elif data.plugin == "json_formatter":

        try:

            parsed = json.loads(data.input)

            return {
                "plugin": "json_formatter",
                "valid": True,
                "result": json.dumps(
                    parsed,
                    indent=2,
                    ensure_ascii=False
                )
            }

        except json.JSONDecodeError as error:

            raise HTTPException(
                400,
                f"Invalid JSON: {error}"
            )

    else:

        raise HTTPException(
            404,
            "Plugin not found."
        )
