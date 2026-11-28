# =========================================
# NEXTGEN GODOT 4 RELIABLE ZIP GENERATOR
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

func _draw():
    var block_size = 48
    var ground_y = 390

    for x in range(-20, 30):
        var px = x * block_size

        draw_rect(
            Rect2(px, ground_y, block_size, block_size),
            Color(0.35, 0.72, 0.22)
        )

        draw_rect(
            Rect2(px, ground_y + block_size, block_size, block_size),
            Color(0.48, 0.30, 0.16)
        )

        draw_rect(
            Rect2(px, ground_y + block_size * 2, block_size, block_size),
            Color(0.35, 0.25, 0.18)
        )

        draw_rect(
            Rect2(px, ground_y + block_size * 3, block_size, block_size),
            Color(0.32, 0.32, 0.35)
        )

    for x in range(-10, 15):
        if x % 4 == 0:
            draw_rect(
                Rect2(x * block_size, ground_y - 100, 48, 100),
                Color(0.38, 0.23, 0.12)
            )

            draw_circle(
                Vector2(x * block_size + 24, ground_y - 115),
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
    else:
        if Input.is_action_just_pressed("jump"):
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

    for action in [
        "move_left",
        "move_right",
        "jump"
    ]:
        if not InputMap.has_action(action):
            InputMap.add_action(action)

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
    hotbar.text = "  1: Block     2: Wood     3: Stone"
    hotbar.position = Vector2(350, 480)
    hotbar.add_theme_font_size_override("font_size", 22)
    add_child(hotbar)

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
    title.add_theme_font_size_override("font_size", 26)
    add_child(title)
'''

    files["README.md"] = f"""
# {game_name}

NEXTGEN AI CREATOR - Godot 4 Starter Project

## Included

- 2D block-style terrain
- Player movement
- Jumping
- Android touch buttons
- Basic animal movement
- Inventory data system
- Hotbar display
- Grass, dirt and stone terrain

## Game request

{feature}

## Installation

1. Install Godot 4.
2. Extract this ZIP.
3. Open the extracted project folder.
4. Select project.godot.
5. Press Play.

## Important

This is a starter project.
It has not been tested in the Godot editor.
Additional development is required.
"""

    return files


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
        prefix="nextgen_game_"
    )

    try:

        project_dir = Path(temp_dir) / safe_name
        project_dir.mkdir(parents=True, exist_ok=True)

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
                    f"Missing file: {filename}"
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

        with zipfile.ZipFile(zip_path, "r") as archive:

            bad_file = archive.testzip()

            if bad_file:
                raise ValueError(
                    f"ZIP verification failed: {bad_file}"
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
            detail=f"Game ZIP generation failed: {str(error)}"
        )


# =========================================
# END GODOT ZIP GENERATOR
# =========================================
