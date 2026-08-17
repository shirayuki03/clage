import copy
import math
import time


Clage_sprites = {}
Clage_clone_scripts = {}
Clage_clone_sources = {}


def Clage_reset_state():
    Clage_sprites.clear()
    Clage_clone_scripts.clear()
    Clage_clone_sources.clear()


def Clage_export_state():
    return {
        "sprites": copy.deepcopy(Clage_sprites),
        "clone_sources": copy.deepcopy(Clage_clone_sources),
    }


def Clage_import_state(state):
    Clage_sprites.clear()
    Clage_sprites.update(copy.deepcopy((state or {}).get("sprites", {})))
    Clage_clone_sources.clear()
    Clage_clone_sources.update(copy.deepcopy((state or {}).get("clone_sources", {})))


def Clage_emit_state():
    emit_extension_event("Clage", "state", {"sprites": copy.deepcopy(Clage_sprites)})


def Clage_sprite_template(source=None):
    if source and source in Clage_sprites:
        sprite = copy.deepcopy(Clage_sprites[source])
    else:
        sprite = {
            "x": 0,
            "y": 0,
            "direction": 90,
            "costume": "",
            "visible": True,
            "width": 44,
            "height": 44,
        }
    return sprite


class Clage_main:
    def Clage_setup(self):
        self.current_sprite_definition = None
        self.current_clone_name = None

    def stage(self, tree):
        for cmd in tree.children:
            self.visit_command(cmd)
        Clage_emit_state()

    def sprite(self, tree):
        sprite_name = str(tree.children[0])
        Clage_sprites[sprite_name] = Clage_sprite_template()
        previous_sprite = self.current_sprite_definition
        self.current_sprite_definition = sprite_name
        try:
            for cmd in tree.children[1:]:
                self.visit_command(cmd)
        finally:
            self.current_sprite_definition = previous_sprite
        Clage_emit_state()

    def resolve_sprite(self, node):
        if hasattr(node, "data"):
            return self.visit(node)
        return str(node)

    def activate_task_context(self, context):
        previous_clone = self.current_clone_name
        self.current_clone_name = None if context is None else context.get("clone_name")
        return previous_clone

    def restore_task_context(self, previous_context):
        self.current_clone_name = previous_context

    def move(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        distance = self._resolve(self.visit(tree.children[1]))
        sprite = Clage_sprites[sprite_name]
        radians = math.radians(sprite["direction"])
        sprite["x"] += distance * math.cos(radians)
        sprite["y"] += distance * math.sin(radians)
        Clage_emit_state()

    def x_assignment(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        Clage_sprites[sprite_name]["x"] = self._resolve(self.visit(tree.children[1]))
        Clage_emit_state()

    def y_assignment(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        Clage_sprites[sprite_name]["y"] = self._resolve(self.visit(tree.children[1]))
        Clage_emit_state()

    def direction_assignment(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        direction = self._resolve(self.visit(tree.children[1]))
        Clage_sprites[sprite_name]["direction"] = ((direction + 180) % 360) - 180
        Clage_emit_state()

    def x_position(self, tree):
        return Clage_sprites[self.resolve_sprite(tree.children[0])]["x"]

    def y_position(self, tree):
        return Clage_sprites[self.resolve_sprite(tree.children[0])]["y"]

    def direction(self, tree):
        return Clage_sprites[self.resolve_sprite(tree.children[0])]["direction"]

    def costume(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        Clage_sprites[sprite_name]["costume"] = self._resolve(self.visit(tree.children[1]))
        Clage_emit_state()

    def show(self, tree):
        Clage_sprites[self.resolve_sprite(tree.children[0])]["visible"] = True
        Clage_emit_state()

    def hide(self, tree):
        Clage_sprites[self.resolve_sprite(tree.children[0])]["visible"] = False
        Clage_emit_state()

    def clone_start(self, tree):
        if self.current_sprite_definition is None:
            raise ClambonError("clone ブロックは Sprite の中に書いてね。")
        Clage_clone_scripts[self.current_sprite_definition] = list(tree.children)

    def clone_call(self, tree):
        if self.current_clone_name is None:
            raise ClambonError("clone は clone ブロックの中だけで使えます。")
        return self.current_clone_name

    def clone_create(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        clone_name = sprite_name
        index = 0
        while clone_name in Clage_sprites:
            clone_name = f"{sprite_name}_clone{index}"
            index += 1

        Clage_sprites[clone_name] = Clage_sprite_template(sprite_name)
        source_name = Clage_clone_sources.get(sprite_name, sprite_name)
        Clage_clone_sources[clone_name] = source_name
        commands = Clage_clone_scripts.get(source_name)
        if commands is not None:
            self.register_runtime_script(commands, context={"clone_name": clone_name})
        Clage_emit_state()
        return clone_name

    def clone_delete(self, tree):
        clone_name = self.current_clone_name
        if clone_name is None:
            raise ClambonError("clone.delete() は clone ブロックの中だけで使えます。")
        self.delete_clone(clone_name)
        Clage_emit_state()
        self.cancel_current_task()

    def delete_clone(self, clone_name):
        Clage_sprites.pop(clone_name, None)
        Clage_clone_sources.pop(clone_name, None)

    def touching(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        target_name = self.resolve_sprite(tree.children[1])
        if target_name == "edge":
            return self.touching_edge(sprite_name)
        return self.touching_sprite(sprite_name, target_name)

    def touching_edge(self, sprite_name):
        sprite = Clage_sprites.get(sprite_name)
        if not sprite or not sprite.get("visible", True):
            return False
        half_w = sprite.get("width", 44) / 2
        half_h = sprite.get("height", 44) / 2
        return (
            sprite["x"] - half_w <= -360
            or sprite["x"] + half_w >= 360
            or sprite["y"] - half_h <= -270
            or sprite["y"] + half_h >= 270
        )

    def touching_sprite(self, sprite_name, target_name):
        sprite = Clage_sprites.get(sprite_name)
        target = Clage_sprites.get(target_name)
        if not sprite or not target:
            return False
        if not sprite.get("visible", True) or not target.get("visible", True):
            return False
        return (
            abs(sprite["x"] - target["x"]) <= (sprite.get("width", 44) + target.get("width", 44)) / 2
            and abs(sprite["y"] - target["y"]) <= (sprite.get("height", 44) + target.get("height", 44)) / 2
        )

    def key_pressed(self, tree):
        key = self._resolve(self.visit(tree.children[0]))
        pressed = get_extension_input("pressedKeys", [])
        return key in pressed

    def start_(self, tree):
        self.register_start_script(tree.children)

    def run_(self, tree):
        Clage_emit_state()

    def on_scheduler_tick(self):
        Clage_emit_state()
