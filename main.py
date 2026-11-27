import os
import base64
import csv
import httpx
import ast
import operator
import json

from io import BytesIO, StringIO
from typing import Optional

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =====================================
# NEXTGEN AI BRAIN
# =====================================

app = FastAPI(
    title="NEXTGEN AI BRAIN",
    description="NEXTGEN AI CREATOR and GAME DEVELOPMENT ENGINE",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL = os.getenv(
    "AI_MODEL",
    "openai/gpt-oss-20b"
)

VISION_MODEL = os.getenv(
    "VISION_MODEL",
    "qwen/qwen3.8-27b"
)


# =====================================
# REQUEST MODELS
# =====================================

class ChatRequest(BaseModel):
    message: str


class PluginRequest(BaseModel):
    plugin: str
    input: str


class SmartAnalysisRequest(BaseModel):
    project_name: str = ""
    project_type: str = ""
    description: str = ""
    content: str = ""


class GameRequest(BaseModel):
    game_name: str = "My Game"
    engine: str = "Godot 4"
    task: str = "create_project"
    description: str
    existing_code: str = ""


# =====================================
# AI PROVIDER FUNCTION
# =====================================

async def ask_ai(
    messages,
    model=None,
    temperature=0.5,
    max_tokens=3000
):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            500,
            "AI key is not configured."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model or MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens
    }

    try:

        async with httpx.AsyncClient(timeout=150) as client:

            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=payload
            )

        if response.status_code != 200:

            raise HTTPException(
                502,
                f"AI provider error {response.status_code}: "
                f"{response.text[:300]}"
            )

        result = response.json()

        choices = result.get("choices", [])

        if not choices:
            raise HTTPException(
                502,
                "AI provider returned an empty response."
            )

        return choices[0]["message"]["content"]

    except httpx.RequestError:

        raise HTTPException(
            503,
            "Could not connect to AI provider."
        )


# =====================================
# HOME AND HEALTH
# =====================================

@app.get("/")
def home():

    return {
        "name": "NEXTGEN AI BRAIN",
        "version": "2.0.0",
        "status": "online",
        "features": [
            "AI Chat",
            "Image Analysis",
            "File Analysis",
            "Smart Analysis",
            "Plugins",
            "AI Game Creator",
            "Godot Project Generator",
            "Code Reviewer",
            "Bug Fixer",
            "Android Optimization"
        ]
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "engine": "NEXTGEN AI BRAIN"
    }


# =====================================
# AI CHAT
# =====================================

@app.post("/api/chat")
async def chat(data: ChatRequest):

    if not data.message.strip():
        raise HTTPException(
            400,
            "Message cannot be empty."
        )

    answer = await ask_ai(
        [
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI CREATOR, an advanced "
                    "AI engineering assistant. "
                    "Understand Cebuano, Filipino and English. "
                    "Help users create games, Android apps, "
                    "websites, software and creative projects. "
                    "You are also a professional Godot 4 "
                    "game development assistant. "
                    "When generating code, provide complete "
                    "code, exact filenames and folder structure. "
                    "Explain installation and testing. "
                    "Never claim code was executed or tested "
                    "unless it actually was. "
                    "Never invent completed features. "
                    "Prefer free tools and solutions."
                )
            },
            {
                "role": "user",
                "content": data.message
            }
        ],
        max_tokens=4000
    )

    return {
        "reply": answer,
        "response": answer,
        "model": MODEL
    }


# =====================================
# IMAGE ANALYSIS
# Accepts both image and file fields
# =====================================

