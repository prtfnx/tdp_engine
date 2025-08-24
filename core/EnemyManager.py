from venv import logger
from core.Enemy import Enemy
from core.Enemies.Mage_1 import Mage_1
from core.Enemies.Minotaur import Minotaur
import os
from tools.logger import setup_logger
import sdl3
logger = setup_logger(__name__)

class EnemyManager:
    ENEMY_TYPE_MAP = {
        "Mage_1": Mage_1,
        "Minotaur": Minotaur,
        
    }
    def __init__(self):
        self.enemies = []
        self.player = None
        # interface for cast ray:
        self.cast_ray = None
        self.context = None
        

    def add_enemy(self, enemy, coord_x=0, coord_y=0):
        if enemy in self.ENEMY_TYPE_MAP.keys():
            enemy_object = self.ENEMY_TYPE_MAP[enemy](coord_x=coord_x, coord_y=coord_y)
            if hasattr(enemy_object, 'footstep_sounds_folder'):
                enemy_object.footstep_sounds = [sdl3.Mix_LoadWAV(os.path.join(folder, path).encode()) for folder in enemy_object.footstep_sounds_folder for path in os.listdir(folder) if path.endswith(".wav")]
            for key, value in enemy_object.dict_of_sounds.items():
                print(f"Loading sounds for {key}: {value}")
                enemy_object.sounds[key] = [sdl3.Mix_LoadWAV(os.path.join(value, path).encode()) for path in os.listdir(value) if path.endswith(".wav")]
            self.enemies.append(enemy_object)
            logger.info(f"Added enemy: {enemy_object}")
            enemy_object.context = self.context
        else:
            logger.error(f"Failed to add enemy: {enemy}")
            raise ValueError(f"Enemy type '{enemy}' is not recognized.")
    def prepare_enemies(self):
        for enemy in self.enemies:
            enemy.prepare()

    def update(self, player, obstacles_np, dt):
        if not self.context.is_gm:
            for enemy in self.enemies:
                enemy.update(self.cast_ray, player, dt, obstacles_np)

    def create_enemy(self, enemy_type) -> Enemy | None:
        if enemy_class := self.ENEMY_TYPE_MAP.get(enemy_type):
            enemy = enemy_class()
            self.add_enemy(enemy)           
            return enemy
        return None
    
