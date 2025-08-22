from core.Enemy import Enemy
class Mage_1(Enemy):
    def __init__(self):
        super().__init__(name="Mage_1", health=80, damage=15)        
        self.sprite_idle_path="spritesheets/mage-1-85x94.png"
        self.sprite_idle_atlas="resources/spritesheets/mage-1-85x94.json"
        self.sprite_move_path="spritesheets/mage-1-85x94.png"
        self.sprite_move_atlas="resources/spritesheets/mage-1-85x94.json"
        self.sprite_attack_path="spritesheets/mage-1-85x94.png"
        self.sprite_attack_atlas="resources/spritesheets/mage-1-85x94.json"
        self.save_path_to_sprites_and_atlases()
        self.dict_of_sounds = {
            "idle": "resources/spritesheets/mage-1-85x94/sounds/idle.wav",
            "move": "resources/spritesheets/mage-1-85x94/sounds/move.wav",
            "attack": "resources/spritesheets/mage-1-85x94/sounds/attack.wav"
        }
        self.range_for_attack = 400.0