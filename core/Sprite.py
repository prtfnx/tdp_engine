import ctypes
from tools.logger import setup_logger
from typing import Optional, Union, Dict, Any, TYPE_CHECKING
import sdl3
import uuid
import time
import json
import re

# Import types for type checking
if TYPE_CHECKING:     
    from Context import Context
    from ContextTable import ContextTable

logger = setup_logger(__name__)

class Sprite:
    """A sprite represents a visual entity on the game table with position, texture, and game logic."""
    
    def __init__(self, 
                 renderer: Any,  # SDL_Renderer 
                 texture_path: Union[str, bytes], 
                 scale_x: float = 1, 
                 scale_y: float = 1,
                 character: Optional[Any] = None, 
                 moving: bool = False, 
                 speed: Optional[float] = None, 
                 collidable: bool = False,
                 texture: Optional[Any] = None,  # SDL_Texture
                 layer: str = 'tokens', 
                 coord_x: float = 0.0, 
                 coord_y: float = 0.0,
                 compendium_entity: Optional[Any] = None, 
                 entity_type: Optional[str] = None, 
                 sprite_id: Optional[str] = None, 
                 die_timer: Optional[float] = None,
                 asset_id: Optional[str] = None, 
                 context: Optional['Context'] = None,
                 visible: bool = True,
                 rotation: float = 0.0,
                 is_player: bool = False) -> None:
        # Initialize all ctypes structures properly
        self.coord_x: ctypes.c_float = ctypes.c_float(coord_x)  
        self.coord_y: ctypes.c_float = ctypes.c_float(coord_y)  
        self.rect: sdl3.SDL_Rect = sdl3.SDL_Rect() 
        self.frect: sdl3.SDL_FRect = sdl3.SDL_FRect()  

        # Initialize dimensions to prevent access violations
        self.original_w: float = 0.0
        self.original_h: float = 0.0

        # Store basic properties
        self.texture_path: Union[str, bytes] = texture_path
        self.renderer: sdl3.SDL_Renderer = renderer
        self.scale_x: float = scale_x
        self.scale_y: float = scale_y
        self.character = character
        self.moving: bool = moving
        self.speed: Optional[float] = speed
        self.die_timer: Optional[float] = die_timer
        self.collidable: bool = collidable
        self.layer: str = layer
        self.texture: Optional[sdl3.SDL_Texture] = None
        self.rotation: float = rotation
        self.visible: bool = visible  # Visibility flag
          # Compendium entity support
        self.compendium_entity: Optional[Any] = compendium_entity
        self.entity_type: Optional[str] = entity_type
        self.sprite_id: str = sprite_id if sprite_id is not None else str(uuid.uuid4())
          # R2 Asset support
        self.asset_id: Optional[str] = asset_id
        self.context: Optional['Context'] = context  # Store context reference for R2 requests

        # Add name attribute for identification
        if compendium_entity and hasattr(compendium_entity, 'name'):
            self.name: Optional[str] = compendium_entity.name
        else:
            self.name: Optional[str] = None
        self.is_player: bool = is_player  # Default to not a player sprite
        # Initialize movement properties
        self.dx: float = 0.0
        self.dy: float = 0.0

        # Store previous position for network sync
        self._last_network_x: float = coord_x
        self._last_network_y: float = coord_y

        # Load texture last, after everything is initialized
        logger.info(f"created sprite {self.sprite_id} at ({coord_x}, {coord_y}) with texture path {texture_path}")
        try:
            #io_sys.load_texture(self, context)
            #self.set_texture(texture_path)
            pass
        except Exception as e:
            logger.error(f"Failed to load texture {texture_path}: {e}")
            self.texture = None

    def __repr__(self) -> str:
        return (f"Sprite(coord_x={self.coord_x}, coord_y={self.coord_y}, rect={self.rect}, "
                f"frect={self.frect}, texture_path={self.texture_path}, scale_x={self.scale_x}, scale_y={self.scale_y})")

    def __str__(self) -> str:
        return (f"Sprite at ({self.coord_x.value}, {self.coord_y.value}) "
                f"with texture {self.texture_path} and scale {self.scale_x} {self.scale_y}")    
    
    def set_speed(self, dx: float, dy: float) -> None:
        self.dx = dx
        self.dy = dy

    def move(self, delta_time: float) -> None:
        if self.moving:
            self.coord_x.value += self.dx * delta_time
            self.coord_y.value += self.dy * delta_time
            # Apply speed friction
            if self.speed_friction:
                self.dx *= self.speed_friction            
                self.dy *= self.speed_friction

    def set_die_timer(self, time: float) -> None:
        self.die_timer = time
    
    def set_texture(self, texture_path: Union[str, bytes], context: Optional['Context'] = None) -> bool:
        """Set texture with proper error handling"""
        self.texture_path = texture_path
        logger.info("Setting texture path: %s", texture_path)
        
        # Use provided context or fall back to instance context
        ctx = context or self.context
        
        try:
            #self.texture = io_sys.load_texture(self, ctx)
            if not self.texture:
                logger.error(f"Failed to load texture: {texture_path}")
                return False
            return True
        except Exception as e:
            logger.error(f"Exception loading texture {texture_path}: {e}")
            self.texture = None
            return False

    def set_position(self, x: float, y: float) -> None:
        #TODO: fix logic for setting frect
        self.coord_x.value = x
        self.coord_y.value = y
        self.set_frect()

    def set_frect(self) -> None:
        """Fix logic for setting frect - avoid memory corruption"""   
        self.frect.x = ctypes.c_float(self.coord_x.value)
        self.frect.y = ctypes.c_float(self.coord_y.value)
        
        # Only scale if we have original dimensions
        if hasattr(self, 'original_w') and hasattr(self, 'original_h'):
            self.frect.w = ctypes.c_float(self.original_w * self.scale_x)
            self.frect.h = ctypes.c_float(self.original_h * self.scale_y)

    def set_rect(self) -> None:
        self.rect.x = int(self.coord_x)
        self.rect.y = int(self.coord_y)
        self.rect.w = int(self.frect.w * self.scale_x)
        self.rect.h = int(self.frect.h * self.scale_y)
        
    def set_original_size(self) -> None:
        """Set original size with validation"""
        if self.frect.w > 0 and self.frect.h > 0:
            self.original_w = float(self.frect.w)
            self.original_h = float(self.frect.h)
        else:
            logger.warning(f"Invalid frect dimensions: {self.frect.w}x{self.frect.h}")
            self.original_w = 32.0  # Default fallback
            self.original_h = 32.0
            
    def die(self) -> None:
        #TODO: remove
        self.cleanup()

    def cleanup(self) -> None:
        """Clean up sprite resources"""
        try:
            if hasattr(self, 'texture') and self.texture:
                #sdl3.SDL_DestroyTexture(self.texture)# we cache textures
                self.texture = None
                logger.debug(f"Cleaned up texture for sprite: {self.texture_path}")
        except Exception as e:
            logger.error(f"Error cleaning up sprite texture: {e}")

    def reload_texture(self, texture: Any, w: int, h: int) -> bool:  # texture: SDL_Texture
        """Reload texture"""     
        old_texture = self.texture        
        self.texture = texture
        if old_texture and self.texture:
            try:
                sdl3.SDL_DestroyTexture(old_texture)
            except Exception as e:
                logger.error(f"Error destroying old texture: {e}")
            
        if self.texture:            
            self.rect.w = w
            self.rect.h = h           
            self.frect.w = ctypes.c_float(w)
            self.frect.h = ctypes.c_float(h)
            self.original_w = float(w)
            self.original_h = float(h)
        return True
       

    def has_r2_asset(self) -> bool:
        """Check if this sprite has an associated R2 asset"""
        return self.asset_id is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert sprite to dictionary representation"""
        return {
            'sprite_id': self.sprite_id,
            'texture_path': self.texture_path.decode('utf-8'),
            'coord_x': self.coord_x.value,
            'coord_y': self.coord_y.value,
            'scale_x': self.scale_x,
            'scale_y': self.scale_y,
            'frect_w': self.original_w,
            'frect_h': self.original_h,
            'character': self.character,
            'moving': self.moving,
            'speed': self.speed,
            'collidable': self.collidable,
            'layer': self.layer,
            'compendium_entity': self.compendium_entity.to_dict() if self.compendium_entity else None,
            'entity_type': self.entity_type,
            'asset_id': self.asset_id,
            'visibility': self.visible,
            'rotation': self.rotation,
            'die_timer': self.die_timer,
            'asset_id': self.asset_id,
            'is_player': self.is_player,
            'visible': self.visible
        }

class AnimatedSprite(Sprite):
    """A sprite that supports animation with frames."""
    
    def __init__(self, 
                 renderer: Any,  # SDL_Renderer 
                 sheet_path: Union[str, bytes], 
                 frame_rects: list = [],  # List of SDL_Rect or SDL_FRect for each frame
                 frame_duration: float = 100,  # ms per frame
                 scale_x: float = 1,
                 scale_y: float = 1,
                 atlas_path: str = None,
                 is_player: bool = False,
                 **kwargs) -> None:
        super().__init__(renderer, sheet_path, scale_x=scale_x, scale_y=scale_y, is_player=is_player, **kwargs)
        self.sheet_path = sheet_path
        self.frame_rects = frame_rects  # List of rectangles for each frame
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.last_frame_time = int(time.time() * 1000)  # ms
        self.sheet_texture = None  # Will be loaded externally or via set_texture
        self.atlas_path = atlas_path
        if atlas_path:
            self.init_animation()


    def init_animation(self):
        """Init sprite atlas"""
        #TODO - integrate with storage manager
        with open(self.atlas_path, 'r') as f:
            atlas = json.load(f)
        frames = atlas['frames']
        frame_frects = []      
      
        def frame_sort_key(key):
            match = re.search(r'(\d+)\.png$', key)
            return int(match.group(1)) if match else 0

        for key in sorted(frames.keys(), key=frame_sort_key):
            frame = frames[key]['frame']
            print(f"Loading frame {key}: {frame}")
            frect = sdl3.SDL_FRect()
            frect.x = frame['x']
            frect.y = frame['y']
            frect.w = frame['w']
            frect.h = frame['h']
            frame_frects.append(frect)
        
        self.frame_frects = frame_frects

    def update_animation(self):
        """Update the current frame based on elapsed time."""
        now = int(time.time() * 1000)
        if now - self.last_frame_time > self.frame_duration:
           
            self.current_frame = (self.current_frame + 1) % len(self.frame_frects)
            self.last_frame_time = now

    def reload_texture(self, texture: Any, w: int, h: int)-> bool:  # texture: SDL_Texture
        """Reload texture for animated sprite"""     
        old_texture = self.texture        
        self.texture = texture
        if old_texture and self.texture:
            try:
                sdl3.SDL_DestroyTexture(old_texture)
            except Exception as e:
                logger.error(f"Error destroying old texture: {e}")        

        w = int(self.frame_frects[0].w)
        h = int(self.frame_frects[0].h)
        if self.texture:
            self.rect.w = w
            self.rect.h = h           
            self.frect.w = ctypes.c_float(w)
            self.frect.h = ctypes.c_float(h)
            self.original_w = float(w)
            self.original_h = float(h)
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert animated sprite to dictionary representation"""
        return {
            'sprite_id': self.sprite_id,
            'texture_path': self.texture_path.decode('utf-8'),
            'coord_x': self.coord_x.value,
            'coord_y': self.coord_y.value,
            'scale_x': self.scale_x,
            'scale_y': self.scale_y,
            'frect_w': self.original_w,
            'frect_h': self.original_h,
            'character': self.character,
            'moving': self.moving,
            'speed': self.speed,
            'collidable': self.collidable,
            'layer': self.layer,
            'compendium_entity': self.compendium_entity.to_dict() if self.compendium_entity else None,
            'entity_type': self.entity_type,
            'asset_id': self.asset_id,
            'visibility': self.visible,
            'rotation': self.rotation,
            'die_timer': self.die_timer,
            'asset_id': self.asset_id,
            'sheet_path': self.sheet_path,
            'frame_rects': self.frame_rects,
            'frame_duration': self.frame_duration,
            'current_frame': self.current_frame,
            'last_frame_time': self.last_frame_time,
            'sheet_texture': self.sheet_texture,
            'atlas_path': self.atlas_path,
            'is_player': self.is_player,
            'visible': self.visible
        }

    def get_current_frame_frect(self):
        return self.frame_frects[self.current_frame]

    def set_sheet_texture(self, texture):
        """Set the loaded sprite sheet texture."""
        self.sheet_texture = texture

   