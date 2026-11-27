import os
import ast
import csv
import json
import base64
import operator
import zipfile
import tempfile
import shutil

from pathlib import Path
from io import BytesIO, StringIO
from typing import Optional, Any

import httpx

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from pydantic import BaseModel, Field

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation


# =========================================
# NEXTGEN AI BRAIN 4.0
# =========================================

APP_NAME = "NEXTGEN AI BRAIN"

VERSION = "4.0.0"

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

MODEL = os.getenv(
    "AI_MODEL",
    "openai/gpt-oss-20b"
)

VISION_MODEL = os.getenv(
    "VISION_MODEL",
    "qwen/qwen3.8-27b"
)


# =========================================
# FASTAPI
# =========================================

app = FastAPI(
    title=APP_NAME,
    description=(
        "NEXTGEN AI CREATOR, AI Engineering "
        "and Godot Game Development Engine."
    ),
    version=VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================================
# REQUEST MODELS
# =========================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    model: Optional[str] = None


class SmartAnalysisRequest(BaseModel):
    content: str = ""
    message: Optional[str] = None
    task: Optional[str] = None


class PluginRequest(BaseModel):
    plugin: str
    input: Any = None
    data: Any = None


class GameCreateRequest(BaseModel):
    game_name: str = "My Godot Game"

    engine: str = "Godot 4"

    task: str = "create_project"

    feature_request: str = ""

    feature: Optional[str] = None

    request: Optional[str] = None

    existing_code: Optional[str] = None

    code: Optional[str] = None

    platform: str = "Android"

    model: Optional[str] = None


# =========================================
# AI PROVIDER
# =========================================

async def ask_ai(
    messages,
    model=None,
    temperature=0.5,
    max_tokens=3000
):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="AI key is not configured."
        )

    selected_model = model or MODEL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "stream": False
    }

    if selected_model.startswith("openai/gpt-oss"):

        payload["include_reasoning"] = False

        payload["reasoning_effort"] = "low"

    try:

        async with httpx.AsyncClient(
            timeout=180
        ) as client:

            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=payload
            )

        if response.status_code != 200:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"AI provider error "
                    f"{response.status_code}: "
                    f"{response.text[:500]}"
                )
            )

        result = response.json()

        choices = result.get("choices", [])

        if not choices:

            raise HTTPException(
                status_code=502,
                detail="AI provider returned no choices."
            )

        choice = choices[0]

        message = choice.get("message") or {}

        answer = message.get("content")

        if isinstance(answer, list):

            answer = "\n".join(
                item.get("text", "")
                for item in answer
                if isinstance(item, dict)
            )

        if not isinstance(answer, str) or not answer.strip():

            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an empty final answer. "
                    f"Finish reason: {choice.get('finish_reason')}"
                )
            )

        return answer.strip()

    except HTTPException:
        raise

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail="AI provider timed out."
        )

    except httpx.RequestError:

        raise HTTPException(
            status_code=503,
            detail="Could not connect to AI provider."
        )

    except (ValueError, KeyError, TypeError):

        raise HTTPException(
            status_code=502,
            detail="AI provider returned an invalid response."
        )


# =========================================
# HOME
# =========================================

@app.get("/")
async def home():

    return {
        "name": APP_NAME,
        "version": VERSION,
        "status": "online",
        "message": "Welcome to NEXTGEN AI CREATOR!"
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "ai_configured": bool(
            os.getenv("GROQ_API_KEY")
        ),
        "model": MODEL
    }


@app.get("/api/status")
async def api_status():

    return {
        "success": True,
        "name": APP_NAME,
        "version": VERSION,
        "status": "online",
        "features": [
            "AI Chat",
            "Image Analysis",
            "File Analysis",
            "Smart Analysis",
            "Plugins",
            "Godot Game Developer",
            "Godot ZIP Generator"
        ]
    }


# =========================================
# AI CHAT
# =========================================

@app.post("/api/chat")
async def chat(request: ChatRequest):

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI, a helpful assistant. "
                    "Communicate in English, Cebuano or Filipino. "
                    "Give accurate and understandable answers."
                )
            },
            {
                "role": "user",
                "content": request.message
            }
        ],
        model=request.model
    )

    return {
        "success": True,
        "response": answer,
        "model": request.model or MODEL
    }


# =========================================
# IMAGE ANALYSIS
# =========================================

