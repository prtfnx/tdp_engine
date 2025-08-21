import sdl3
import ctypes
from core.Player import ACCELERATION_COEF
from tools.logger import setup_logger
import numpy as np

logger = setup_logger(__name__)

TIME_TO_DIE = 2000
ACCELERATION_FRICTION = 0.999
SPEED_FRICTION = 0.995
class MovementManager:
    # Define which layers can collide with which
    COLLISION_MATRIX = {
        'projectiles': ['tokens', 'obstacles'],
        'tokens': ['tokens', 'obstacles'],
    }

    def __init__(self, context_table, player):
        self.table = context_table
        self.layers = list(context_table.dict_of_sprites_list.keys())
        self.player = player

    def move_and_collide(self, delta_time):
        # Debug: print all sprite frect values before collision check
        # print('--- Sprite frect values before collision check ---')
        # for layer, sprite_list in self.table.dict_of_sprites_list.items():
        #     for sprite in sprite_list:
        #         print(f'Layer: {layer}, Sprite: {sprite}, frect: x={sprite.frect.x}, y={sprite.frect.y}, w={sprite.frect.w}, h={sprite.frect.h}, collidable={sprite.collidable}')
        # Player management        
        speed_friction = SPEED_FRICTION # TODO: implement friction
        acceleration_friction = ACCELERATION_FRICTION
        self.player.physics_step(delta_time, acceleration_friction, speed_friction)
        # Move all sprites
        for layer, sprite_list in self.table.dict_of_sprites_list.items():
            for sprite in sprite_list:
                if sprite.moving:
                    sprite.move(delta_time)
                # Only update die timer here
                if sprite.die_timer is not None:
                    sprite.die_timer -= delta_time
                    if sprite.die_timer <= 0:
                        sprite.die()
                        self.table.dict_of_sprites_list[sprite.layer].remove(sprite)
                   
        
        # Batch collision for each relevant layer pair
        for layer_a, targets in self.COLLISION_MATRIX.items():            
            sprites_a = [s for s in self.table.dict_of_sprites_list.get(layer_a, []) if getattr(s, 'collidable', True)]
            rects_a = np.array([[s.frect.x, s.frect.y, s.frect.w, s.frect.h] for s in sprites_a], dtype=np.float32)
            for layer_b in targets:
                sprites_b = [s for s in self.table.dict_of_sprites_list.get(layer_b, []) if getattr(s, 'collidable', True)]
                rects_b = np.array([[s.frect.x, s.frect.y, s.frect.w, s.frect.h] for s in sprites_b], dtype=np.float32)
                if rects_a.size == 0 or rects_b.size == 0:
                    continue
                # Batch AABB collision
                a_min = rects_a[:, :2][:, None, :]
                a_max = (rects_a[:, :2] + rects_a[:, 2:])[:, None, :]
                b_min = rects_b[:, :2]
                b_max = rects_b[:, :2] + rects_b[:, 2:]
                collide = (a_max[...,0] > b_min[:,0]) & (b_max[:,0] > a_min[...,0]) & (a_max[...,1] > b_min[:,1]) & (b_max[...,1] > a_min[...,1])
                # Handle collisions
                idx_a, idx_b = np.where(collide)
                for i, j in zip(idx_a, idx_b):
                    sa = sprites_a[i]
                    sb = sprites_b[j]
                    if sa is sb:
                        continue
                    if sa is self.table.player or sb is self.table.player:
                        print(f"Collision between player and sprite: {sa.sprite_id} <-> {sb.sprite_id}")
                    sa.set_speed(sa.dx*(-0.3), sa.dy*(-0.3))
                    #sa.collidable = False
        #player collide check (use table coordinates)
        player = self.table.player
        all_collidable_sprites = [
            s for layer_sprites in self.table.dict_of_sprites_list.values()
            for s in layer_sprites if getattr(s, 'collidable', True) and getattr(s, 'is_player', False) is not True
        ]
        collidable_rects = np.array([
            [
                s.coord_x.value if hasattr(s.coord_x, 'value') else float(s.coord_x),
                s.coord_y.value if hasattr(s.coord_y, 'value') else float(s.coord_y),
                s.original_w * s.scale_x,
                s.original_h * s.scale_y
            ]
            for s in all_collidable_sprites
        ], dtype=np.float32)
        player_rect = np.array([
            [
                player.coord_x.value if hasattr(player.coord_x, 'value') else float(player.coord_x),
                player.coord_y.value if hasattr(player.coord_y, 'value') else float(player.coord_y),
                player.sprite.original_w * player.sprite.scale_x,
                player.sprite.original_h * player.sprite.scale_y
            ]
        ], dtype=np.float32)
        p_min = player_rect[:, :2]
        p_max = player_rect[:, :2] + player_rect[:, 2:]
        s_min = collidable_rects[:, :2]
        s_max = collidable_rects[:, :2] + collidable_rects[:, 2:]

        collide = (p_max[0,0] > s_min[:,0]) & (s_max[:,0] > p_min[0,0]) & (p_max[0,1] > s_min[:,1]) & (s_max[:,1] > p_min[0,1])
        colliding_indices = np.where(collide)[0]
        for idx in colliding_indices:
            sprite = all_collidable_sprites[idx]
            logger.debug(f"Collision between player and sprite: {self.player.sprite.sprite_id} <-> {sprite.sprite_id}")
            player.speed_x*=-1
            player.speed_y*=-1
            player.acceleration_x*=-0.3
            player.acceleration_y*=-0.3
            player.update_position(delta_time)

        # Now update frect for rendering (screen coordinates)
        for layer, sprite_list in self.table.dict_of_sprites_list.items():
            for sprite in sprite_list:
                if hasattr(self.table, 'table_to_screen'):
                    screen_x, screen_y = self.table.table_to_screen(sprite.coord_x.value, sprite.coord_y.value)
                    sprite.frect.x = ctypes.c_float(screen_x)
                    sprite.frect.y = ctypes.c_float(screen_y)
                    sprite.frect.w = ctypes.c_float(sprite.original_w * sprite.scale_x * self.table.table_scale)
                    sprite.frect.h = ctypes.c_float(sprite.original_h * sprite.scale_y * self.table.table_scale)
        
