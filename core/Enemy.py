import dis
from enum import Enum, auto
from typing import Optional
from ctypes import c_float
from core.actions_protocol import Position
import sdl3
import uuid
from tools.logger import setup_logger
logger = setup_logger(__name__)

HEALTH_FOR_FLEE = 20
TIME_FOR_SEARCHING = 5000
IDLE_VISION_DISTANCE = 500
SEARCH_VISION_DISTANCE = 1000


class EnemyState(Enum):
    IDLE = auto()
    DISTURBED = auto()
    SEARCHING = auto()
    PATROLLING = auto()
    CHASING = auto()
    ATTACKING = auto()
    FLEEING = auto()

class Enemy:
    def __init__(self, name, health, damage, coord_x = 500.0, coord_y = 500.0):
        self.name = name
        self.health: int = health
        self.damage: int = damage
        self.dict_of_sprites: dict = {}
        self.state: EnemyState = EnemyState.IDLE
        self.disturbed_from: Optional[Position] = None
        self.coord_x: c_float = c_float(coord_x)
        self.coord_y: c_float = c_float(coord_y)
        self.speed_x: float = 0.0
        self.speed_y: float = 0.0
        self.speed: float = 1.0
        self.list_of_sprites_path: list[str] = []
        self.list_of_atlas_path: list[str] = []
        self.enemy_id =  '_'.join([name,str(uuid.uuid4())])
        # settings
        self.vision_distance: float = IDLE_VISION_DISTANCE
        # Data:
        self.sprite_idle_path: str = ""
        self.sprite_move_path: str = ""
        self.sprite_attack_path: str = ""
        self.sprite_idle_atlas: str = ""
        self.sprite_move_atlas: str = ""
        self.sprite_attack_atlas: str = ""
        self.last_known_player_position: Optional[Position] = None

    def prepare(self):
        for sprite in self.dict_of_sprites.values():
            sprite.coord_x = self.coord_x
            sprite.coord_y = self.coord_y
            sprite.visible = False
            sprite.collidable = False
            logger.debug(f"Preparing enemy: {self.enemy_id} with sprites: {sprite} that is visible{sprite.visible} and collidable {sprite.collidable}")
        self.set_state(EnemyState.IDLE)

    def save_path_to_sprites_and_atlases(self):
        self.list_of_sprites_path.extend([
            self.sprite_idle_path,
            self.sprite_move_path,
            self.sprite_attack_path
        ])
        self.list_of_atlas_path.extend([
            self.sprite_idle_atlas,
            self.sprite_move_atlas,
            self.sprite_attack_atlas
        ])

    def set_position(self, x: float, y: float):
        self.coord_x.value = x
        self.coord_y.value = y

    def attack(self, target):
        # projectile or melee attack
        pass

    def move(self):
        logger.debug(f"Enemy {self.name} moving from ({self.coord_x.value}, {self.coord_y.value}) with speed ({self.speed_x}, {self.speed_y}) and speed factor {self.speed}")
        self.coord_x.value += self.speed_x*self.speed
        self.coord_y.value += self.speed_y*self.speed
        logger.debug(f"Enemy {self.name} moved to ({self.coord_x.value}, {self.coord_y.value})")
    def try_find_player(self, cast_ray,  player, obstacles_np) -> bool:
       """Cast ray to player and check obstacles"""
       #TODO implement proper system for rays and checks in group, for now dirty hack
       finded= cast_ray(self.sprite.frect, player.sprite.frect, obstacles_np, self.vision_distance, threshold= 100.0)      
       logger.debug(f"Enemy {self.name} trying to find player: {finded}")       
       if finded:
           self.last_known_player_position = Position(player.coord_x.value, player.coord_y.value)
       return finded

    
    def update(self, cast_ray,player, obstacles_np):
        logger.debug(f"Updating enemy {self.name} at position ({self.coord_x.value}, {self.coord_y.value}) with health {self.health} in state {self.state}")
        if self.health <= HEALTH_FOR_FLEE:
            self.set_state(EnemyState.FLEEING)
        else:
            match self.state:
                case EnemyState.IDLE:
                    if self.try_find_player(cast_ray,  player, obstacles_np):
                        self.set_state(EnemyState.CHASING)
                case EnemyState.DISTURBED:
                    # Logic for disturbed state
                    if self.try_find_player(cast_ray,  player=player, obstacles_np=obstacles_np):
                        self.set_state(EnemyState.CHASING)
                    else:
                        self.set_state(EnemyState.SEARCHING)
                case EnemyState.SEARCHING:
                    self.move()
                    if self.try_find_player(cast_ray, player=player, obstacles_np=obstacles_np):
                        self.set_state(EnemyState.CHASING)
                    elif  sdl3.SDL_GetTicks() - self.timer_for_searching > TIME_FOR_SEARCHING:
                        self.set_state(EnemyState.IDLE)
                case EnemyState.PATROLLING:
                    if self.try_find_player(cast_ray,  player=player, obstacles_np=obstacles_np):
                        self.set_state(EnemyState.CHASING)
                    # Logic for patrolling
                    pass
                case EnemyState.CHASING:
                    self.move()
                    if self.try_find_player(cast_ray,  player=player, obstacles_np=obstacles_np):
                        distance=self.set_direction()
                        logger.debug(f"Enemy {self.name} is chasing player, distance to player: {distance}, range for attack: {self.range_for_attack}")
                        if distance < self.range_for_attack:
                            self.set_state(EnemyState.ATTACKING)
                    else:
                        self.set_state(EnemyState.SEARCHING)
                case EnemyState.ATTACKING:
                    if self.try_find_player(cast_ray, player=player, obstacles_np=obstacles_np):
                        # Logic to attack the player
                        self.attack(player)
                        distance=self.set_direction()
                        if distance > self.range_for_attack:
                            self.set_state(EnemyState.CHASING)
                    else:
                        self.set_state(EnemyState.SEARCHING)
                case EnemyState.FLEEING:
                    # Logic to flee from the player
                    pass

    def set_direction(self) -> float:
        """
        Returns normalized direction vector (dx, dy) from enemy to last known player position.
        If last_known_player_position is None, returns (0.0, 0.0).
        """
        if self.last_known_player_position is None:
            return 0.0
        dx = self.last_known_player_position.x - self.coord_x.value
        dy = self.last_known_player_position.y - self.coord_y.value
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length < 1e-6:
            dx,dy = (0.0, 0.0)
        self.speed_x = dx / length
        self.speed_y = dy / length
        logger.debug(f"Enemy {self.name} set direction to ({self.speed_x}, {self.speed_y}) towards last known player position ({self.last_known_player_position.x}, {self.last_known_player_position.y})")
        return length

    def set_state(self, new_state: EnemyState):
        # TODO logic for state transition
        self.sprite.collidable = False
        self.sprite.visible = False
        match new_state:
            case EnemyState.IDLE:
                self.speed_x = 0.0
                self.speed_y = 0.0
                self.sprite = self.dict_of_sprites["sprite_enemy_idle"]
                self.vision_distance = IDLE_VISION_DISTANCE
            case EnemyState.DISTURBED:
                self.sprite = self.dict_of_sprites["sprite_enemy_attack"]
                self.vision_distance = SEARCH_VISION_DISTANCE
            case EnemyState.SEARCHING:
                self.timer_for_searching = sdl3.SDL_GetTicks()
                self.sprite = self.dict_of_sprites["sprite_enemy_walk"]
                self.vision_distance = SEARCH_VISION_DISTANCE
            case EnemyState.CHASING:        
                self.sprite = self.dict_of_sprites["sprite_enemy_walk"]
                self.vision_distance = SEARCH_VISION_DISTANCE
                self.set_direction()                
            case EnemyState.PATROLLING:
                self.sprite = self.dict_of_sprites["sprite_enemy_walk"] 
                self.vision_distance = SEARCH_VISION_DISTANCE         
            case EnemyState.ATTACKING:
                self.sprite = self.dict_of_sprites["sprite_enemy_attack"]
                self.vision_distance = SEARCH_VISION_DISTANCE
            case EnemyState.FLEEING:
                self.sprite = self.dict_of_sprites["sprite_enemy_fleeing"]
                self.vision_distance = SEARCH_VISION_DISTANCE
        logger.debug(f"Enemy {self.name} changed state from {self.state} to {new_state}, sprite {self.sprite}, visible {self.sprite.visible}, collidable {self.sprite.collidable}")        
        self.sprite.collidable = True
        self.sprite.visible = True
        self.state = new_state
