import os
import ast
import csv
import json
import base64
import operator
import zipfile
import tempfile
import shutil
import re

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
# NEXTGEN AI BRAIN 6.0
# =========================================

APP_NAME = "NEXTGEN AI BRAIN"
VERSION = "6.0.0"

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
# FASTAPI
# =========================================

app = FastAPI(
    title=APP_NAME,
    description="NEXTGEN AI CREATOR and Game Development Engine.",
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

        async with httpx.AsyncClient(timeout=180) as client:

            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=payload
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"AI provider error {response.status_code}: "
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

        message = choices[0].get("message") or {}
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
                detail="AI returned an empty answer."
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
# HOME AND STATUS
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
        "ai_configured": bool(os.getenv("GROQ_API_KEY")),
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
    prompt: str = Form("Describe and analyze this image.")
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

    encoded = base64.b64encode(content).decode("utf-8")

    image_url = f"data:{mime_type};base64,{encoded}"

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
            return content.decode("utf-8", errors="replace")

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

                output.append(f"Sheet: {sheet.title}")

                for row in sheet.iter_rows(values_only=True):

                    output.append(
                        " | ".join(
                            str(value)
                            for value in row
                            if value is not None
                        )
                    )

            return "\n".join(output)

        elif extension == "pptx":

            presentation = Presentation(BytesIO(content))
            output = []

            for number, slide in enumerate(
                presentation.slides,
                start=1
            ):

                output.append(f"Slide {number}")

                for shape in slide.shapes:

                    if hasattr(shape, "text"):
                        output.append(shape.text)

            return "\n".join(output)

        elif extension == "csv":

            text_content = content.decode(
                "utf-8",
                errors="replace"
            )

            reader = csv.reader(StringIO(text_content))

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
async def analyze_file(file: UploadFile = File(...)):

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
async def smart_analysis(request: SmartAnalysisRequest):

    content = request.content or request.message or ""

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
            {"id": "calculator", "name": "Calculator"},
            {"id": "text_analyzer", "name": "Text Analyzer"},
            {"id": "json_formatter", "name": "JSON Formatter"}
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

    tree = ast.parse(expression, mode="eval")

    def evaluate(node):

        if isinstance(node, ast.Constant):

            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError("Invalid number.")

        if isinstance(node, ast.BinOp):

            operation = ALLOWED_OPERATORS.get(type(node.op))

            if not operation:
                raise ValueError("Operator not allowed.")

            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("Exponent too large.")

            return operation(left, right)

        if isinstance(node, ast.UnaryOp):

            operation = ALLOWED_OPERATORS.get(type(node.op))

            if not operation:
                raise ValueError("Operator not allowed.")

            return operation(evaluate(node.operand))

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

            result = safe_calculate(str(data))

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

Support different game genres, not only survival games.

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
        "note": "Generated code must still be opened and tested in Godot 4."
    }


# =========================================
# RELIABLE GODOT 4 PROJECT BUILDER
# =========================================