@app.post("/api/analyze-image")
async def analyze_image(
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    prompt: str = Form(
        "Describe and analyze this image."
    )
):

    uploaded = file or image

    if not uploaded:

        raise HTTPException(
            status_code=400,
            detail="Please upload an image."
        )

    content = await uploaded.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Image is empty."
        )

    if len(content) > 10 * 1024 * 1024:

        raise HTTPException(
            status_code=413,
            detail="Maximum image size is 10 MB."
        )

    mime_type = uploaded.content_type or "image/jpeg"

    if not mime_type.startswith("image/"):

        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image."
        )

    encoded = base64.b64encode(
        content
    ).decode("utf-8")

    image_url = (
        f"data:{mime_type};base64,{encoded}"
    )

    answer = await ask_ai(
        messages=[
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
        temperature=0.3,
        max_tokens=2000
    )

    return {
        "success": True,
        "analysis": answer,
        "filename": uploaded.filename,
        "model": VISION_MODEL
    }


# =========================================
# FILE TEXT EXTRACTION
# =========================================

def extract_file_text(filename, content):

    extension = filename.lower().split(".")[-1]

    try:

        if extension == "txt":

            return content.decode(
                "utf-8",
                errors="replace"
            )

        elif extension == "pdf":

            reader = PdfReader(
                BytesIO(content)
            )

            return "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        elif extension == "docx":

            document = Document(
                BytesIO(content)
            )

            return "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

        elif extension == "xlsx":

            workbook = load_workbook(
                BytesIO(content),
                data_only=True
            )

            output = []

            for sheet in workbook.worksheets:

                output.append(
                    f"Sheet: {sheet.title}"
                )

                for row in sheet.iter_rows(
                    values_only=True
                ):

                    output.append(
                        " | ".join(
                            str(value)
                            for value in row
                            if value is not None
                        )
                    )

            return "\n".join(output)

        elif extension == "pptx":

            presentation = Presentation(
                BytesIO(content)
            )

            output = []

            for slide_number, slide in enumerate(
                presentation.slides,
                start=1
            ):

                output.append(
                    f"Slide {slide_number}"
                )

                for shape in slide.shapes:

                    if hasattr(shape, "text"):
                        output.append(shape.text)

            return "\n".join(output)

        elif extension == "csv":

            text_content = content.decode(
                "utf-8",
                errors="replace"
            )

            reader = csv.reader(
                StringIO(text_content)
            )

            return "\n".join(
                " | ".join(row)
                for row in reader
            )

        else:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type."
            )

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Could not read file: {str(error)}"
        )


# =========================================
# FILE ANALYSIS
# =========================================

@app.post("/api/analyze-file")
async def analyze_file(
    file: UploadFile = File(...)
):

    content = await file.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    if len(content) > 10 * 1024 * 1024:

        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 10 MB."
        )

    extracted_text = extract_file_text(
        file.filename or "uploaded.txt",
        content
    )

    if not extracted_text.strip():

        raise HTTPException(
            status_code=400,
            detail="No readable text found."
        )

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI file analysis assistant. "
                    "Analyze documents carefully and summarize "
                    "important information."
                )
            },
            {
                "role": "user",
                "content": (
                    "Analyze this file:\n\n"
                    + extracted_text[:20000]
                )
            }
        ],
        max_tokens=3000
    )

    return {
        "success": True,
        "filename": file.filename,
        "analysis": answer
    }


# =========================================
# SMART ANALYSIS
# =========================================

@app.post("/api/smart-analysis")
async def smart_analysis(
    request: SmartAnalysisRequest
):

    content = (
        request.content
        or request.message
        or ""
    )

    if not content.strip():

        raise HTTPException(
            status_code=400,
            detail="Please enter something to analyze."
        )

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI SMART ANALYSIS. "
                    "Analyze ideas, code and projects. "
                    "Identify strengths, weaknesses, errors "
                    "and improvements. Never claim physical "
                    "testing unless it actually happened."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Task: {request.task or 'Analyze and improve'}"
                    f"\n\nContent:\n{content}"
                )
            }
        ],
        max_tokens=3000
    )

    return {
        "success": True,
        "analysis": answer
    }


# =========================================
# PLUGINS
# =========================================

@app.get("/api/plugins")
async def get_plugins():

    return {
        "success": True,
        "plugins": [
            {
                "id": "calculator",
                "name": "Calculator"
            },
            {
                "id": "text_analyzer",
                "name": "Text Analyzer"
            },
            {
                "id": "json_formatter",
                "name": "JSON Formatter"
            }
        ]
    }


# =========================================
# SAFE CALCULATOR
# =========================================

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos
}


