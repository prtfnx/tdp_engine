"""
TileMapManager - Handles tile map data, placement, and storage
"""

import json
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import sdl3
import ctypes
from tools.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class PlacedTile:
    """Information about a placed tile on the map"""
    tileset_name: str
    tile_id: int
    map_x: int  # Grid position X
    map_y: int  # Grid position Y
    world_x: float = 0.0  # World coordinates (calculated)
    world_y: float = 0.0  # World coordinates (calculated)

@dataclass 
class TileMap:
    """Complete tile map data"""
    name: str
    grid_size: int = 32  # Size of each grid cell in pixels
    width: int = 100     # Map width in grid cells
    height: int = 100    # Map height in grid cells
    tiles: Dict[str, PlacedTile] = None  # key: "x,y" -> PlacedTile
    
    def __post_init__(self):
        if self.tiles is None:
            self.tiles = {}

class TileMapManager:
    """Manages tile maps - placement, removal, saving, loading"""
    
    def __init__(self, context, tile_manager):
        self.context = context
        self.tile_manager = tile_manager
        self.current_map: Optional[TileMap] = None
        self.grid_size = 32  # Default grid size
        
        # Create default map
        self.create_new_map("default_map")
    
    def create_new_map(self, name: str, width: int = 100, height: int = 100, grid_size: int = 32):
        """Create a new empty tile map"""
        self.current_map = TileMap(
            name=name,
            grid_size=grid_size,
            width=width,
            height=height,
            tiles={}
        )
        logger.info(f"Created new tile map: {name} ({width}x{height}, grid: {grid_size})")
    
    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to grid coordinates"""
        if not self.current_map:
            return 0, 0
        
        grid_x = int(world_x // self.current_map.grid_size)
        grid_y = int(world_y // self.current_map.grid_size)
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convert grid coordinates to world coordinates"""
        if not self.current_map:
            return 0.0, 0.0
        
        world_x = float(grid_x * self.current_map.grid_size)
        world_y = float(grid_y * self.current_map.grid_size)
        return world_x, world_y
    
    def place_tile(self, tileset_name: str, tile_id: int, world_x: float, world_y: float) -> bool:
        """Place a tile at world coordinates"""
        if not self.current_map:
            logger.error("No current map to place tile on")
            return False
        
        # Convert to grid coordinates
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        
        # Check bounds
        if grid_x < 0 or grid_x >= self.current_map.width or grid_y < 0 or grid_y >= self.current_map.height:
            logger.debug(f"Tile placement out of bounds: ({grid_x}, {grid_y})")
            return False
        
        # Verify tileset and tile exist
        if not self.tile_manager.get_tile_info(tileset_name, tile_id):
            logger.error(f"Invalid tile: {tileset_name}:{tile_id}")
            return False
        
        # Calculate world position for this grid cell
        tile_world_x, tile_world_y = self.grid_to_world(grid_x, grid_y)
        
        # Create placed tile
        placed_tile = PlacedTile(
            tileset_name=tileset_name,
            tile_id=tile_id,
            map_x=grid_x,
            map_y=grid_y,
            world_x=tile_world_x,
            world_y=tile_world_y
        )
        
        # Store in map
        key = f"{grid_x},{grid_y}"
        self.current_map.tiles[key] = placed_tile
        
        logger.debug(f"Placed tile {tileset_name}:{tile_id} at grid ({grid_x},{grid_y}) world ({tile_world_x},{tile_world_y})")
        return True
    
    def remove_tile(self, world_x: float, world_y: float) -> bool:
        """Remove tile at world coordinates"""
        if not self.current_map:
            return False
        
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        key = f"{grid_x},{grid_y}"
        
        if key in self.current_map.tiles:
            del self.current_map.tiles[key]
            logger.debug(f"Removed tile at grid ({grid_x},{grid_y})")
            return True
        
        return False
    
    def get_tile_at(self, world_x: float, world_y: float) -> Optional[PlacedTile]:
        """Get tile at world coordinates"""
        if not self.current_map:
            return None
        
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        key = f"{grid_x},{grid_y}"
        return self.current_map.tiles.get(key)
    
    def get_tiles_in_area(self, world_x: float, world_y: float, width: float, height: float) -> List[PlacedTile]:
        """Get all tiles in a rectangular world area"""
        if not self.current_map:
            return []
        
        tiles = []
        
        # Convert area to grid bounds
        start_grid_x, start_grid_y = self.world_to_grid(world_x, world_y)
        end_grid_x, end_grid_y = self.world_to_grid(world_x + width, world_y + height)
        
        # Search in grid area
        for grid_x in range(start_grid_x, end_grid_x + 1):
            for grid_y in range(start_grid_y, end_grid_y + 1):
                key = f"{grid_x},{grid_y}"
                if key in self.current_map.tiles:
                    tiles.append(self.current_map.tiles[key])
        
        return tiles
    
    def render_tiles(self, viewport_x: float, viewport_y: float, viewport_width: float, viewport_height: float, table_scale: float = 1.0):
        """Render all tiles visible in the current viewport"""
        if not self.current_map:
            return
        
        # Get tiles in viewport area
        tiles_to_render = self.get_tiles_in_area(viewport_x, viewport_y, viewport_width, viewport_height)
        
        for tile in tiles_to_render:
            # Calculate screen position
            screen_x = (tile.world_x - viewport_x) * table_scale
            screen_y = (tile.world_y - viewport_y) * table_scale
            screen_size = self.current_map.grid_size * table_scale
            
            # Create destination rectangle
            dest_rect = sdl3.SDL_FRect()
            dest_rect.x = screen_x
            dest_rect.y = screen_y
            dest_rect.w = screen_size
            dest_rect.h = screen_size
            
            # Render the tile
            self.tile_manager.render_tile(tile.tileset_name, tile.tile_id, dest_rect)
    
    def save_map(self, filepath: str) -> bool:
        """Save current map to JSON file"""
        if not self.current_map:
            logger.error("No current map to save")
            return False
        
        try:
            # Convert map to serializable format
            map_data = {
                "name": self.current_map.name,
                "grid_size": self.current_map.grid_size,
                "width": self.current_map.width,
                "height": self.current_map.height,
                "tiles": {key: asdict(tile) for key, tile in self.current_map.tiles.items()}
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(map_data, f, indent=2)
            
            logger.info(f"Saved tile map to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving tile map: {e}")
            return False
    
    def load_map(self, filepath: str) -> bool:
        """Load map from JSON file"""
        try:
            with open(filepath, 'r') as f:
                map_data = json.load(f)
            
            # Create new map from data
            self.current_map = TileMap(
                name=map_data["name"],
                grid_size=map_data["grid_size"],
                width=map_data["width"],
                height=map_data["height"],
                tiles={}
            )
            
            # Load tiles
            for key, tile_data in map_data["tiles"].items():
                placed_tile = PlacedTile(**tile_data)
                self.current_map.tiles[key] = placed_tile
            
            logger.info(f"Loaded tile map from: {filepath} ({len(self.current_map.tiles)} tiles)")
            return True
            
        except Exception as e:
            logger.error(f"Error loading tile map: {e}")
            return False
    
    def clear_map(self):
        """Clear all tiles from current map"""
        if self.current_map:
            self.current_map.tiles.clear()
            logger.info("Cleared all tiles from current map")
    
    def get_map_info(self) -> Optional[Dict]:
        """Get current map information"""
        if not self.current_map:
            return None
        
        return {
            "name": self.current_map.name,
            "grid_size": self.current_map.grid_size,
            "width": self.current_map.width,
            "height": self.current_map.height,
            "tile_count": len(self.current_map.tiles)
        }
