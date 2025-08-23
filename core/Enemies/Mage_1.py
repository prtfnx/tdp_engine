from os import path
from core.Enemy import Enemy
from core.actions_protocol import Position
import sdl3
import random
import uuid
import math

SPEED = 0.01
SHOOT_CD = 1400
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
            "idle": "resources/sounds/mage_1/idle",
            "move": "resources/sounds/mage_1/move",
            "attack": "resources/sounds/mage_1/attack",
            "pain": "resources/sounds/mage_1/pain"
        }
        self.last_shoot_time = 0
        #TODO make separate system for storage data
        # format for now:
        # dict={
        # 'name':[
        # projectile_path,
        # atlas_path,
        # sound_path,
        # projectile_collision_path,
        # atlas_collision_path,
        # sound_collision_path,
        # ],

        self.dict_of_list_of_projectiles = {
            'electro':[
            "projectile/projectile1.png",
            "resources/projectile/projectile1.json",
            "projectile/projectile1_collision.png",
            "resources/projectile/projectile1_collision.json",
            "resources/sounds/projectile/electro.wav",
            "resources/sounds/projectile/electro_collision.wav",
            ],
            'fireball':[
            "projectile/projectile2.png",
            "resources/projectile/projectile2.json",
            "projectile/projectile2_collision.png",
            "resources/projectile/projectile2_collision.json",
            "resources/sounds/projectile/fireball.wav",
            "resources/sounds/projectile/fireball_collision.wav",
            ]
        }
        self.range_for_attack = 350.0
        self.shoot_CD = SHOOT_CD
        self.speed = SPEED
        self.init_sounds()
        
    def init_sounds(self):
        projectiles = [key for key in self.dict_of_list_of_projectiles.keys()]
        self.sounds = {}
        for projectile in projectiles:
            path_to_sound = self.dict_of_list_of_projectiles[projectile][4]
            path_to_collision_sound = self.dict_of_list_of_projectiles[projectile][5]
            self.sounds[projectile] = [
                sdl3.Mix_LoadWAV(path_to_sound.encode()),
                sdl3.Mix_LoadWAV(path_to_collision_sound.encode())
            ]

        self.sounds = {**self.sounds, **self.dict_of_sounds}
    def attack(self):
        super().attack()
        self.shoot()
    
    def shoot(self):
        current_time = sdl3.SDL_GetTicks()   # Get current time in seconds
        if current_time - self.last_shoot_time >= self.shoot_CD:
            self.last_shoot_time = current_time
            projectile = random.choice(list(self.dict_of_list_of_projectiles.keys()))
            sound = self.sounds[projectile][0]
            sdl3.Mix_PlayChannel(-1, sound, 0)  
            self.create_projectile(projectile)  # TODO refactor to proper system
    
    def create_projectile(self, projectile_name):
        """TODO: make proper system for projectiles"""
        if projectile_name in self.dict_of_list_of_projectiles:
            dx, dy = self.angle_to_player(self.context.player)
            paths = self.dict_of_list_of_projectiles[projectile_name]
            projectile_sprite_path = paths[0]
            projectile_atlas_path = paths[1]
            projectile_collision_image_path = paths[2]
            projectile_collision_atlas_path = paths[3]
            projectile_position = Position(self.coord_x.value, self.coord_y.value)
            result = self.context.Actions.create_animated_sprite(
                    table_id=self.context.current_table.table_id,
                    sprite_id=uuid.uuid4().hex,
                    position=projectile_position,
                    image_path=projectile_sprite_path,
                    frame_duration=100,
                    scale_x=0.5,
                    scale_y=0.5,
                    rotation=math.atan2(dy, dx),
                    moving=True,
                    speed=0.5,
                    collidable=True,
                    layer='projectiles',
                    atlas_path=projectile_atlas_path,
            )
            if result.success:
                sprite = result.data['sprite']
                sprite.on_collision= {
                    'image_path': projectile_collision_image_path,
                    'atlas_path': projectile_collision_atlas_path,
                    'sound': self.sounds[projectile_name][1]
                }
                sprite.is_enemy = True
                sprite.enemy_type = self.name
                sprite.set_position(self.coord_x.value, self.coord_y.value)
                sprite.speed_friction = 1.005  # Apply friction
                sprite.is_player = True
                sprite.set_die_timer(5000)
                # Calculate direction using table coordinates
                length = (dx ** 2 + dy ** 2) ** 0.5            
                if length > 0:
                    vx = dx / length
                    vy = dy / length
                    sprite.set_speed(vx * sprite.speed, vy * sprite.speed)
            