def safe_calculate(expression):

    tree = ast.parse(
        expression,
        mode="eval"
    )

    def evaluate(node):

        if isinstance(node, ast.Constant):

            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError("Invalid number.")

        if isinstance(node, ast.BinOp):

            operation = ALLOWED_OPERATORS.get(
                type(node.op)
            )

            if not operation:
                raise ValueError("Operator not allowed.")

            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow):

                if abs(right) > 100:
                    raise ValueError("Exponent too large.")

            return operation(left, right)

        if isinstance(node, ast.UnaryOp):

            operation = ALLOWED_OPERATORS.get(
                type(node.op)
            )

            if not operation:
                raise ValueError("Operator not allowed.")

            return operation(
                evaluate(node.operand)
            )

        raise ValueError("Invalid expression.")

    return evaluate(tree.body)


# =========================================
# RUN PLUGINS
# =========================================

@app.post("/api/plugins/run")
async def run_plugin(request: PluginRequest):

    plugin = request.plugin.lower()

    data = (
        request.input
        if request.input is not None
        else request.data
    )

    if plugin == "calculator":

        try:

            result = safe_calculate(
                str(data)
            )

            return {
                "success": True,
                "plugin": plugin,
                "result": result
            }

        except Exception as error:

            raise HTTPException(
                status_code=400,
                detail=str(error)
            )

    elif plugin == "text_analyzer":

        text_value = str(data or "")

        return {
            "success": True,
            "plugin": plugin,
            "characters": len(text_value),
            "words": len(text_value.split()),
            "lines": len(text_value.splitlines())
        }

    elif plugin == "json_formatter":

        try:

            parsed = (
                data
                if isinstance(data, (dict, list))
                else json.loads(str(data))
            )

            return {
                "success": True,
                "plugin": plugin,
                "result": json.dumps(
                    parsed,
                    indent=4,
                    ensure_ascii=False
                )
            }

        except Exception as error:

            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON: {str(error)}"
            )

    raise HTTPException(
        status_code=404,
        detail="Plugin not found."
    )


# =========================================
# GODOT GAME TASKS
# =========================================

GAME_TASKS = [
    {"id": "create_project", "name": "Create Complete Game Project"},
    {"id": "generate", "name": "Generate Game Code"},
    {"id": "player", "name": "Player System"},
    {"id": "animal", "name": "Animal AI"},
    {"id": "monster", "name": "Monster AI"},
    {"id": "world", "name": "World Generation"},
    {"id": "npc", "name": "NPC System"},
    {"id": "combat", "name": "Combat System"},
    {"id": "inventory", "name": "Inventory System"},
    {"id": "review", "name": "Review Game Code"},
    {"id": "fix", "name": "Fix Game Bugs"},
    {"id": "optimize", "name": "Android Optimization"}
]


@app.get("/api/game/tasks")
async def get_game_tasks():

    return {
        "success": True,
        "engine": "Godot 4",
        "tasks": GAME_TASKS
    }


# =========================================
# GAME DEVELOPER
# =========================================

GAME_SYSTEM_PROMPT = """
You are NEXTGEN AI GAME DEVELOPER.

You develop games using Godot 4 and GDScript 2.0.

Rules:

1. Use Godot 4 syntax only.
2. Never use Godot 3 APIs.
3. Generate practical code.
4. Explain filenames and folder structure.
5. Include scene setup instructions.
6. Use Android-friendly touch controls.
7. Do not claim code is tested unless it is.
8. Do not claim an APK was built unless it was.
9. Do not reference nonexistent assets.
10. Make code organized and understandable.

For BLOCK WORLD SURVIVAL preserve:
- Voxel/block-style graphics
- Player customization
- Survival mechanics
- Animal AI
- Monster AI
- World generation
- Inventory and crafting
- Android touch controls
- Offline gameplay
- Future multiplayer support
"""


@app.post("/api/game/create")
async def create_game(request: GameCreateRequest):

    feature = (
        request.feature_request
        or request.feature
        or request.request
        or "Create a starter game project."
    )

    existing_code = (
        request.existing_code
        or request.code
        or ""
    )

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": GAME_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"""
Game: {request.game_name}

Engine: {request.engine}

Platform: {request.platform}

Task: {request.task}

Feature:
{feature}

Existing code:
{existing_code}

Generate the requested development output.
Label every filename clearly.
"""
            }
        ],
        model=request.model,
        temperature=0.3,
        max_tokens=6000
    )

    return {
        "success": True,
        "game_name": request.game_name,
        "engine": request.engine,
        "task": request.task,
        "project_output": answer,
        "model": request.model or MODEL,
        "tested": False,
        "note": (
            "Generated code must still be opened "
            "and tested in Godot 4."
        )
    }


# =========================================
# PARSE AI PROJECT JSON
# =========================================

def parse_project_json(answer):

    cleaned = answer.strip()

    if cleaned.startswith("```"):

        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines)

    try:

        return json.loads(cleaned)

    except json.JSONDecodeError:

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found.")

        return json.loads(
            cleaned[start:end + 1]
        )


# =========================================
# GODOT 4 ZIP GENERATOR
# =========================================

ZIP_SYSTEM_PROMPT = """
You are NEXTGEN AI GODOT 4 PROJECT GENERATOR.

