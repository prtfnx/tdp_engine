import sdl3
import time
import ctypes
import math
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

    def get_transformed_aabb(self, sprite):
        """
        Calculate the transformed AABB for a sprite, accounting for scale only (rotation ignored for collision).
        """
        # Get top-left and bottom-right corners (no rotation)
        x = sprite.coord_x.value
        y = sprite.coord_y.value
        w = sprite.original_w * sprite.scale_x
        h = sprite.original_h * sprite.scale_y
        min_x = x
        min_y = y
        max_x = x + w
        max_y = y + h
        if self.context.debug_mode or self.context.is_gm:
            self.context.RenderManager.aabb_rectangles.append((min_x, min_y, max_x, max_y))
        return min_x, min_y, max_x, max_y

    def move_and_collide(self, delta_time, table):
        # Debug: print all sprite frect values before collision check
        # print('--- Sprite frect values before collision check ---')
        # for layer, sprite_list in self.table.dict_of_sprites_list.items():
        #     for sprite in sprite_list:
        #         print(f'Layer: {layer}, Sprite: {sprite}, frect: x={sprite.frect.x}, y={sprite.frect.y}, w={sprite.frect.w}, h={sprite.frect.h}, collidable={sprite.collidable}')
        #start = time.time()
        # Player management
        self.table=table
        self.player = table.player
        player_last_coord = [self.player.coord_x.value, self.player.coord_y.value]
        speed_friction = SPEED_FRICTION # TODO: implement friction
        acceleration_friction = ACCELERATION_FRICTION
        self.player.physics_step(delta_time, acceleration_friction, speed_friction)
        #print(f'player name: {self.player.name} speed {self.player.speed_x}, {self.player.speed_y}, acceleration {self.player.acceleration_x}, {self.player.acceleration_y}')
        # Move all sprites
        for layer, sprite_list in self.table.dict_of_sprites_list.items():
            for sprite in sprite_list:
                if sprite.moving:
                    sprite.move(delta_time)
                # Only update die timer here
                if sprite.die_timer is not None:
                    sprite.die_timer -= delta_time
                    if sprite.die_timer <= 0:
                        #sprite.die() # no need - textures cached
                        self.table.dict_of_sprites_list[sprite.layer].remove(sprite)
        # Efficient batch collision checking (all sprites except player)
        for layer_a, targets in self.COLLISION_MATRIX.items():
            sprites_a = [s for s in self.table.dict_of_sprites_list.get(layer_a, []) if getattr(s, 'collidable', True)]
            for layer_b in targets:
                sprites_b = [s for s in self.table.dict_of_sprites_list.get(layer_b, []) if getattr(s, 'collidable', True)]
                if not sprites_a or not sprites_b:
                    continue
                # Build transformed AABBs for all sprites
                a_aabbs = np.array([self.get_transformed_aabb(s) for s in sprites_a])  # (N, 4)
                b_aabbs = np.array([self.get_transformed_aabb(s) for s in sprites_b])  # (M, 4)
                a_min_x = a_aabbs[:, 0][:, None]
                a_max_x = a_aabbs[:, 2][:, None]
                a_min_y = a_aabbs[:, 1][:, None]
                a_max_y = a_aabbs[:, 3][:, None]
                b_min_x = b_aabbs[:, 0]
                b_max_x = b_aabbs[:, 2]
                b_min_y = b_aabbs[:, 1]
                b_max_y = b_aabbs[:, 3]
                # Check for overlap on both axes
                collide_x = (a_max_x > b_min_x) & (b_max_x > a_min_x)
                collide_y = (a_max_y > b_min_y) & (b_max_y > a_min_y)
                collide = collide_x & collide_y
                idx_a, idx_b = np.where(collide)
                for i, j in zip(idx_a, idx_b):
                    sa = sprites_a[i]
                    sb = sprites_b[j]
                    if sa is sb:
                        continue  # Skip self-collision
                    # Compute overlap on both axes
                    overlap_x = min(a_max_x[i, 0], b_max_x[j]) - max(a_min_x[i, 0], b_min_x[j])
                    overlap_y = min(a_max_y[i, 0], b_max_y[j]) - max(a_min_y[i, 0], b_min_y[j])
                    # Clamp on axis with smallest overlap
                    if overlap_x < overlap_y:
                        # Clamp X
                        if a_min_x[i, 0] < b_min_x[j]:
                            sa.coord_x.value = b_min_x[j] - (a_max_x[i, 0] - a_min_x[i, 0])
                            logger.debug(f"Clamped {sa.sprite_id} to left of {sb.sprite_id}")
                            sa.dx *= -0.5
                        else:
                            sa.coord_x.value = b_max_x[j]
                            logger.debug(f"Clamped {sa.sprite_id} to right of {sb.sprite_id}")
                            sa.dx *= -0.5
                    else:
                        # Clamp Y
                        if a_min_y[i, 0] < b_min_y[j]:
                            sa.coord_y.value = b_min_y[j] - (a_max_y[i, 0] - a_min_y[i, 0])
                            logger.debug(f"Clamped {sa.sprite_id} above {sb.sprite_id}")
                            sa.dy *= -0.5
                        else:
                            sa.coord_y.value = b_max_y[j]
                            logger.debug(f"Clamped {sa.sprite_id} below {sb.sprite_id}")
                            sa.dy *= -0.5
        
        # Efficient player collision check (against all obstacles)
        player = self.table.player
        all_collidable_sprites = [
            s for layer_sprites in self.table.dict_of_sprites_list.values()
            for s in layer_sprites if getattr(s, 'collidable', True) and getattr(s, 'is_player', False) is not True
        ]
        if all_collidable_sprites:
            p_min_x, p_min_y, p_max_x, p_max_y = self.get_transformed_aabb(player.sprite)
            p_aabb = np.array([[p_min_x, p_min_y, p_max_x, p_max_y]])
            s_aabbs = np.array([self.get_transformed_aabb(s) for s in all_collidable_sprites])
            # Unpack for broadcasting
            p_min_x = p_aabb[:, 0][:, None]
            p_max_x = p_aabb[:, 2][:, None]
            p_min_y = p_aabb[:, 1][:, None]
            p_max_y = p_aabb[:, 3][:, None]
            s_min_x = s_aabbs[:, 0]
            s_max_x = s_aabbs[:, 2]
            s_min_y = s_aabbs[:, 1]
            s_max_y = s_aabbs[:, 3]
            # Check for overlap on both axes
            collide_x = (p_max_x > s_min_x) & (s_max_x > p_min_x)
            collide_y = (p_max_y > s_min_y) & (s_max_y > p_min_y)
            collide = collide_x & collide_y
            idx_p, idx_s = np.where(collide)
            for i, j in zip(idx_p, idx_s):
                sprite = all_collidable_sprites[j]
                # Compute overlap
                overlap_x = min(p_max_x[0, 0], s_max_x[j]) - max(p_min_x[0, 0], s_min_x[j])
                overlap_y = min(p_max_y[0, 0], s_max_y[j]) - max(p_min_y[0, 0], s_min_y[j])
                # Clamp on axis with smallest overlap
                if overlap_x < overlap_y:
                    # Clamp X
                    if p_min_x[0, 0] < s_min_x[j]:
                        player.coord_x.value = s_min_x[j] - (p_max_x[0, 0] - p_min_x[0, 0])
                        logger.debug(f"Player clamped to left of obstacle {sprite.sprite_id}")
                        player.speed_x *= -0.5
                    else:
                        player.coord_x.value = s_max_x[j]
                        logger.debug(f"Player clamped to right of obstacle {sprite.sprite_id}")
                        player.speed_x *= -0.5
                else:
                    # Clamp Y
                    if p_min_y[0, 0] < s_min_y[j]:
                        player.coord_y.value = s_min_y[j] - (p_max_y[0, 0] - p_min_y[0, 0])
                        logger.debug(f"Player clamped above obstacle {sprite.sprite_id}")
                        player.speed_y *= -0.5
                    else:
                        player.coord_y.value = s_max_y[j]
                        logger.debug(f"Player clamped below obstacle {sprite.sprite_id}")
                        player.speed_y *= -0.5

        # Now update frect for rendering (screen coordinates)
        for layer, sprite_list in self.table.dict_of_sprites_list.items():
            for sprite in sprite_list:
                if hasattr(self.table, 'table_to_screen'):
                    screen_x, screen_y = self.table.table_to_screen(sprite.coord_x.value, sprite.coord_y.value)
                    sprite.frect.x = ctypes.c_float(screen_x)
                    sprite.frect.y = ctypes.c_float(screen_y)
                    sprite.frect.w = ctypes.c_float(sprite.original_w * sprite.scale_x * self.table.table_scale)
                    sprite.frect.h = ctypes.c_float(sprite.original_h * sprite.scale_y * self.table.table_scale)
        # measure time print(f'time for collision check: {time.time() - start:.6f} seconds')
