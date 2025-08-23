"""
TileManager - Manages tilesets and tile data for the 2D tile-based map system
"""

import os
import json
import sdl3
import ctypes
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from tools.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class TilesetInfo:
    """Information about a tileset"""
    name: str
    path: str
    tile_width: int = 32
    tile_height: int = 32
    tiles_per_row: int = 10
    total_tiles: int = 0
    texture: Optional[Any] = None  # SDL_Texture
        im_texture_ref: Optional[Any] = None  # ImGui ImTextureRef

@dataclass
class TileInfo:
    """Information about a single tile"""
    tileset_name: str
    tile_id: int
    source_rect: sdl3.SDL_Rect
    name: str = ""

class TileManager:
    """Manages tilesets and provides tile information for map creation"""
    
    def __init__(self, context):
        self.context = context
        self.renderer = context.renderer
        
        # Tileset storage
        self.tilesets: Dict[str, TilesetInfo] = {}
        self.tiles: Dict[str, List[TileInfo]] = {}  # tileset_name -> list of tiles
        
        # Default tile size
        self.default_tile_size = (32, 32)
        
        # Load tilesets from resources
        self._discover_tilesets()
    
    def _discover_tilesets(self):
        """Discover and load tilesets from the resources/tilesets directory"""
        tilesets_path = os.path.join("resources", "tilesets")
        
        if not os.path.exists(tilesets_path):
            logger.warning(f"Tilesets directory not found: {tilesets_path}")
            return
        
        # Scan for tileset directories and files
        for root, dirs, files in os.walk(tilesets_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, tilesets_path)
                    
                    # Create tileset name from path
                    tileset_name = os.path.splitext(relative_path.replace(os.sep, '_'))[0]
                    
                    self._load_tileset(tileset_name, full_path)
    
    def _load_tileset(self, name: str, path: str, tile_width: int = 32, tile_height: int = 32, tiles_per_row: int = 10):
        """Load a tileset from file"""
        try:
            # Load texture directly using SDL3
            texture = None
            
            # Use IMG_Load for loading various image formats (PNG, JPG, etc.)
            surface = sdl3.IMG_Load(path.encode())
            if surface:
                texture = sdl3.SDL_CreateTextureFromSurface(self.renderer, surface)
                sdl3.SDL_DestroySurface(surface)
            
            if not texture:
                logger.error(f"Failed to load tileset texture: {path}")
                return
            
            # Get texture dimensions using SDL3 GetTextureSize
            w_ptr = ctypes.c_float()
            h_ptr = ctypes.c_float()
            
            if not sdl3.SDL_GetTextureSize(texture, ctypes.byref(w_ptr), ctypes.byref(h_ptr)):
                logger.error(f"Failed to query texture dimensions for: {path}")
                sdl3.SDL_DestroyTexture(texture)
                return
            
            texture_width = int(w_ptr.value)
            texture_height = int(h_ptr.value)
            
            # Calculate tile layout
            actual_tiles_per_row = texture_width // tile_width
            rows = texture_height // tile_height
            total_tiles = actual_tiles_per_row * rows
            
            # Create tileset info
            tileset_info = TilesetInfo(
                name=name,
                path=path,
                tile_width=tile_width,
                tile_height=tile_height,
                tiles_per_row=actual_tiles_per_row,
                total_tiles=total_tiles,
                texture=texture
            )
            
            self.tilesets[name] = tileset_info
            
            # Generate tile info for each tile in the tileset
            tiles = []
            for row in range(rows):
                for col in range(actual_tiles_per_row):
                    from imgui_bundle import imgui
                    im_texture_ref = imgui.register_texture(texture)
                    tile_id = row * actual_tiles_per_row + col
                    
                    source_rect = sdl3.SDL_Rect()
                    source_rect.x = col * tile_width
                    source_rect.y = row * tile_height
                    source_rect.w = tile_width
                    source_rect.h = tile_height
                    
                    tile_info = TileInfo(
                        tileset_name=name,
                        im_texture_ref=im_texture_ref
                        tile_id=tile_id,
                        source_rect=source_rect,
                        name=f"{name}_tile_{tile_id}"
                    )
                    tiles.append(tile_info)
            
            self.tiles[name] = tiles
            logger.info(f"Loaded tileset '{name}' with {total_tiles} tiles ({actual_tiles_per_row}x{rows})")
            
        except Exception as e:
            logger.error(f"Error loading tileset {name} from {path}: {e}")
    
    def get_tileset_names(self) -> List[str]:
        """Get list of available tileset names"""
        return list(self.tilesets.keys())
    
    def get_tileset_info(self, name: str) -> Optional[TilesetInfo]:
        """Get tileset information by name"""
        return self.tilesets.get(name)
    
    def get_tiles(self, tileset_name: str) -> List[TileInfo]:
        """Get all tiles from a tileset"""
        return self.tiles.get(tileset_name, [])
    
    def get_tile_info(self, tileset_name: str, tile_id: int) -> Optional[TileInfo]:
        """Get specific tile information"""
        tiles = self.tiles.get(tileset_name, [])
        for tile in tiles:
            if tile.tile_id == tile_id:
                return tile
        return None
    
    def render_tile(self, tileset_name: str, tile_id: int, dest_rect: sdl3.SDL_FRect):
        """Render a specific tile to the given destination rectangle"""
        tileset = self.tilesets.get(tileset_name)
        if not tileset or not tileset.texture:
            return False
        
        tile_info = self.get_tile_info(tileset_name, tile_id)
        if not tile_info:
            return False
        
        # Convert SDL_Rect to SDL_FRect for source
        src_frect = sdl3.SDL_FRect()
        src_frect.x = float(tile_info.source_rect.x)
        src_frect.y = float(tile_info.source_rect.y)
        src_frect.w = float(tile_info.source_rect.w)
        src_frect.h = float(tile_info.source_rect.h)
        
        result = sdl3.SDL_RenderTexture(self.renderer, tileset.texture, 
                                      ctypes.byref(src_frect), ctypes.byref(dest_rect))
        return result == 0
    
    def cleanup(self):
        """Clean up resources"""
        for tileset in self.tilesets.values():
            if tileset.texture:
                sdl3.SDL_DestroyTexture(tileset.texture)
        self.tilesets.clear()
        self.tiles.clear()