@app.post("/api/analyze-image")
async def analyze_image(
    image: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    prompt: str = Form(
        "Describe this image clearly and briefly."
    )
):

    uploaded = image or file

    if uploaded is None:
        raise HTTPException(
            400,
            "Please upload an image using image or file."
        )

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            500,
            "AI key is not configured."
        )

    allowed_types = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]

    if uploaded.content_type not in allowed_types:
        raise HTTPException(
            400,
            "Only JPG, PNG and WEBP images are supported."
        )

    image_data = await uploaded.read()

    if not image_data:
        raise HTTPException(
            400,
            "Image is empty."
        )

    if len(image_data) > 10 * 1024 * 1024:
        raise HTTPException(
            413,
            "Image must be 10 MB or smaller."
        )

    encoded = base64.b64encode(
        image_data
    ).decode("utf-8")

    image_url = (
        f"data:{uploaded.content_type};base64,{encoded}"
    )

    answer = await ask_ai(
        [
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
        model=VISION_MODEL,
        max_tokens=1500
    )

    return {
        "reply": answer,
        "response": answer,
        "analysis": answer,
        "filename": uploaded.filename,
        "model": VISION_MODEL
    }


# =====================================
# FILE ANALYSIS
# =====================================

@app.post("/api/analyze-file")
async def analyze_file(
    file: UploadFile = File(...)
):

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
        raise HTTPException(
            400,
            "File is empty."
        )

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

                rows.append(
                    f"Sheet: {sheet.title}"
                )

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

            presentation = Presentation(
                BytesIO(data)
            )

            slides = []

            for number, slide in enumerate(
                presentation.slides,
                start=1
            ):

                slides.append(
                    f"Slide {number}:"
                )

                for shape in slide.shapes:

                    if shape.has_text_frame:
                        slides.append(shape.text)

                    if shape.has_table:

                        for row in shape.table.rows:

                            slides.append(
                                " | ".join(
                                    cell.text
                                    for cell in row.cells
                                )
                            )

            content = "\n".join(slides)

        elif extension == ".csv":

            decoded = data.decode("utf-8-sig")

            reader = csv.reader(
                StringIO(decoded)
            )

            content = "\n".join(
                " | ".join(row)
                for row in reader
            )

    except Exception:

        raise HTTPException(
            400,
            "Could not read this file. Check its format."
        )

    if not content.strip():
        raise HTTPException(
            400,
            "No readable text found."
        )

    answer = await ask_ai(
        [
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI CREATOR. "
                    "Analyze documents carefully. "
                    "Explain the contents clearly in Cebuano "
                    "or English depending on the user."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Analyze this file: {filename}\n\n"
                    f"Contents:\n{content[:12000]}"
                )
            }
        ],
        max_tokens=2500
    )

    return {
        "reply": answer,
        "response": answer,
        "analysis": answer,
        "filename": filename,
        "model": MODEL
    }


# =====================================
# SMART ANALYSIS
# Supports old and new frontend fields
# =====================================

@app.post("/api/smart-analysis")
async def smart_analysis(
    data: SmartAnalysisRequest
):

    project_name = (
        data.project_name.strip()
        or "Unnamed Project"
    )

    project_type = (
        data.project_type.strip()
        or "General Project"
    )

    description = (
        data.description.strip()
        or data.content.strip()
    )

    if not description:
        raise HTTPException(
            400,
            "Please provide project information to analyze."
        )

    if (
        len(project_name) > 200
        or len(project_type) > 100
        or len(description) > 10000
    ):
        raise HTTPException(
            413,
            "Project information is too long."
        )

    answer = await ask_ai(
        [
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN SMART ANALYSIS. "
                    "Analyze projects carefully. "
                    "Identify strengths, weaknesses, risks "
                    "and improvements. "
                    "Give an estimated quality score from "
                    "1 to 100. Explain that this is an AI "
                    "estimate, not a verified test result. "
                    "Never claim that you executed or tested "
                    "the project if you did not. "
                    "Understand Cebuano and English."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Project: {project_name}\n"
                    f"Type: {project_type}\n"
                    f"Description:\n{description}\n\n"
                    "Provide:\n"
                    "1. Overall analysis\n"
                    "2. Strengths\n"
                    "3. Problems\n"
                    "4. Estimated score out of 100\n"
                    "5. Improvements\n"
                    "6. Testing plan\n"
                    "7. Recommendations"
                )
            }
        ],
        temperature=0.4,
        max_tokens=3000
    )

    return {
        "success": True,
        "analysis": answer,
        "response": answer,
        "project_name": project_name,
        "model": MODEL
    }


# =====================================
# AI GAME CREATOR
# =====================================

GAME_TASKS = {

    "create_project": (
        "Create a complete starter game project. "
        "Include folder structure, scenes, scripts, "
        "project configuration and setup instructions."
    ),

    "generate": (
        "Generate complete Godot 4 game files "
        "with exact filenames and complete source code."
    ),

    "player": (
        "Create a complete player controller with "
        "movement, jumping, health, animations, "
        "inventory and Android touch controls."
    ),

    "animal": (
        "Create intelligent animal AI. Animals should "
        "find food and water, eat, drink, rest, sleep, "
        "reproduce, care for babies and react to danger."
    ),

    "monster": (
        "Create monster AI with detection, chasing, "
        "attacking, fleeing, hunting and special abilities."
    ),

    "world": (
        "Create world generation with terrain, "
        "biomes, chunks, caves and environmental systems."
    ),

    "npc": (
        "Create NPC and villager AI with jobs, homes, "
        "conversations, trading and daily routines."
    ),

    "combat": (
        "Create weapons, armor, health, damage, "
        "defense and combat mechanics."
    ),

    "inventory": (
        "Create inventory, hotbar, crafting, "
        "equipment, storage and item management."
    ),

    "review": (
        "Review the supplied game code. Find errors, "
        "missing dependencies and design problems."
    ),

    "fix": (
        "Find bugs and provide corrected complete code. "
        "Explain the changes."
    ),

    "optimize": (
        "Optimize the game for Android devices with "
        "limited memory and processing power."
    )
}


