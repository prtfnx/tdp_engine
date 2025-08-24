from core.Enemy import Enemy
SPEED = 1
class Minotaur(Enemy):
    def __init__(self, coord_x=0, coord_y=0):
        super().__init__(name="Minotaur", coord_x=coord_x, coord_y=coord_y, health=150, damage=25)
        self.sprite_idle_path="Minotaur_1/idle.png"
        self.sprite_idle_atlas="resources/Minotaur_1/idle.json"
        self.sprite_move_path="Minotaur_1/Walk.png"
        self.sprite_move_atlas="resources/Minotaur_1/Walk.json"
        self.sprite_attack_path="Minotaur_1/attack.png"
        self.sprite_attack_atlas="resources/Minotaur_1/attack.json"
        self.save_path_to_sprites_and_atlases()
        self.dict_of_sounds = {
            "idle": "resources/sounds/minotaur/idle",
            "move": "resources/sounds/minotaur/move",
            "attack": "resources/sounds/minotaur/attack",
            "pain": "resources/sounds/minotaur/pain"
        }
        self.footstep_sounds_folder =["resources/sounds/minotaur/footsteps"]         
        self.speed = SPEED
        self.range_for_attack = 1
        self.attack_cd = 500
        self.is_flipped = False
        self.sounds ={}