import math
import sdl3
import uuid
from typing import Optional, TYPE_CHECKING
from ctypes import c_float, byref
from venv import logger
from enum import Enum, auto
from core.actions_protocol import Position
if TYPE_CHECKING:
    from core.Sprite import Sprite
ACCELERATION_COEF = 0.1
SPEED_COEF = 0.01
EPSILON = 0.001  # Small value to avoid floating point precision issues
SHOOT_COOLDOWN = 0.5  # 500 ms cooldown for shooting
class PlayerState(Enum):
    IDLE = auto()
    MOVING = auto()
    SHOOTING = auto()
    DYING = auto()

class Player():
    def __init__(self, name: str, context):
        self.name: str = name
        self.coord_x: c_float = c_float(0.0)  # ctypes.c_float
        self.coord_y: c_float = c_float(0.0)  # ctypes.c_float
        self.health: int = 100
        self.score: int = 0
        self.level: int = 1
        self.is_alive: bool = True
        self.speed: float = 0
        self.direction: float = 0
        self.acceleration: float = 0
        self.sprite: Optional[Sprite] = None        
        self.go_x: bool = False
        self.go_y: bool = False
        self.state = PlayerState.IDLE
        self.context = context
        #timers
        self.shoot_CD = SHOOT_COOLDOWN
        self.last_shoot_time = 0  # Timestamp of the last shot
        self.last_state_change_time = 0  # Timestamp of the last state change
        # Data
        self.sprite_dict = {}
        self.sound_effects_dict = {}
        self.sprite_bullet_dict = {}
        self.inventory: list = []




    def set_state(self, new_state: PlayerState):
        match new_state:
            case PlayerState.IDLE:
                self.speed = 0
                sprite_player_idle = self.sprite_dict.get("sprite_player_idle")
                sprite_player_idle.coord_x = self.coord_x
                sprite_player_idle.coord_y = self.coord_y
                sprite_player_idle.rotation = self.sprite.rotation
                self.sprite.visible = False
                self.sprite = sprite_player_idle
                self.sprite.visible = True
                sprite_foots_run = self.sprite_dict.get("sprite_foots_run")
                sprite_foots_run.visible = False

            case PlayerState.MOVING:                
                sprite_player_move = self.sprite_dict.get("sprite_player_move")
                sprite_player_move.coord_x = self.coord_x
                sprite_player_move.coord_y = self.coord_y
                sprite_player_move.rotation = self.sprite.rotation                
                self.sprite.visible = False
                self.sprite = sprite_player_move
                self.sprite.visible = True
                # Handle foots
                sprite_foots_run = self.sprite_dict.get("sprite_foots_run")
                sprite_foots_run.coord_x = self.coord_x
                sprite_foots_run.coord_y = self.coord_y
                sprite_foots_run.rotation = self.sprite.rotation
                sprite_foots_run.visible = True

            case PlayerState.SHOOTING:
                sprite_player_shoot = self.sprite_dict.get("sprite_player_shoot")
                sprite_player_shoot.coord_x = self.coord_x
                sprite_player_shoot.coord_y = self.coord_y
                sprite_player_shoot.rotation = self.sprite.rotation
                self.sprite.visible = False
                self.sprite = sprite_player_shoot
                self.sprite.visible = True
                sprite_foots_run = self.sprite_dict.get("sprite_foots_run")
                sprite_foots_run.visible = False
            case PlayerState.DYING:
                pass #TODO
        self.state = new_state

    def move(self, dx: int, dy: int):
        """Fallback move implementation."""
        self.coord_x.value += dx
        self.coord_y.value += dy

    def pick_item(self, item):
        # TBD
        self.inventory.append(item)

    def drop_item(self, item):
        # TBD
        self.inventory.remove(item)
    
    def set_acceleration(self, ax: float, ay: float):
        """Set acceleration in x and y directions."""
        self.acceleration_x = ax
        self.acceleration_y = ay

    def update_moving(self,move_x:bool, move_y:bool):
        """Update moving state based on input."""
        self.go_x = move_x
        self.go_y = move_y


    def update_acceleration(self, dt, acceleration_friction: float):
        """Update acceleration based on friction and time delta (dt)."""
        if not hasattr(self, 'acceleration_x'):
            self.acceleration_x = 0
        if not hasattr(self, 'acceleration_y'):
            self.acceleration_y = 0        
        if self.go_x:
            self.acceleration_x += dt * ACCELERATION_COEF
            self.go_x = False
        if self.go_y:
            self.acceleration_y += dt * ACCELERATION_COEF
            self.go_y = False
        # Exponential decay for variable dt
        self.acceleration_x *= acceleration_friction ** dt
        self.acceleration_y *= acceleration_friction ** dt

    def update_speed(self, dt: float, speed_friction: float):
        """Update speed based on acceleration and time delta (dt)."""
        if not hasattr(self, 'acceleration_x'):
            self.acceleration_x = 0
        if not hasattr(self, 'acceleration_y'):
            self.acceleration_y = 0
        if not hasattr(self, 'speed_x'):
            self.speed_x = 0
        if not hasattr(self, 'speed_y'):
            self.speed_y = 0
        self.speed_x += self.acceleration_x * dt * SPEED_COEF
        self.speed_y += self.acceleration_y * dt * SPEED_COEF
        if abs(self.speed_x) < EPSILON:
            self.speed_x = 0
        else:
            self.speed_x *= speed_friction**dt
        if abs(self.speed_y) < EPSILON:
            self.speed_y = 0
        else:
            self.speed_y *= speed_friction**dt

    def update_position(self, dt: float):
        """Update position based on speed and time delta (dt)."""
        if not hasattr(self, 'speed_x'):
            self.speed_x = 0
        if not hasattr(self, 'speed_y'):
            self.speed_y = 0
        motion_x= self.speed_x * dt
        motion_y= self.speed_y * dt
        self.coord_x.value += motion_x
        self.coord_y.value += motion_y
        
    def sprite_step(self):
        """Update player sprite based on current state."""    
        self.sprite_dict["sprite_foots_run"].rotation = self.weapon_angle
    def state_step(self):
        """Update player state based on current conditions."""
        if self.state == PlayerState.SHOOTING and self.last_shoot_time > 1:
            if self.speed == 0:
                logger.debug("Player is idle after shooting, updating state to IDLE.")
                self.update_state(PlayerState.IDLE)
            else:
                logger.debug("Player is moving after shooting, updating state to MOVING.")
                self.update_state(PlayerState.MOVING)
        elif self.state == PlayerState.IDLE and (self.speed_x != 0 or self.speed_y != 0):
            logger.debug("Player is moving after being idle, updating state to MOVING.")
            self.update_state(PlayerState.MOVING)
        elif self.state == PlayerState.MOVING and self.speed_x == 0 and self.speed_y == 0:
            logger.debug("Player is idle after being moving, updating state to IDLE.")
            self.update_state(PlayerState.IDLE)
        if self.state == PlayerState.MOVING:
            self.sprite_step()

    def physics_step(self, dt: float, acceleration_friction: float=1.0, speed_friction: float=1.0):
        """Update acceleration, speed and position for a physics step."""
        self.update_acceleration(dt, acceleration_friction)
        self.update_speed(dt, speed_friction)
        self.update_position(dt)
        self.state_step()

        

    def update_state(self, state: PlayerState):
        """Update player state and reset timers."""        
        if state != self.state:
            self.set_state(state)
            self.last_state_change_time = sdl3.SDL_GetTicks() / 1000.0  # Reset timer

    def set_weapon_direction(self, mouse_x: float, mouse_y: float):
        """Set weapon direction based on mouse position."""
        dx = mouse_x - self.coord_x.value
        dy = mouse_y - self.coord_y.value
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length != 0:
            self.weapon_dir = (dx / length, dy / length)
        else:
            self.weapon_dir = (0, 0)        
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        self.weapon_angle = angle
        self.sprite.rotation = self.weapon_angle
    
    def shoot(self):
        current_time = sdl3.SDL_GetTicks() / 1000.0  # Get current time in seconds
        if current_time - self.last_shoot_time >= self.shoot_CD:
            self.last_shoot_time = current_time
            self.update_state(PlayerState.SHOOTING)
            print("Shooting!")
            self.create_bullet() # TODO refactor to proper system    

    def create_bullet(self):
        x, y = c_float(), c_float()
        sdl3.SDL_GetMouseState(byref(x), byref(y))
        logger.info(f"Mouse pos {x.value}, {y.value}")
        table = self.context.current_table            
        # Convert mouse screen coordinates to table coordinates
        if hasattr(table, 'screen_to_table'):
            target_table_x, target_table_y = table.screen_to_table(x.value, y.value)
        table_id = table.table_id if hasattr(table, 'table_id') else table.name
        bullet_sprite_path = self.sprite_bullet_dict['sprite_path']
        bullet_atlas_path = self.sprite_bullet_dict['atlas_path']
        bullet_position = Position(self.coord_x.value, self.coord_y.value)
        result = self.context.Actions.create_animated_sprite(
                table_id=table_id,
                sprite_id=uuid.uuid4().hex,
                position=bullet_position,
                image_path=bullet_sprite_path,
                frame_duration=1,
                scale_x=1.5,
                scale_y=1.5,
                moving=True,
                speed=1.5,
                collidable=True,
                atlas_path=bullet_atlas_path,
                die_timer=2
        )        
        sprite = result.data['sprite']
        sprite.set_position(self.coord_x.value, self.coord_y.value)
        
        # Calculate direction using table coordinates
        dx = target_table_x - self.coord_x.value
        dy = target_table_y - self.coord_y.value
        length = (dx ** 2 + dy ** 2) ** 0.5
        
        if length > 0:
            vx = dx / length
            vy = dy / length
            sprite.set_speed(vx * sprite.speed, vy * sprite.speed)
