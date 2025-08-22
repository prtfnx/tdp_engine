from venv import logger
from core.Enemy import Enemy
from core.Enemies.Mage_1 import Mage_1
from core.Enemies.Minotaur import Minotaur
import core.Actions
from tools.logger import setup_logger

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

    def add_enemy(self, enemy):
        if enemy in self.ENEMY_TYPE_MAP.keys():
            enemy_object = self.ENEMY_TYPE_MAP[enemy]()
            self.enemies.append(enemy_object)
            logger.info(f"Added enemy: {enemy_object}")
        else:
            logger.error(f"Failed to add enemy: {enemy}")
            raise ValueError(f"Enemy type '{enemy}' is not recognized.")
    def prepare_enemies(self):
        for enemy in self.enemies:
            enemy.prepare()

    def update(self, player, obstacles_np):
        for enemy in self.enemies:
            enemy.update(self.cast_ray, player, obstacles_np)

    def create_enemy(self, enemy_type) -> Enemy | None:
        if enemy_class := self.ENEMY_TYPE_MAP.get(enemy_type):
            enemy = enemy_class()
            self.add_enemy(enemy)           
            return enemy
        return None
    
