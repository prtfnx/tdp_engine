"""
TileManager - Manages tilesets and tile data for the 2D tile-based map system
"""

import os
import json
import sdl3
import ctypes
from typing import Dict, List, Tuple, Optional, Any
from OpenGL.GL import (
    glGenTextures, glBindTexture, glTexImage2D, glTexParameteri, glPixelStorei, glGetError,
    GL_TEXTURE_2D, GL_RGBA, GL_UNSIGNED_BYTE, GL_LINEAR, glDeleteTextures,
    GL_UNPACK_ALIGNMENT, GL_UNPACK_ROW_LENGTH, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER
)
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
    gl_texture_id: Optional[int] = None  # OpenGL texture ID


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
            # Load image as SDL_Surface using pysdl3
            surface = sdl3.IMG_Load(ctypes.c_char_p(path.encode()))
            if not surface:
                logger.error(f"Failed to load tileset surface: {path}")
                return

            # Create SDL_Texture for map rendering
            texture = sdl3.SDL_CreateTextureFromSurface(self.renderer, surface)
            if not texture:
                logger.error(f"Failed to create SDL_Texture from surface: {path}")
                sdl3.SDL_DestroySurface(surface)
                return

            # --- OpenGL texture creation for ImGui panel preview ---

            surf = surface[0]
            width = surf.w
            height = surf.h
            pitch = surf.pitch
            try:
                pixel_data = ctypes.string_at(surf.pixels, pitch * height)
            except Exception as e:
                logger.error(f"Tileset '{name}': Failed to convert surface pixels to buffer: {e}. Aborting tileset loading.")
                sdl3.SDL_DestroySurface(surface)
                sdl3.SDL_DestroyTexture(texture)
                return
            # Use SDL3/pysdl3 API to get BytesPerPixel safely
            try:
                # surface.format is an integer pixel format enum
                bpp = sdl3.SDL_BYTESPERPIXEL(surf.format)
                print(f'DEBUG: BytesPerPixel value from SDL_BYTESPERPIXEL: {bpp}')
                if bpp <= 0 or bpp > 8:
                    logger.error(f"Tileset '{name}': BytesPerPixel value is invalid ({bpp}). Aborting tileset loading.")
                    sdl3.SDL_DestroySurface(surface)
                    sdl3.SDL_DestroyTexture(texture)
                    return
            except Exception as e:
                logger.error(f"Tileset '{name}': Exception accessing BytesPerPixel via SDL3 API: {e}. Aborting tileset loading.")
                sdl3.SDL_DestroySurface(surface)
                sdl3.SDL_DestroyTexture(texture)
                return
            # Determine alignment (largest power of 2 divisor of pitch, up to 8)
            alignment = 8
            while pitch % alignment != 0 and alignment > 1:
                alignment //= 2
            glPixelStorei(GL_UNPACK_ALIGNMENT, alignment)

            # Set row length if needed
            expected_pitch = width * bpp
            if pitch != expected_pitch:
                glPixelStorei(GL_UNPACK_ROW_LENGTH, pitch // bpp)
            else:
                glPixelStorei(GL_UNPACK_ROW_LENGTH, 0)

            # Choose format (assume RGBA)
            pixel_format = GL_RGBA
            internal_format = GL_RGBA
            pixel_type = GL_UNSIGNED_BYTE

            # Generate OpenGL texture
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, internal_format, width, height, 0, pixel_format, pixel_type, pixel_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            # Reset pixel store
            glPixelStorei(GL_UNPACK_ALIGNMENT, 4)
            glPixelStorei(GL_UNPACK_ROW_LENGTH, 0)

            # Destroy SDL_Surface (no longer needed)
            sdl3.SDL_DestroySurface(surface)

            # Calculate tile layout
            actual_tiles_per_row = width // tile_width
            rows = height // tile_height
            total_tiles = actual_tiles_per_row * rows

            # Create tileset info
            tileset_info = TilesetInfo(
                name=name,
                path=path,
                tile_width=tile_width,
                tile_height=tile_height,
                tiles_per_row=actual_tiles_per_row,
                total_tiles=total_tiles,
                texture=texture,           # SDL_Texture for map rendering
                gl_texture_id=texture_id   # OpenGL texture for ImGui panel
            )
            self.tilesets[name] = tileset_info

            # Generate tile info for each tile in the tileset
            tiles = []
            for row in range(rows):
                for col in range(actual_tiles_per_row):
                    tile_id = row * actual_tiles_per_row + col
                    source_rect = sdl3.SDL_Rect()
                    source_rect.x = col * tile_width
                    source_rect.y = row * tile_height
                    source_rect.w = tile_width
                    source_rect.h = tile_height
                    tile_info = TileInfo(
                        tileset_name=name,
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
            if tileset.gl_texture_id:
                glDeleteTextures(1, [tileset.gl_texture_id])
            if tileset.texture:
                sdl3.SDL_DestroyTexture(tileset.texture)
        self.tilesets.clear()
        self.tiles.clear()