def sync_sprite_move(context, sprite, old_pos, new_pos):
    """Handle sprite movement with network sync"""
    if not hasattr(context, 'protocol') or not context.protocol:
        return  # No network connection
        
    # Ensure sprite has an ID
    if not hasattr(sprite, 'sprite_id') or not sprite.sprite_id:
        sprite.sprite_id = str(__import__('uuid').uuid4())

    # Send sprite movement update with proper protocol format
    change = {
        'category': 'sprite',
        'type': 'sprite_move',
        'data': {
            'table_id': context.current_table.table_id,
            'table_name': context.current_table.name,
            'sprite_id': sprite.sprite_id,
            'from': {'x': old_pos[0], 'y': old_pos[1]},
            'to': {'x': new_pos[0], 'y': new_pos[1]},                
            'timestamp': __import__('time').time()
        }
    }
    
    # Send via protocol using SPRITE_UPDATE message type
    
    msg = Message(MessageType.SPRITE_UPDATE, change, 
                getattr(context.protocol, 'client_id', 'unknown'))
    

    try:
        # Send the message 
        context.protocol.send(msg.to_json())
        logger.debug(f"Sent sprite move: {sprite.sprite_id} to ({new_pos[0]:.1f}, {new_pos[1]:.1f})")

    except Exception as e:
        logger.error(f"Failed to send sprite movement: {e}")

def sync_sprite_scale(context, sprite, old_scale, new_scale):
    """Handle sprite scaling with network sync"""
    if not hasattr(context, 'protocol') or not context.protocol:
        return
          # Ensure sprite has an ID
    if not hasattr(sprite, 'sprite_id') or not sprite.sprite_id:
        sprite.sprite_id = str(__import__('uuid').uuid4())
        
    change = {
        'category': 'sprite',
        'type': 'sprite_scale',
        'data': {
            'table_id': context.current_table.table_id,
            'table_name': context.current_table.name,
            'sprite_id': sprite.sprite_id,
            'from': {'x': old_scale[0], 'y': old_scale[1]},
            'to': {'x': new_scale[0], 'y': new_scale[1]},               
            'timestamp': __import__('time').time()
        }
    }
    
    
    msg = Message(MessageType.TABLE_UPDATE, change,
                 getattr(context.protocol, 'client_id', 'unknown'))
    
    try:
        if hasattr(context.protocol, 'send'):
            context.protocol.send(msg.to_json())
        elif hasattr(context.protocol, 'send_message'):
            context.protocol.send_message(msg)
            logger.info(f"Sent sprite scale: {sprite.sprite_id} to ({new_scale[0]:.2f}, {new_scale[1]:.2f})")
        
    except Exception as e:
        logger.error(f"Failed to send sprite scaling: {e}")