Return ONLY a valid JSON object.

Required format:

{
  "files": {
    "project.godot": "file contents",
    "scenes/Main.tscn": "file contents",
    "scripts/main.gd": "file contents",
    "scripts/player.gd": "file contents",
    "scripts/world.gd": "file contents",
    "scripts/touch_controls.gd": "file contents",
    "scripts/inventory.gd": "file contents",
    "scripts/animal.gd": "file contents",
    "README.md": "file contents"
  }
}

PROJECT REQUIREMENTS:

- Godot 4 only.
- Valid GDScript 2.0.
- Create a playable 2D starter game.
- Use built-in shapes and drawing.
- Do not require external assets.
- Create a working main scene.
- Include player movement.
- Include a simple generated grass world.
- Include Android touch buttons.
- Include inventory and hotbar.
- Include basic animal wandering and eating behavior.
- Make all scripts compatible with each other.
- Include project setup instructions.
- Include testing instructions.
- Do not claim the project has been tested.
- Avoid missing node references.
- Do not use Godot 3 syntax.

Return all required files in the JSON files object.
"""


@app.post("/api/game/create-zip")
async def create_game_zip(request: GameCreateRequest):

    game_name = request.game_name or "NEXTGEN_GAME"

    safe_name = "".join(
        character
        for character in game_name
        if character.isalnum()
        or character in ("-", "_")
    ).strip()

    if not safe_name:
        safe_name = "NEXTGEN_GAME"

    feature = (
        request.feature_request
        or request.feature
        or request.request
        or "Create a complete starter survival game."
    )

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": ZIP_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"""
GAME NAME: {game_name}

ENGINE: Godot 4

PLATFORM: {request.platform}

FEATURE REQUEST:
{feature}

Generate all required project files.

Return valid JSON only.
"""
            }
        ],
        model=request.model,
        temperature=0.2,
        max_tokens=12000
    )

    try:

        project_data = parse_project_json(answer)

        files = project_data.get("files")

        if not isinstance(files, dict):
            raise ValueError("Missing files object.")

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "AI did not return a valid project file list. "
                f"Please try again. Details: {str(error)}"
            )
        )

    required_files = [
        "project.godot",
        "scenes/Main.tscn",
        "scripts/main.gd",
        "scripts/player.gd",
        "scripts/world.gd",
        "scripts/touch_controls.gd",
        "scripts/inventory.gd",
        "scripts/animal.gd",
        "README.md"
    ]

    missing_files = [
        filename
        for filename in required_files
        if filename not in files
    ]

    if missing_files:

        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI project is incomplete.",
                "missing_files": missing_files
            }
        )

    if len(files) > 60:

        raise HTTPException(
            status_code=502,
            detail="AI generated too many files."
        )

    temp_dir = tempfile.mkdtemp(
        prefix="nextgen_game_"
    )

    project_dir = (
        Path(temp_dir) / safe_name
    )

    project_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        total_size = 0

        for filename, content in files.items():

            if not isinstance(filename, str):
                continue

            if not isinstance(content, str):
                continue

            relative_path = Path(filename)

            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
            ):
                continue

            total_size += len(
                content.encode("utf-8")
            )

            if total_size > 2 * 1024 * 1024:

                raise ValueError(
                    "Generated project exceeds 2 MB."
                )

            target = project_dir / relative_path

            target.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            target.write_text(
                content,
                encoding="utf-8"
            )

        zip_path = (
            Path(temp_dir) / f"{safe_name}.zip"
        )

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as archive:

            for file_path in project_dir.rglob("*"):

                if file_path.is_file():

                    archive.write(
                        file_path,
                        file_path.relative_to(temp_dir)
                    )

        if (
            not zip_path.exists()
            or zip_path.stat().st_size == 0
        ):

            raise ValueError(
                "ZIP file creation failed."
            )

        return FileResponse(
            path=str(zip_path),
            filename=f"{safe_name}.zip",
            media_type="application/zip",
            background=BackgroundTask(
                shutil.rmtree,
                temp_dir,
                ignore_errors=True
            )
        )

    except Exception as error:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not create project ZIP: {str(error)}"
            )
        )


# =========================================
# END
# =========================================