def build_godot_project(game_name, feature):

    files = {}

    files["project.godot"] = """
config_version=5

[application]
config/name="BLOCK WORLD SURVIVAL"
run/main_scene="res://scenes/Main.tscn"

[display]
window/size/viewport_width=960
window/size/viewport_height=540
window/stretch/mode="canvas_items"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
environment/defaults/default_clear_color=Color(0.35, 0.65, 0.95, 1)
"""

    files["scenes/Main.tscn"] = """
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/main.gd" id="1"]

[node name="Main" type="Node2D"]
script = ExtResource("1")
"""

    files["scripts/world.gd"] = r'''
extends Node2D

const BLOCK_SIZE = 48
const GROUND_Y = 390

func _ready():

    var ground = StaticBody2D.new()
    ground.name = "Ground"

    var collision = CollisionShape2D.new()
    var shape = RectangleShape2D.new()

    shape.size = Vector2(2400, 48)
    collision.shape = shape
    collision.position = Vector2(0, GROUND_Y + 24)

    ground.add_child(collision)
    add_child(ground)

    queue_redraw()


func _draw():

    for x in range(-25, 26):

        var px = x * BLOCK_SIZE

        draw_rect(
            Rect2(px, GROUND_Y, BLOCK_SIZE, BLOCK_SIZE),
            Color(0.35, 0.72, 0.22)
        )

        draw_rect(
            Rect2(px, GROUND_Y + BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
            Color(0.48, 0.30, 0.16)
        )

        draw_rect(
            Rect2(px, GROUND_Y + BLOCK_SIZE * 2, BLOCK_SIZE, BLOCK_SIZE),
            Color(0.35, 0.25, 0.18)
        )

        draw_rect(
            Rect2(px, GROUND_Y + BLOCK_SIZE * 3, BLOCK_SIZE, BLOCK_SIZE),
            Color(0.32, 0.32, 0.35)
        )

    for x in range(-10, 15):

        if x % 4 == 0:

            draw_rect(
                Rect2(x * BLOCK_SIZE, GROUND_Y - 100, 48, 100),
                Color(0.38, 0.23, 0.12)
            )

            draw_circle(
                Vector2(x * BLOCK_SIZE + 24, GROUND_Y - 115),
                42,
                Color(0.12, 0.55, 0.18)
            )
'''

    files["scripts/player.gd"] = r'''
extends CharacterBody2D

const SPEED = 240.0
const JUMP_FORCE = -420.0
const GRAVITY = 1000.0

func _ready():

    var collision = CollisionShape2D.new()
    var shape = RectangleShape2D.new()

    shape.size = Vector2(30, 54)
    collision.shape = shape

    add_child(collision)


func _physics_process(delta):

    var direction = Input.get_axis(
        "move_left",
        "move_right"
    )

    velocity.x = direction * SPEED

    if not is_on_floor():

        velocity.y += GRAVITY * delta

    elif Input.is_action_just_pressed("jump"):

        velocity.y = JUMP_FORCE

    move_and_slide()
    queue_redraw()


func _draw():

    draw_rect(
        Rect2(-15, -27, 30, 54),
        Color(0.15, 0.35, 0.85)
    )

    draw_rect(
        Rect2(-12, -43, 24, 18),
        Color(0.92, 0.70, 0.50)
    )
'''

    files["scripts/touch_controls.gd"] = r'''
extends CanvasLayer

func _ready():

    setup_actions()

    var left = create_button("◀", Vector2(35, 410))
    var right = create_button("▶", Vector2(125, 410))
    var jump = create_button("▲", Vector2(790, 410))

    left.button_down.connect(
        Input.action_press.bind("move_left")
    )

    left.button_up.connect(
        Input.action_release.bind("move_left")
    )

    right.button_down.connect(
        Input.action_press.bind("move_right")
    )

    right.button_up.connect(
        Input.action_release.bind("move_right")
    )

    jump.button_down.connect(
        Input.action_press.bind("jump")
    )

    jump.button_up.connect(
        Input.action_release.bind("jump")
    )

    var hotbar = Label.new()

    hotbar.text = "1: Block     2: Wood     3: Stone"
    hotbar.position = Vector2(350, 480)

    hotbar.add_theme_font_size_override(
        "font_size",
        22
    )

    add_child(hotbar)


func setup_actions():

    var actions = [
        "move_left",
        "move_right",
        "jump"
    ]

    for action in actions:

        if not InputMap.has_action(action):
            InputMap.add_action(action)

    var left_key = InputEventKey.new()
    left_key.physical_keycode = KEY_A
    InputMap.action_add_event("move_left", left_key)

    var right_key = InputEventKey.new()
    right_key.physical_keycode = KEY_D
    InputMap.action_add_event("move_right", right_key)

    var jump_key = InputEventKey.new()
    jump_key.physical_keycode = KEY_SPACE
    InputMap.action_add_event("jump", jump_key)


func create_button(text_value, button_position):

    var button = Button.new()

    button.text = text_value
    button.position = button_position
    button.size = Vector2(75, 75)

    add_child(button)

    return button
'''

    files["scripts/inventory.gd"] = r'''
extends Node

var items = {
    "block": 20,
    "wood": 10,
    "stone": 5
}


func add_item(item_name, amount = 1):

    if items.has(item_name):
        items[item_name] += amount
    else:
        items[item_name] = amount


func remove_item(item_name, amount = 1):

    if items.has(item_name):

        if items[item_name] >= amount:

            items[item_name] -= amount
            return true

    return false


func get_inventory():

    return items
'''

    files["scripts/animal.gd"] = r'''
extends CharacterBody2D

var direction = 1.0
var speed = 35.0
var change_timer = 0.0

func _ready():

    var collision = CollisionShape2D.new()
    var shape = CircleShape2D.new()

    shape.radius = 15
    collision.shape = shape

    add_child(collision)


func _physics_process(delta):

    change_timer -= delta

    if change_timer <= 0:

        direction *= -1
        change_timer = randf_range(2.0, 5.0)

    velocity.x = direction * speed

    if not is_on_floor():
        velocity.y += 900.0 * delta

    move_and_slide()
    queue_redraw()


func _draw():

    draw_circle(
        Vector2.ZERO,
        17,
        Color(0.95, 0.90, 0.75)
    )

    draw_circle(
        Vector2(5, -5),
        3,
        Color.BLACK
    )
'''

    files["scripts/main.gd"] = r'''
extends Node2D

const WorldScript = preload("res://scripts/world.gd")
const PlayerScript = preload("res://scripts/player.gd")
const TouchScript = preload("res://scripts/touch_controls.gd")
const InventoryScript = preload("res://scripts/inventory.gd")
const AnimalScript = preload("res://scripts/animal.gd")


func _ready():

    var world = WorldScript.new()
    add_child(world)

    var player = PlayerScript.new()
    player.position = Vector2(250, 300)
    add_child(player)

    var inventory = InventoryScript.new()
    add_child(inventory)

    var animal = AnimalScript.new()
    animal.position = Vector2(500, 350)
    add_child(animal)

    var animal_two = AnimalScript.new()
    animal_two.position = Vector2(700, 350)
    add_child(animal_two)

    var controls = TouchScript.new()
    add_child(controls)

    var title = Label.new()

    title.text = "BLOCK WORLD SURVIVAL"
    title.position = Vector2(20, 15)

    title.add_theme_font_size_override(
        "font_size",
        26
    )

    add_child(title)
'''

    files["README.md"] = f"""
# {game_name}

NEXTGEN AI CREATOR - Godot 4 Starter Project

## Included

- 2D block-style terrain
- Grass, dirt and stone
- Player movement
- Jumping
- Basic ground collision
- Android touch buttons
- Keyboard controls
- Basic animal movement
- Inventory data system
- Hotbar display

## Game request

{feature}

## Installation

1. Install Godot 4.
2. Extract this ZIP.
3. Open the extracted project folder.
4. Select project.godot.
5. Press Play.

## Controls

- A or Left button: Move left
- D or Right button: Move right
- Space or Jump button: Jump

## Important

This is a starter project.

It has not been tested in the Godot editor.

The inventory and hotbar are starter systems.
Breaking and placing blocks, crafting, advanced animal
behavior and other survival features still require development.
"""

    return files


