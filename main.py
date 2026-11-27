import os
import ast
import csv
import json
import base64
import operator

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
from pydantic import BaseModel, Field

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation


# =========================================
# NEXTGEN AI BRAIN CONFIGURATION
# =========================================

APP_NAME = "NEXTGEN AI BRAIN"
VERSION = "3.0.0"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL = os.getenv(
    "AI_MODEL",
    "openai/gpt-oss-20b"
)

VISION_MODEL = os.getenv(
    "VISION_MODEL",
    "qwen/qwen3.8-27b"
)


# =========================================
# FASTAPI APPLICATION
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
# AI PROVIDER FUNCTION
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

    # GPT-OSS reasoning configuration
    if selected_model.startswith("openai/gpt-oss"):
        payload["include_reasoning"] = False
        payload["reasoning_effort"] = "low"

    try:
        async with httpx.AsyncClient(timeout=150) as client:
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
            finish_reason = choice.get("finish_reason")

            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an empty final answer. "
                    f"Finish reason: {finish_reason}"
                )
            )

        return answer.strip()

    except HTTPException:
        raise

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="AI provider timed out. Please try again."
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
# HOME AND HEALTH
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
                    "You are NEXTGEN AI, a helpful AI assistant. "
                    "Answer clearly and accurately. "
                    "You can communicate in English, Cebuano "
                    "and Filipino. Be honest about limitations."
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
            detail="The uploaded image is empty."
        )

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image is too large. Maximum size is 10 MB."
        )

    mime_type = uploaded.content_type or "image/jpeg"

    if not mime_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image."
        )

    encoded = base64.b64encode(content).decode("utf-8")

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

