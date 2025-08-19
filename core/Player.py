from typing import Optional, TYPE_CHECKING
from ctypes import c_float
if TYPE_CHECKING:
    from core.Sprite import Sprite
ACCELERATION_COEF = 0.0001
SPEED_COEF = 0.0001

class Player():
    def __init__(self, name: str):
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
        self.inventory: list = []
        self.go_x: bool = False
        self.go_y: bool = False


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

    def update_acceleration(self, dt, friction: float):
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
        self.acceleration_x -= friction * dt
        self.acceleration_y -= friction * dt

    def update_speed(self, dt: float):
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

    def update_position(self, dt: float):
        """Update position based on speed and time delta (dt)."""
        if not hasattr(self, 'speed_x'):
            self.speed_x = 0
        if not hasattr(self, 'speed_y'):
            self.speed_y = 0
        self.coord_x.value += self.speed_x * dt
        self.coord_y.value += self.speed_y * dt

    def physics_step(self, dt: float, friction: float=1.0):
        """Update acceleration, speed and position for a physics step."""
        self.update_acceleration(dt, friction)
        self.update_speed(dt)
        self.update_position(dt)
    
    def set_weapon_direction(self, mouse_x: float, mouse_y: float):
        """Set weapon direction based on mouse position."""
        dx = mouse_x - self.coord_x.value
        dy = mouse_y - self.coord_y.value
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length != 0:
            self.weapon_dir = (dx / length, dy / length)
        else:
            self.weapon_dir = (0, 0)
        import math
        self.weapon_angle = math.atan2(dy, dx)