@app.post("/api/game/create")
async def create_game(
    data: GameRequest
):

    if not data.description.strip():
        raise HTTPException(
            400,
            "Please describe the game or feature."
        )

    task = GAME_TASKS.get(data.task)

    if task is None:
        raise HTTPException(
            400,
            "Unknown game development task."
        )

    if len(data.description) > 12000:
        raise HTTPException(
            413,
            "Game request is too long."
        )

    if len(data.existing_code) > 20000:
        raise HTTPException(
            413,
            "Existing code is too long."
        )

    message = f"""
GAME NAME:
{data.game_name}

GAME ENGINE:
{data.engine}

TASK:
{task}

USER REQUEST:
{data.description}

EXISTING CODE:
{data.existing_code or "No existing code supplied."}

DEVELOPMENT RULES:

1. Use Godot 4 and GDScript when Godot is selected.
2. Give exact project folder structure.
3. Give exact filenames.
4. Provide complete code, not incomplete snippets.
5. Explain scene nodes and their configuration.
6. Include dependencies.
7. Explain installation and testing.
8. Review code for possible errors.
9. Never claim code was executed or tested if it was not.
10. Mention features that are not implemented.
11. Prefer free tools.
12. Design the project for future expansion.
13. Keep Android performance in mind.

ORGANIZE YOUR ANSWER:

A. Project Structure
B. Complete Files and Code
C. Scene Setup
D. Installation Instructions
E. Testing Instructions
F. Known Limitations
"""

    answer = await ask_ai(
        [
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI GAME CREATOR, "
                    "a professional game development assistant. "
                    "Your job is to generate organized, "
                    "complete and maintainable game source code. "
                    "Be honest about limitations."
                )
            },
            {
                "role": "user",
                "content": message
            }
        ],
        temperature=0.3,
        max_tokens=6000
    )

    return {
        "success": True,
        "game_name": data.game_name,
        "engine": data.engine,
        "task": data.task,
        "project_output": answer,
        "model": MODEL,
        "tested": False,
        "note": (
            "Generated code must still be installed, "
            "executed and tested in the game engine."
        )
    }


# =====================================
# GAME DEVELOPMENT TASK LIST
# =====================================

@app.get("/api/game/tasks")
def game_tasks():

    return {
        "engine": "Godot 4",
        "tasks": [
            {
                "id": key,
                "description": value
            }
            for key, value in GAME_TASKS.items()
        ]
    }


# =====================================
# AI PLUGINS
# =====================================

@app.get("/api/plugins")
def list_plugins():

    return {
        "plugins": [
            {
                "id": "calculator",
                "name": "Calculator",
                "description": "Mathematical calculations."
            },
            {
                "id": "text_analyzer",
                "name": "Text Analyzer",
                "description": "Count characters, words and lines."
            },
            {
                "id": "json_formatter",
                "name": "JSON Formatter",
                "description": "Format and validate JSON."
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

    # CALCULATOR

    if data.plugin == "calculator":

        allowed = {
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

                return node.value

            if isinstance(node, ast.BinOp):

                op = allowed.get(type(node.op))

                if op is None:
                    raise ValueError("Unsupported operation.")

                left = calculate(node.left)
                right = calculate(node.right)

                if isinstance(node.op, ast.Pow):
                    if abs(right) > 10:
                        raise ValueError("Exponent too large.")

                result = op(left, right)

                if abs(result) > 1e100:
                    raise ValueError("Result too large.")

                return result

            if isinstance(node, ast.UnaryOp):

                op = allowed.get(type(node.op))

                if op is None:
                    raise ValueError("Unsupported operation.")

                return op(calculate(node.operand))

            raise ValueError("Invalid expression.")

        try:

            tree = ast.parse(
                data.input,
                mode="eval"
            )

            result = calculate(tree.body)

            return {
                "plugin": "calculator",
                "result": result
            }

        except Exception as error:

            raise HTTPException(
                400,
                str(error)
            )

    # TEXT ANALYZER

    elif data.plugin == "text_analyzer":

        return {
            "plugin": "text_analyzer",
            "characters": len(data.input),
            "words": len(data.input.split()),
            "lines": len(data.input.splitlines())
        }

    # JSON FORMATTER

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

    raise HTTPException(
        404,
        "Plugin not found."
    )