def extract_file_text(
    filename: str,
    content: bytes
):

    extension = filename.lower().split(".")[-1]

    try:

        if extension == "txt":
            return content.decode(
                "utf-8",
                errors="replace"
            )

        elif extension == "pdf":

            reader = PdfReader(BytesIO(content))

            return "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        elif extension == "docx":

            document = Document(BytesIO(content))

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
            detail="File is too large. Maximum size is 10 MB."
        )

    extracted_text = extract_file_text(
        file.filename or "uploaded.txt",
        content
    )

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail="No readable text found in the file."
        )

    extracted_text = extracted_text[:20000]

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI file analysis assistant. "
                    "Analyze documents carefully. "
                    "Summarize important information and "
                    "identify useful findings."
                )
            },
            {
                "role": "user",
                "content": (
                    "Analyze this uploaded file:\n\n"
                    + extracted_text
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

    task = request.task or "Analyze and improve"

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI SMART ANALYSIS. "
                    "Analyze the user's idea, code, product "
                    "or project. Identify problems, strengths, "
                    "weaknesses, improvements and practical "
                    "next steps. Never claim that you physically "
                    "tested something unless an actual test "
                    "was performed."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Task: {task}\n\n"
                    f"Content:\n{content}"
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
                "name": "Calculator",
                "description": "Perform basic arithmetic."
            },
            {
                "id": "text_analyzer",
                "name": "Text Analyzer",
                "description": "Analyze text statistics."
            },
            {
                "id": "json_formatter",
                "name": "JSON Formatter",
                "description": "Format and validate JSON."
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
# PLUGIN EXECUTION
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
                detail=f"Calculator error: {str(error)}"
            )

    elif plugin == "text_analyzer":

        text_value = str(data or "")

        words = text_value.split()

        return {
            "success": True,
            "plugin": plugin,
            "characters": len(text_value),
            "words": len(words),
            "lines": len(text_value.splitlines()),
            "sentences": text_value.count(".")
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

    else:

        raise HTTPException(
            status_code=404,
            detail="Plugin not found."
        )


# =========================================
# GODOT 4 GAME DEVELOPMENT TASKS
# =========================================

GAME_TASKS = [
    {
        "id": "create_project",
        "name": "Create Complete Game Project",
        "description": "Plan and generate a Godot 4 project."
    },
    {
        "id": "generate",
        "name": "Generate Game Code",
        "description": "Create GDScript code and scenes."
    },
    {
        "id": "player",
        "name": "Player System",
        "description": "Player movement and customization."
    },
    {
        "id": "animal",
        "name": "Animal AI",
        "description": "Animal movement, eating and behavior."
    },
    {
        "id": "monster",
        "name": "Monster AI",
        "description": "Monster behavior and combat."
    },
    {
        "id": "world",
        "name": "World Generation",
        "description": "Biomes, terrain and environment."
    },
    {
        "id": "npc",
        "name": "NPC System",
        "description": "Villagers and intelligent NPCs."
    },
    {
        "id": "combat",
        "name": "Combat System",
        "description": "Weapons, attacks and health."
    },
    {
        "id": "inventory",
        "name": "Inventory System",
        "description": "Items, hotbar and crafting."
    },
    {
        "id": "review",
        "name": "Review Game Code",
        "description": "Inspect code and identify problems."
    },
    {
        "id": "fix",
        "name": "Fix Game Bugs",
        "description": "Find and correct code errors."
    },
    {
        "id": "optimize",
        "name": "Android Optimization",
        "description": "Improve mobile performance."
    }
]


@app.get("/api/game/tasks")
async def get_game_tasks():

    return {
        "success": True,
        "engine": "Godot 4",
        "tasks": GAME_TASKS
    }


# =========================================
# AI GAME DEVELOPER
# =========================================

@app.post("/api/game/create")
async def create_game(
    request: GameCreateRequest
):

    game_name = request.game_name
    engine = request.engine
    task = request.task

    feature = (
        request.feature_request
        or request.feature
        or request.request
        or ""
    )

    existing_code = (
        request.existing_code
        or request.code
        or ""
    )

    if not feature.strip() and not existing_code.strip():
        if task not in ("create_project",):
            raise HTTPException(
                status_code=400,
                detail="Please describe the game development task."
            )

    task_names = {
        item["id"]: item["name"]
        for item in GAME_TASKS
    }

    task_name = task_names.get(
        task,
        task
    )

    system_prompt = """
You are NEXTGEN AI GAME DEVELOPER.

Your job is to help create real game projects using Godot 4.

IMPORTANT RULES:

1. Use Godot 4 and valid GDScript 2.0 syntax.
2. Do not use Godot 3 syntax.
3. Generate practical, organized and understandable code.
4. Include filenames and folder structures.
5. Include scene setup instructions.
6. Include node paths and required node types.
7. Explain how scripts connect to each other.
8. For Android, consider touch controls and performance.
9. Do not claim code has been tested unless it was actually tested.
10. Do not claim an APK has been built unless it was actually built.
11. If information is missing, state reasonable assumptions.
12. Avoid fake assets, fake download links and imaginary files.
13. Make code as complete as reasonably possible.

For BLOCK WORLD SURVIVAL, preserve the requested
voxel/block-style graphics and survival gameplay.

The game should eventually support:
- Player movement and customization
- Animals with intelligent behaviors
- Monsters and combat
- World generation and biomes
- Inventory and crafting
- Building and survival systems
- Android touch controls
- Offline gameplay
- Future multiplayer support

When generating a project, provide:
- Project folder structure
- project.godot configuration
- Main scene
- GDScript files
- Scene creation instructions
- Testing instructions

When reviewing or fixing code:
- Identify errors
- Explain why they happen
- Return corrected complete code where possible
- Explain how to test the correction

Be honest about limitations.
"""

    user_prompt = f"""
GAME NAME: {game_name}

GAME ENGINE: {engine}

TARGET PLATFORM: {request.platform}

DEVELOPMENT TASK: {task_name}

FEATURE OR REQUEST:
{feature if feature else "Create the initial project structure."}

EXISTING CODE:
{existing_code if existing_code else "No existing code provided."}

Please complete this development task.

For generated code, clearly label each filename.
Do not return an empty answer.
"""

    answer = await ask_ai(
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        model=request.model,
        temperature=0.3,
        max_tokens=6000
    )

    return {
        "success": True,
        "game_name": game_name,
        "engine": engine,
        "task": task,
        "project_output": answer,
        "model": request.model or MODEL,
        "tested": False,
        "note": (
            "Generated code must still be installed, "
            "executed and tested in the game engine. "
            "This API does not automatically build an APK."
        )
    }


# =========================================
# SERVER STARTUP INFORMATION
# =========================================

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
            "Godot 4 Game Developer"
        ]
    }