def sync_sprite_rotation(context, sprite, old_rotation, new_rotation):
    """Handle sprite rotation with network sync"""
    if not hasattr(context, 'protocol') or not context.protocol:
        return
        
    # Ensure sprite has an ID
    if not hasattr(sprite, 'sprite_id') or not sprite.sprite_id:
        sprite.sprite_id = str(__import__('uuid').uuid4())
        
    change = {
        'category': 'sprite',
        'type': 'sprite_rotate',
        'data': {
            'table_id': context.current_table.table_id,
            'table_name': context.current_table.name,
            'sprite_id': sprite.sprite_id,
            'from': old_rotation,
            'to': new_rotation,
            'timestamp': __import__('time').time()
        }
    }
    
    msg = Message(MessageType.SPRITE_UPDATE, change,
                 getattr(context.protocol, 'client_id', 'unknown'))
    
    try:
        if hasattr(context.protocol, 'send'):
            context.protocol.send(msg.to_json())
        elif hasattr(context.protocol, 'send_message'):
            context.protocol.send_message(msg)
        logger.debug(f"Sent sprite rotation: {sprite.sprite_id} to {new_rotation:.1f} degrees")
        
    except Exception as e:
        logger.error(f"Failed to send sprite rotation: {e}")

def check_collision_with_all_sprites(table, sprite):
    """Check collision of a sprite with all other collidable sprites in the table."""
    #TODO: make anothet function for checking collision in the same layer
    for layers in table.dict_of_sprites_list.values():
        for other_sprite in layers:
            if other_sprite != sprite and other_sprite != table.selected_sprite and other_sprite.collidable:
                if sdl3.SDL_HasRectIntersectionFloat(ctypes.byref(sprite.frect), ctypes.byref(other_sprite.frect)):
                    logger.info(
                        f"Collision detected: sprite={sprite}, other_sprite={other_sprite}, table={table}"
                    )
                    logger.debug(
                        f"sprite.frect {sprite.frect.x} {sprite.frect.y} {sprite.frect.w} {sprite.frect.h}"
                    )
                    logger.debug(
                        f"other_sprite.frect {other_sprite.frect.x} {other_sprite.frect.y} {other_sprite.frect.w} {other_sprite.frect.h}"
                    )
                    return True
    return False


def move_sprites(cnt, delta_time):
    """Move all sprites, handle collisions and dying sprites."""
    width = cnt.window_width
    height = cnt.window_height   
    # Player managment
    speed_friction = SPEED_FRICTION # TODO: implement friction
    acceleration_friction = ACCELERATION_FRICTION
    cnt.player.physics_step(delta_time, acceleration_friction, speed_friction)
    for layer, sprite_list in cnt.current_table.dict_of_sprites_list.items():
        for sprite in sprite_list:
            # Movement
            if sprite.moving:
                sprite.move(delta_time)
                if sprite.coord_x.value > width.value:
                    sprite.coord_x.value = 0
                if sprite.coord_y.value > height.value:
                    sprite.coord_y.value = 0
                if sprite.coord_x.value < 0:
                    sprite.coord_x.value = width.value
                if sprite.coord_y.value < 0:
                    sprite.coord_y.value = height.value
                if sprite.collidable:
                    if check_collision_with_all_sprites(cnt.current_table, sprite):
                        logger.info("Collision occurred, changing sprite texture and stopping movement.")
                        sprite.set_texture(b'resources/fire_explosion.png')
                        sprite.moving = False
                        sprite.collidable = False
                        sprite.set_die_timer(TIME_TO_DIE)
            # Handle dying sprites
            if sprite.die_timer is not None:
                sprite.die_timer -= delta_time
                if sprite.die_timer <= 0:
                    sprite.die()
                    cnt.current_table.dict_of_sprites_list[sprite.layer].remove(sprite)
            
            # Convert sprite's table coordinates to screen coordinates for rendering
            if hasattr(cnt.current_table, 'table_to_screen'):
                # Use new coordinate system
                screen_x, screen_y = cnt.current_table.table_to_screen(sprite.coord_x.value, sprite.coord_y.value)
                sprite.frect.x = ctypes.c_float(screen_x)
                sprite.frect.y = ctypes.c_float(screen_y)                
                # Scale sprites based on table scale
                sprite.frect.w = ctypes.c_float(sprite.original_w * sprite.scale_x * cnt.current_table.table_scale)
                sprite.frect.h = ctypes.c_float(sprite.original_h * sprite.scale_y * cnt.current_table.table_scale)
            
            cnt.step.value = max(float(sprite.frect.w), float(sprite.frect.h))

