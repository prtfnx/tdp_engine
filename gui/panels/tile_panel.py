"""
Tile Panel - GUI panel for tile-based map editing
"""

from imgui_bundle import imgui
import os
from typing import Optional, List
from tools.logger import setup_logger

logger = setup_logger(__name__)

class TilePanel:
    """GUI panel for tile-based map editing"""
    
    def __init__(self, context, actions_bridge):
        self.context = context
        self.actions_bridge = actions_bridge
        
        # Tile system components (will be initialized in initialize method)
        self.tile_manager = None
        self.tile_map_manager = None
        
        # UI State
        self.selected_tileset = ""
        self.selected_tile_id = -1
        self.tile_mode = "place"  # "place", "erase"
        self.show_grid = True
        self.grid_opacity = 0.5
        
        # Tile preview
        self.tiles_per_row = 8  # For tileset display
        self.tile_button_size = 32
        
        # Map settings
        self.new_map_name = "new_map"
        self.new_map_width = 100
        self.new_map_height = 100
        self.new_map_grid_size = 32
        
        # File management
        self.save_filename = "tilemap.json"
        self.maps_directory = "resources/maps"
        
        # Ensure maps directory exists
        os.makedirs(self.maps_directory, exist_ok=True)
    
    def initialize(self):
        """Initialize tile system components"""
        try:
            from core.TileManager import TileManager
            from core.TileMapManager import TileMapManager
            # Initialize TileManager
            try:
                logger.info("Initializing TileManager...")
                self.context.TileManager = TileManager(game_context)
            except Exception as e:
                logger.error(f"Failed to initialize TileManager: {e}")
            
            # Initialize TileMapManager
            try:
                logger.info("Initializing TileMapManager...")
                self.context.TileMapManager = TileMapManager(self.context, self.context.TileManager)
            except Exception as e:
                logger.error(f"Failed to initialize TileMapManager: {e}")
                self.context.TileMapManager = None
            self.tile_manager = self.context.TileManager
            self.tile_map_manager = self.context.TileMapManager
            
            # Set default tileset
            tilesets = self.tile_manager.get_tileset_names()
            if tilesets:
                self.selected_tileset = tilesets[0]
            
            logger.info("Tile system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize tile system: {e}")
            return False
    
    def render(self):
        """Render the tile panel content"""
        # Initialize if needed
        if not self.tile_manager or not self.tile_map_manager:
            if imgui.button("Initialize Tile System"):
                self.initialize()
            return
        
        # Only show tile tools to GM
        if not self.actions_bridge.is_gm_mode():
            imgui.text("Tile editing requires GM mode")
            return
        
        # === TILE MODE SELECTION ===
        imgui.text("Tile Mode:")
        if imgui.radio_button("Place", self.tile_mode == "place"):
            self.tile_mode = "place"
        imgui.same_line()
        if imgui.radio_button("Erase", self.tile_mode == "erase"):
            self.tile_mode = "erase"
        
        imgui.separator()
        
        # === TILESET SELECTION ===
        imgui.text("Tileset:")
        tilesets = self.tile_manager.get_tileset_names()
        
        if tilesets:
            # Tileset combo box
            current_index = 0
            if self.selected_tileset in tilesets:
                current_index = tilesets.index(self.selected_tileset)
            
            changed, new_index = imgui.combo("##tileset", current_index, tilesets)
            if changed:
                self.selected_tileset = tilesets[new_index]
                self.selected_tile_id = -1  # Reset tile selection
            
            # === TILE SELECTION ===
            if self.selected_tileset and self.tile_mode == "place":
                self._render_tile_selector()
        else:
            imgui.text("No tilesets found")
        
        imgui.separator()
        
        # === MAP CONTROLS ===
        self._render_map_controls()
        
        imgui.separator()
        
        # === GRID SETTINGS ===
        self._render_grid_settings()
        
        imgui.separator()
        
        # === FILE OPERATIONS ===
        self._render_file_operations()
        
        # === MAP INFO ===
        imgui.separator()
        self._render_map_info()
    
    def _render_tile_selector(self):
        """Render the tile selection grid with actual tile graphics"""
        if not self.selected_tileset:
            return
        
        tiles = self.tile_manager.get_tiles(self.selected_tileset)        
        if not tiles:
            imgui.text("No tiles in selected tileset")
            return
        
        # Get tileset info for texture access
        tileset_info = self.tile_manager.get_tileset_info(self.selected_tileset)
        if not tileset_info or not tileset_info.gl_texture_id:
            imgui.text("Tileset texture not available")
            return
        
        imgui.text(f"Tiles ({len(tiles)}):")
        
        # Calculate layout
        available_width = imgui.get_content_region_avail().x
        button_size_with_spacing = self.tile_button_size + 4  # 4 for spacing
        tiles_per_row = max(1, int(available_width / button_size_with_spacing))
        
        # Get texture dimensions for UV calculation
        texture_width = tileset_info.tiles_per_row * tileset_info.tile_width
        texture_height = (tileset_info.total_tiles // tileset_info.tiles_per_row) * tileset_info.tile_height
        if tileset_info.total_tiles % tileset_info.tiles_per_row > 0:
            texture_height += tileset_info.tile_height
        
        # Render tiles in grid
        for i, tile in enumerate(tiles):
            if i > 0 and i % tiles_per_row != 0:
                imgui.same_line()
            
            # Create button ID
            button_id = f"##tile_{tile.tile_id}"
            
            # Calculate UV coordinates for this tile
            uv0_x = tile.source_rect.x / texture_width
            uv0_y = tile.source_rect.y / texture_height
            uv1_x = (tile.source_rect.x + tile.source_rect.w) / texture_width
            uv1_y = (tile.source_rect.y + tile.source_rect.h) / texture_height
            
            # TODO Highlight selected tile with border color
            is_selected = tile.tile_id == self.selected_tile_id
            tint =(1.0, 1.0, 0.0, 1.0)           
            
            tex_ref = imgui.ImTextureRef(tileset_info.gl_texture_id)
            clicked = imgui.image_button(
                f"tile_{tile.tile_id}",
                tex_ref,
                imgui.ImVec2(self.tile_button_size, self.tile_button_size),
                imgui.ImVec2(uv0_x, uv0_y),
                imgui.ImVec2(uv1_x, uv1_y),
                imgui.ImVec4(1.0, 1.0, 1.0, 1.0),
                imgui.ImVec4(*tint),
            )
            
            # Handle click
            if clicked:
                self.selected_tile_id = tile.tile_id
                logger.debug(f"Selected tile {tile.tile_id} from tileset {self.selected_tileset}")
            
            # Tooltip with tile info
            if imgui.is_item_hovered():
                imgui.set_tooltip(f"Tile {tile.tile_id}: {tile.name}\nSize: {tile.source_rect.w}x{tile.source_rect.h}")
        
        # Show selected tile info
        if self.selected_tile_id >= 0:
            imgui.text(f"Selected: Tile {self.selected_tile_id}")
    
    def _render_map_controls(self):
        """Render map creation and management controls"""
        imgui.text("Map Controls:")
        
        # New map button
        if imgui.button("New Map"):
            if self.tile_map_manager:
                self.tile_map_manager.create_new_map(
                    self.new_map_name, 
                    self.new_map_width, 
                    self.new_map_height, 
                    self.new_map_grid_size
                )
                logger.info(f"Created new map: {self.new_map_name}")
        
        # Clear map button
        imgui.same_line()
        if imgui.button("Clear Map"):
            if self.tile_map_manager:
                self.tile_map_manager.clear_map()
        
        # New map settings
        if imgui.tree_node("New Map Settings"):
            changed, self.new_map_name = imgui.input_text("Name", self.new_map_name)
            changed, self.new_map_width = imgui.input_int("Width", self.new_map_width)
            changed, self.new_map_height = imgui.input_int("Height", self.new_map_height)
            changed, self.new_map_grid_size = imgui.input_int("Grid Size", self.new_map_grid_size)
            
            # Clamp values
            self.new_map_width = max(1, min(1000, self.new_map_width))
            self.new_map_height = max(1, min(1000, self.new_map_height))
            self.new_map_grid_size = max(8, min(128, self.new_map_grid_size))
            
            imgui.tree_pop()
    
    def _render_grid_settings(self):
        """Render grid display settings"""
        imgui.text("Grid Settings:")
        
        changed, self.show_grid = imgui.checkbox("Show Grid", self.show_grid)
        if self.show_grid:
            changed, self.grid_opacity = imgui.slider_float("Grid Opacity", self.grid_opacity, 0.0, 1.0)
        
        # Apply grid settings to table if available
        if hasattr(self.context, 'current_table') and self.context.current_table:
            self.context.current_table.show_grid = self.show_grid
    
    def _render_file_operations(self):
        """Render save/load operations"""
        imgui.text("File Operations:")
        
        # Save filename input
        changed, self.save_filename = imgui.input_text("Filename", self.save_filename)
        
        # Save button
        if imgui.button("Save Map"):
            filepath = os.path.join(self.maps_directory, self.save_filename)
            if self.tile_map_manager:
                if self.tile_map_manager.save_map(filepath):
                    logger.info(f"Map saved to {filepath}")
                else:
                    logger.error(f"Failed to save map to {filepath}")
        
        # Load button
        imgui.same_line()
        if imgui.button("Load Map"):
            filepath = os.path.join(self.maps_directory, self.save_filename)
            if self.tile_map_manager and os.path.exists(filepath):
                if self.tile_map_manager.load_map(filepath):
                    logger.info(f"Map loaded from {filepath}")
                else:
                    logger.error(f"Failed to load map from {filepath}")
            else:
                logger.warning(f"Map file not found: {filepath}")
        
        # List available maps
        if imgui.tree_node("Available Maps"):
            try:
                map_files = [f for f in os.listdir(self.maps_directory) 
                           if f.endswith('.json')]
                
                for map_file in map_files:
                    if imgui.selectable(f"{map_file}##map_file")[0]:
                        self.save_filename = map_file
                        
            except Exception as e:
                imgui.text(f"Error listing maps: {e}")
            
            imgui.tree_pop()
    
    def _render_map_info(self):
        """Render current map information"""
        if not self.tile_map_manager:
            return
        
        map_info = self.tile_map_manager.get_map_info()
        if map_info:
            imgui.text("Current Map:")
            imgui.text(f"Name: {map_info['name']}")
            imgui.text(f"Size: {map_info['width']}x{map_info['height']}")
            imgui.text(f"Grid: {map_info['grid_size']}px")
            imgui.text(f"Tiles: {map_info['tile_count']}")
    
    def handle_mouse_click(self, world_x: float, world_y: float, button: int) -> bool:
        """Handle mouse click for tile placement/removal"""
        if not self.tile_manager or not self.tile_map_manager:
            return False
        
        # Only handle left mouse button
        if button != 1:  # SDL_BUTTON_LEFT
            return False
        
        # Only in GM mode
        if not self.actions_bridge.is_gm_mode():
            return False
        
        if self.tile_mode == "place":
            # Place tile
            if self.selected_tileset and self.selected_tile_id >= 0:
                success = self.tile_map_manager.place_tile(
                    self.selected_tileset, 
                    self.selected_tile_id, 
                    world_x, 
                    world_y
                )
                if success:
                    logger.debug(f"Placed tile at ({world_x}, {world_y})")
                return success
                
        elif self.tile_mode == "erase":
            # Remove tile
            success = self.tile_map_manager.remove_tile(world_x, world_y)
            if success:
                logger.debug(f"Removed tile at ({world_x}, {world_y})")
            return success
        
        return False
    
    def get_tile_map_manager(self):
        """Get the tile map manager for external access"""
        return self.tile_map_manager
