import copy
import math
import time


Clage_sprites = {}
Clage_clone_scripts = {}
Clage_clone_sources = {}
Clage_clones_by_source = {}
Clage_state_dirty = True
Clage_last_emit_at = 0.0
Clage_emit_interval = 1 / 30


def Clage_reset_state():
    global Clage_state_dirty, Clage_last_emit_at
    Clage_sprites.clear()
    Clage_clone_scripts.clear()
    Clage_clone_sources.clear()
    Clage_clones_by_source.clear()
    Clage_state_dirty = True
    Clage_last_emit_at = 0.0


def Clage_export_state():
    return {
        "sprites": copy.deepcopy(Clage_sprites),
        "clone_sources": copy.deepcopy(Clage_clone_sources),
    }


def Clage_import_state(state):
    global Clage_state_dirty
    Clage_sprites.clear()
    Clage_sprites.update(copy.deepcopy((state or {}).get("sprites", {})))
    Clage_clone_sources.clear()
    Clage_clone_sources.update(copy.deepcopy((state or {}).get("clone_sources", {})))
    Clage_rebuild_clone_index()
    Clage_state_dirty = True


def Clage_mark_dirty():
    global Clage_state_dirty
    Clage_state_dirty = True


def Clage_render_sprite_state():
    return {
        name: {
            "x": sprite.get("x", 0),
            "y": sprite.get("y", 0),
            "direction": sprite.get("direction", 90),
            "costume": sprite.get("costume", ""),
            "visible": sprite.get("visible", True),
            "width": sprite.get("width", 44),
            "height": sprite.get("height", 44),
        }
        for name, sprite in Clage_sprites.items()
    }


def Clage_emit_state(force=False):
    global Clage_state_dirty, Clage_last_emit_at
    if not force and not Clage_state_dirty:
        return

    now = time.monotonic()
    if not force and now - Clage_last_emit_at < Clage_emit_interval:
        return

    emit_extension_event("Clage", "state", {"sprites": Clage_render_sprite_state()})
    Clage_state_dirty = False
    Clage_last_emit_at = now


def Clage_rebuild_clone_index():
    Clage_clones_by_source.clear()
    for clone_name, source_name in Clage_clone_sources.items():
        if clone_name in Clage_sprites:
            Clage_clones_by_source.setdefault(source_name, set()).add(clone_name)


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
        Clage_mark_dirty()

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
        Clage_mark_dirty()

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
        Clage_mark_dirty()

    def x_assignment(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        Clage_sprites[sprite_name]["x"] = self._resolve(self.visit(tree.children[1]))
        Clage_mark_dirty()

    def y_assignment(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        Clage_sprites[sprite_name]["y"] = self._resolve(self.visit(tree.children[1]))
        Clage_mark_dirty()

    def direction_assignment(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        direction = self._resolve(self.visit(tree.children[1]))
        Clage_sprites[sprite_name]["direction"] = ((direction + 180) % 360) - 180
        Clage_mark_dirty()

    def x_position(self, tree):
        return Clage_sprites[self.resolve_sprite(tree.children[0])]["x"]

    def y_position(self, tree):
        return Clage_sprites[self.resolve_sprite(tree.children[0])]["y"]

    def direction(self, tree):
        return Clage_sprites[self.resolve_sprite(tree.children[0])]["direction"]

    def costume(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        Clage_sprites[sprite_name]["costume"] = self._resolve(self.visit(tree.children[1]))
        Clage_mark_dirty()

    def show(self, tree):
        Clage_sprites[self.resolve_sprite(tree.children[0])]["visible"] = True
        Clage_mark_dirty()

    def hide(self, tree):
        Clage_sprites[self.resolve_sprite(tree.children[0])]["visible"] = False
        Clage_mark_dirty()

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
        Clage_clones_by_source.setdefault(source_name, set()).add(clone_name)
        commands = Clage_clone_scripts.get(source_name)
        if commands is not None:
            self.register_runtime_script(commands, context={"clone_name": clone_name})
        Clage_mark_dirty()
        return clone_name

    def clone_delete(self, tree):
        clone_name = self.current_clone_name
        if clone_name is None:
            raise ClambonError("clone.delete() は clone ブロックの中だけで使えます。")
        self.delete_clone(clone_name)
        Clage_mark_dirty()
        self.cancel_current_task()

    def delete_clone(self, clone_name):
        source_name = Clage_clone_sources.pop(clone_name, None)
        Clage_sprites.pop(clone_name, None)
        if source_name in Clage_clones_by_source:
            Clage_clones_by_source[source_name].discard(clone_name)
            if not Clage_clones_by_source[source_name]:
                Clage_clones_by_source.pop(source_name, None)

    def resolve_sprite_group(self, sprite_name):
        group = []
        if sprite_name in Clage_sprites:
            group.append(sprite_name)
        group.extend(
            clone_name
            for clone_name in Clage_clones_by_source.get(sprite_name, ())
            if clone_name in Clage_sprites
        )
        return group

    def touching(self, tree):
        sprite_name = self.resolve_sprite(tree.children[0])
        target_name = self.resolve_sprite(tree.children[1])
        if target_name == "edge":
            return any(self.touching_edge(name) for name in self.resolve_sprite_group(sprite_name))
        return self.touching_group(sprite_name, target_name)

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

    def touching_group(self, sprite_name, target_name):
        sprite_names = self.resolve_sprite_group(sprite_name)
        target_names = self.resolve_sprite_group(target_name)
        return any(
            source_name != candidate_name
            and self.touching_sprite(source_name, candidate_name)
            for source_name in sprite_names
            for candidate_name in target_names
        )

    def key_pressed(self, tree):
        key = self._resolve(self.visit(tree.children[0]))
        pressed = get_extension_input("pressedKeys", [])
        return key in pressed

    def start_(self, tree):
        self.register_start_script(tree.children)

    def run_(self, tree):
        Clage_emit_state(force=True)

    def on_scheduler_tick(self):
        Clage_emit_state()