# =========================================
# GODOT 4 ZIP GENERATOR
# =========================================

@app.post("/api/game/create-zip")
async def create_game_zip(request: GameCreateRequest):

    game_name = request.game_name or "NEXTGEN_GAME"

    safe_name = re.sub(
        r"[^A-Za-z0-9_-]",
        "_",
        game_name
    ).strip("_")[:60]

    if not safe_name:
        safe_name = "NEXTGEN_GAME"

    feature = (
        request.feature_request
        or request.feature
        or request.request
        or "Create a block survival game."
    )

    temp_dir = tempfile.mkdtemp(
        prefix="nextgen_godot_"
    )

    try:

        project_dir = Path(temp_dir) / safe_name

        project_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        files = build_godot_project(
            game_name,
            feature
        )

        for filename, content in files.items():

            target = project_dir / filename

            target.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            target.write_text(
                content,
                encoding="utf-8"
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

        for filename in required_files:

            if not (project_dir / filename).is_file():

                raise ValueError(
                    f"Missing required file: {filename}"
                )

        project_config = (
            project_dir / "project.godot"
        ).read_text(encoding="utf-8")

        if "config_version=5" not in project_config:

            raise ValueError(
                "Invalid Godot 4 project configuration."
            )

        if "run/main_scene" not in project_config:

            raise ValueError(
                "Main scene is not configured."
            )

        total_size = sum(
            file_path.stat().st_size
            for file_path in project_dir.rglob("*")
            if file_path.is_file()
        )

        if total_size > 3 * 1024 * 1024:

            raise ValueError(
                "Project exceeds the 3 MB limit."
            )

        zip_path = Path(temp_dir) / f"{safe_name}.zip"

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

        with zipfile.ZipFile(zip_path, "r") as archive:

            bad_file = archive.testzip()

            if bad_file:

                raise ValueError(
                    f"ZIP verification failed: {bad_file}"
                )

        if not zip_path.exists() or zip_path.stat().st_size == 0:

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
            detail=f"ZIP generation failed: {str(error)}"
        )


# =========================================
# END NEXTGEN AI BRAIN 6.0
# =========================================
