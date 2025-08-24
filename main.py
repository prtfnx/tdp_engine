# For pyinstaller build and deploy
from email.mime import audio
import re, sys, os

from annotated_types import T
if sys.stdout is None: sys.stdout = open(os.devnull, 'w')
if sys.stderr is None: sys.stderr = open(os.devnull, 'w')
# If running frozen, ensure current working directory points to the extracted
# bundle location so relative paths like 'resources/...' resolve correctly.
if getattr(sys, 'frozen', False):
    try:
        # In onefile, sys._MEIPASS points to the temp extraction dir; in onedir the
        # executable directory is where resources are located.
        if getattr(sys, '_MEIPASS', None):
            os.chdir(sys._MEIPASS)
        else:
            os.chdir(os.path.dirname(sys.executable))
    except Exception:
        pass



# System imports
import sys
import sdl3
from typing import TYPE_CHECKING
from ctypes import c_int, c_char_p, c_void_p, byref
# Core imports
from core import event_sys, event_player_mode
from core.Context import Context
from core.Actions import Actions
from core.actions_protocol import Position
from core.MovementManager import MovementManager
from core.EnemyManager import EnemyManager
from core.TileMapManager import TileMapManager
from core.TileManager import TileManager
# Render imports
from render import PaintManager
from render.RenderManager import RenderManager
from render.LayoutManager import LayoutManager
from render.LightManager import LightManager, Light
from render.GeometricManager import GeometricManager
# Tools imports
from tools.logger import setup_logger
from tools import settings
# GUI imports
if settings.GUI_ENABLED:
    import gui.gui_imgui as gui_imgui    
# Storage imports
from storage.StorageManager import StorageManager
from storage.AssetManager import ClientAssetManager
# Game imports
from core.Player import Player

if TYPE_CHECKING:
    SDL_Renderer = c_void_p
    SDL_Window = c_void_p 
    SDL_GLContext = c_void_p
       

logger = setup_logger(__name__)
LOAD_LEVEL: bool = False
MUSIC: bool = True
DEBUG_MODE: bool = True
PLAYER_MODE: bool = False
BASE_WIDTH: int = 1920
BASE_HEIGHT:  int = 1080
TITLE: c_char_p = c_char_p(b"TDP Engine")
NET_SLEEP: float = 0.1
CHECK_INTERVAL: float = 2.0
NUMBER_OF_NET_FAILS: int = 5
TIME_TO_CONNECT: int = 4000  # 4 seconds
COMPENDIUM_SYSTEM: bool = True
LIGHTING_SYS: bool = True
# Layout configuration - centered table with GUI panels on all sides
TABLE_AREA_PERCENT: float = 0.60   # 60% for centered table
GUI_PANEL_SIZE: int = 200           # Fixed size for GUI panels (pixels)
MARGIN_SIZE: int = 20               # Margin between table and GUI panels


def sdl3_init() -> tuple[sdl3.SDL_Window, sdl3.SDL_Renderer, sdl3.SDL_GLContext]:
       
    if not sdl3.SDL_Init(sdl3.SDL_INIT_VIDEO | sdl3.SDL_INIT_EVENTS | sdl3.SDL_INIT_AUDIO):
        logger.error(f"Failed to initialize library: {sdl3.SDL_GetError().decode()}.")
        sys.exit(1)
    # Create window with OpenGL support
    window = sdl3.SDL_CreateWindow(
        TITLE, c_int(BASE_WIDTH), c_int(BASE_HEIGHT), 
        sdl3.SDL_WINDOW_RESIZABLE | sdl3.SDL_WINDOW_OPENGL
    )
    if not window:
        logger.critical("Failed to create SDL window: %s", sdl3.SDL_GetError().decode())
        sys.exit(1)
    
    # Create OpenGL context BEFORE renderer
    gl_context = sdl3.SDL_GL_CreateContext(window)
    sdl3.SDL_GL_SetSwapInterval(c_int(1))
    if not gl_context:
        logger.critical("Failed to create OpenGL context: %s", sdl3.SDL_GetError().decode())
        sys.exit(1)
    
    # Make context current
    sdl3.SDL_GL_MakeCurrent(window, gl_context)    
    render_drivers = [sdl3.SDL_GetRenderDriver(i).decode() for i in range(sdl3.SDL_GetNumRenderDrivers())]
    render_driver = next((d for d in [ "opengl", "software"] if d in render_drivers), None)
    if not render_driver:
        logger.error("No suitable render driver found.")
        sys.exit(1)
    logger.info(f"Renderer {render_driver} initialized.")    
    renderer = sdl3.SDL_CreateRenderer(window, render_driver.encode())
    if not renderer:
        logger.critical("Failed to create renderer: %s", sdl3.SDL_GetError().decode())
        sys.exit(1)    
    return window, renderer, gl_context

def init_audio():
    """Initialize audio subsystem."""    
    audioDrivers = [sdl3.SDL_GetAudioDriver(i).decode() for i in range(sdl3.SDL_GetNumAudioDrivers())]
    logger.debug(f"Available audio drivers: {', '.join(audioDrivers)} (current: {sdl3.SDL_GetCurrentAudioDriver().decode()}).")
    if currentAudioDevice := sdl3.SDL_OpenAudioDevice(sdl3.SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, None):
        sdl3.Mix_Init(sdl3.MIX_INIT_MP3)
        sdl3.Mix_OpenAudio(currentAudioDevice, byref(audioSpec := sdl3.SDL_AudioSpec()))
        logger.debug(f"Current audio device: {sdl3.SDL_GetAudioDeviceName(currentAudioDevice).decode()}.")
        music = sdl3.Mix_LoadMUS(b"resources/music/battle_music.mp3")
        if not music:
            logger.error(f"Failed to load music: {sdl3.SDL_GetError().decode()}")
        
           
    else:
        logger.error(f"Failed to open audio device: {sdl3.SDL_GetAudioDeviceName(sdl3.SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK).decode()}, error: {sdl3.SDL_GetError().decode()}.")
    return music, currentAudioDevice
  

def SDL_AppInit_func() -> Context:
    """Initialize SDL window, renderer, and network client."""
    
    # if sdl dont init, exit
    try:
        window, renderer, gl_context = sdl3_init()
        
    except Exception as e:        
        logger.exception(f'SDL initialization failed: {e}')
        sdl3.SDL_Quit()
        sys.exit(1)
    

    game_context = Context(renderer, window, base_width=BASE_WIDTH, base_height=BASE_HEIGHT)
    game_context.debug_mode = DEBUG_MODE
    game_context.gl_context = gl_context
    game_context.is_gm = not(PLAYER_MODE)
    game_context.player = Player("John1", context=game_context)
    logger.info("Context initialized.")
    # Initialise audio
    if MUSIC:
        try:
            music, audio_device = init_audio()
            game_context.audio_device = audio_device
            game_context.music = music
            sound_folder = "resources/sounds/pistol_shot"
            mp3_files = [f for f in os.listdir(sound_folder) if f.endswith(".wav")]
            game_context.GunshotSounds = [sdl3.Mix_LoadWAV(os.path.join(sound_folder, path).encode()) for path in mp3_files]
            # TODO - music manager and store it here
            player_steps_folder= "resources/sounds/player/footsteps_floor"
            minotaur_steps_folder= "resources/sounds/minotaur/footsteps"
            game_context.player_steps = [sdl3.Mix_LoadWAV(os.path.join(player_steps_folder, path).encode()) for path in os.listdir(player_steps_folder) if path.endswith(".wav")]            
            game_context.minotaur_steps = [sdl3.Mix_LoadWAV(os.path.join(minotaur_steps_folder, path).encode()) for path in os.listdir(minotaur_steps_folder) if path.endswith(".wav")]
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")    
    # Initialize LayoutManager 
    try:
        logger.info("Initializing LayoutManager...")
        game_context.LayoutManager = LayoutManager()
        if game_context.LayoutManager:
           game_context.LayoutManager.update_layout(window)
        else:
           logger.warning("LayoutManager not available.")
        logger.info("LayoutManager initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize LayoutManager: {e}")
        game_context.LayoutManager = None    
    # Initialize AssetManager 
    try:
        logger.info("Initializing AssetManager with owned StorageManager and DownloadManager...")
        game_context.AssetManager = ClientAssetManager(
            cache_dir=None,  # Uses settings default
            storage_root=settings.DEFAULT_STORAGE_PATH
        )
        logger.info("AssetManager initialized with owned managers.")
    except Exception as e:
        logger.error(f"Failed to initialize AssetManager: {e}")
        game_context.AssetManager = None
    # Initialize GeometryManager
    try:
        logger.info("Initializing GeometryManager...")
        game_context.GeometryManager = GeometricManager()       
        logger.info("GeometryManager initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize GeometryManager: {e}")
        game_context.GeometryManager = None
    # Initialize Actions
    try:
        logger.info("Initializing Actions system...")
        game_context.Actions = Actions(game_context)
        game_context.Actions.AssetManager = game_context.AssetManager
        logger.info("Actions system initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Actions system: {e}")        
    # Init GUI system
    if settings.GUI_ENABLED:
        try:            
            simplified_gui = gui_imgui.create_gui(game_context)
            logger.info("Simplified GUI system initialized.")
            game_context.imgui = simplified_gui            
            # Connect Actions system to GUI actions bridge
            if game_context.Actions and hasattr(simplified_gui, 'actions_bridge'):
                game_context.Actions.actions_bridge = simplified_gui.actions_bridge
                logger.info("Connected Actions system to GUI actions bridge.")
            else:
                logger.warning("Actions system not available.")
        except Exception as e:
            logger.exception(f"Error initializing Simplified GUI: {e}")
            game_context.imgui = None

    # Initialie lighting system
    if LIGHTING_SYS:
        logger.info("Initializing lighting system...")
        try:
            game_context.LightingManager = LightManager(game_context, name ="default_lighting_manager")
            if game_context.LightingManager: 
                default_light = Light('default_light')
                game_context.LightingManager.create_light_texture(default_light, path_to_image=b"resources/light.png")
                game_context.light_on= True
                logger.info("Lighting system initialized.")
            else:
                logger.warning("LightingManager not available.")
        except Exception as e:
            logger.error(f"Failed to initialize lighting system: {e}")
            game_context.LightingManager = None
   
    # Initialize paint system
    try:
        PaintManager.init_paint_system(game_context)
        logger.info("Paint system initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize paint system: {e}")       
    # Initialize Table    
    
    test_table = game_context.add_table("test_table", BASE_WIDTH*3, BASE_HEIGHT*3)  
    if test_table:           
        result1=game_context.Actions.create_sprite( test_table.table_id, "sprite_map", Position(0, 0), image_path="map.jpg", scale_x=1, scale_y=1, layer='map')       

        result2=game_context.Actions.create_sprite( test_table.table_id, "sprite_wall1", Position(300, -150), image_path="wall1.png", scale_x=0.1, scale_y=0.1, collidable=True, layer='obstacles')
        result3=game_context.Actions.create_sprite( test_table.table_id, "sprite_wall2", Position(6, -150), image_path="wall1.png", scale_x=0.1, scale_y=0.1, collidable=True, layer='obstacles')
        result4=game_context.Actions.create_sprite( test_table.table_id, "sprite_wall3", Position(300, 300), image_path="wall1.png", scale_x=0.1, scale_y=0.1, collidable=True, layer='obstacles')
        result5=game_context.Actions.create_sprite( test_table.table_id, "sprite_wall4", Position(6, 300), image_path="wall1.png", scale_x=0.1, scale_y=0.1, collidable=True, layer='obstacles')
        #result51=game_context.Actions.create_sprite( test_table.table_id, "sprite_wall", Position(300, 300), image_path="wall1.png", scale_x=0.1, scale_y=0.1, collidable=True, layer='tokens')
        
        logger.info(f"Created sprites:  {result4}, {result5}")
        # add player        
        result9=game_context.Actions.create_animated_sprite(test_table.table_id, "sprite_foots_run", Position(0, 0), image_path="soldier/foots/run.png", atlas_path="resources/soldier/foots/run.json", scale_x=0.5, scale_y=0.5, collidable=False, visible=False, frame_duration=30, is_player=True)
        result6=game_context.Actions.create_animated_sprite(test_table.table_id, "sprite_player_idle", Position(0, 0), image_path="soldier/handgun/idle.png", atlas_path="resources/soldier/handgun/idle.json", scale_x=0.5, scale_y=0.5, collidable=False,is_player=True, visible=True, frame_duration=100)
        result7=game_context.Actions.create_animated_sprite(test_table.table_id, "sprite_player_move", Position(0, 0), image_path="soldier/handgun/move.png", atlas_path="resources/soldier/handgun/move.json", scale_x=0.5, scale_y=0.5, collidable=False, visible=False, frame_duration=100, is_player=True)
        result8=game_context.Actions.create_animated_sprite(test_table.table_id, "sprite_player_shoot", Position(0, 0), image_path="soldier/handgun/shoot.png", atlas_path="resources/soldier/handgun/shoot.json", scale_x=0.5, scale_y=0.5, collidable=False, visible=False, frame_duration=100, is_player=True)
        
        if result6.success and result6.data:
            game_context.player.sprite = result6.data['sprite']
            game_context.player.sprite.coord_x = game_context.player.coord_x
            game_context.player.sprite.coord_y = game_context.player.coord_y
        if result6.success and result7.success and result8.success and result9.success:
            for sprite in [result6.data['sprite'], result7.data['sprite'], result8.data['sprite'], result9.data['sprite']]:
                game_context.player.sprite_dict[sprite.sprite_id] = sprite
                sprite.is_player = True
        test_table.player=game_context.player
        # Add data for bullets
        game_context.player.sprite_bullet_dict= {
            "sprite_path": "bullets/pistol_bullet/bullet.png",
            "atlas_path": "resources/bullets/pistol_bullet/bullet.json",
        }                
    # Initialize Enemy manager
    try:
        game_context.EnemyManager = EnemyManager()
        game_context.EnemyManager.context = game_context
        logger.info("EnemyManager initialized.")
        mage1 = game_context.EnemyManager.add_enemy('Mage_1',coord_x=-600, coord_y=150)
        minotaur1 = game_context.EnemyManager.add_enemy('Minotaur', coord_x=600, coord_y=150)

        for enemy in game_context.EnemyManager.enemies:
            #order [idle,walk, attack] #TODO - proper system for managment for enemies
            sprites_list_order = []
            for sprite_path, atlas_path in zip(enemy.list_of_sprites_path, enemy.list_of_atlas_path):
                result = game_context.Actions.create_animated_sprite(test_table.table_id, sprite_path + enemy.enemy_id, Position(-400, 500), image_path=sprite_path, atlas_path=atlas_path, scale_x=2, scale_y=2, collidable=False, visible=True, frame_duration=100, is_player=False)
                if result.success and result.data:
                    sprite = result.data['sprite']
                    enemy.sprite = sprite
                    enemy.sprite.coord_x = enemy.coord_x
                    enemy.sprite.coord_y = enemy.coord_y
                    # enemy.sprite.original_w = enemy.sprite.fra
                    # enemy.sprite.original_h = enemy.sprite.height
                    sprites_list_order.append(enemy.sprite)
            enemy.dict_of_sprites = {
                "sprite_enemy_idle": sprites_list_order[0],
                "sprite_enemy_walk": sprites_list_order[1],
                "sprite_enemy_attack": sprites_list_order[2]
            }

        # Link to casting rays:
        game_context.EnemyManager.cast_ray = game_context.GeometryManager.cast_ray_and_check_unobstructed_vision
        game_context.EnemyManager.prepare_enemies()

    except Exception as e:
        logger.error(f"Failed to initialize EnemyManager: {e}")
        game_context.EnemyManager = None
        raise(e)
    # Initialize TileManager
    try:
        game_context.TileManager = TileManager(game_context)
    except Exception as e:
        logger.error(f"Failed to initialize TileManager: {e}")
    
    # Initialize TileMapManager
    try:
        game_context.TileMapManager = TileMapManager(game_context, game_context.TileManager)
    except Exception as e:
        logger.error(f"Failed to initialize TileMapManager: {e}")
        game_context.TileMapManager = None

    # Initialize RenderManager
    try:
        logger.info("Initializing RenderManager...")
        game_context.RenderManager = RenderManager(renderer, window)
        if game_context.RenderManager:            
            game_context.RenderManager.dict_of_sprites_list = game_context.current_table.dict_of_sprites_list
            game_context.RenderManager.configure_layers()
            game_context.RenderManager.LightManager= game_context.LightingManager
            game_context.RenderManager.GeometricManager = game_context.GeometryManager
            logger.info("RenderManager initialized.")
        else:
            logger.warning("RenderManager not available.")
    except Exception as e:
        logger.error(f"Failed to initialize RenderManager: {e}")
        game_context.RenderManager = None
    
    # Initialize MovementManager
    try:
        logger.info("Initializing MovementManager...")
        game_context.MovementManager = MovementManager(game_context.current_table, game_context.player)
        game_context.MovementManager.context = game_context
    except Exception as e:
        logger.error(f"Failed to initialize MovementManager: {e}")
        game_context.MovementManager = None
    return game_context

def SDL_AppIterate(context):
    """This function runs every frame."""    
    now = sdl3.SDL_GetTicks()
    delta_time = now - context.last_time
    context.last_time = now
    table = context.current_table
    # Get current window size
    sdl3.SDL_GetWindowSize(context.window, context.window_width, context.window_height)
    window_width = context.window_width.value
    window_height = context.window_height.value
    
    # Get viewport from LayoutManager (updated by ImGui)
    if hasattr(context, 'LayoutManager'):
        table_x, table_y, table_width, table_height = context.LayoutManager.table_area
    else:
        # Fallback to default values if LayoutManager not available
        table_x, table_y, table_width, table_height = 0, 0, window_width, window_height
    # Store layout info in context for other systems to use
    context.layout = {
        'table_area': (table_x, table_y, table_width, table_height),
        'window_size': (window_width, window_height)
    }    
    if table:
        # Set the table's screen area for coordinate transformation
        table.set_screen_area(table_x, table_y, table_width, table_height)

    # Movement
    context.MovementManager.move_and_collide(delta_time, table)
    # Render all sdl content
    context.RenderManager.iterate_draw(table, context.light_on, context)
    # Render paint system if active (in table area)
    if PaintManager.is_paint_mode_active():
        PaintManager.render_paint_system()
    # Enemy logic    
    context.EnemyManager.update(context.player, context.RenderManager.obstacles_np, delta_time)    
    # Async event queue for network and io   
    if context.AssetManager and context.Actions:
        completed = context.AssetManager.process_all_completed_operations()        
        # Process completed operations through Actions
        for op in completed:
            success = op.get('success', False)            
            if success:
                context.Actions.handle_completed_operation(op)
            else:
                context.Actions.handle_operation_error(op)
    return sdl3.SDL_APP_CONTINUE


def main():
    """Main entry point."""
    logger.info("Starting TDP Engine")
    # Initialize SDL
    try:
        context = SDL_AppInit_func()
    except Exception as e:
        logger.critical("Error initializing SDL: %s", e)
        sdl3.SDL_Quit()
        raise(e)
           
    running = True
    event = sdl3.SDL_Event() 
    if LOAD_LEVEL:
        context.Actions.load_table(path_to_table="tables/table_session.json")
    while running:
        # Handle events
        while sdl3.SDL_PollEvent(event):          
            if context.is_gm:
                # Let ImGui process events first and check if it consumed them
                gui_consumed = False
                if context.gui and context.imgui:
                    gui_consumed = context.imgui.process_event(event)            
                # Only process game events if ImGui didn't consume them
                if context.gui:
                    if not gui_consumed:
                    # Handle paint events
                        if PaintManager.handle_paint_events(event):
                            continue  
                    # Handle normal game events
                        running = event_sys.handle_event(context, event)
                else:
                    if PaintManager.handle_paint_events(event):
                            continue 
                    running = event_sys.handle_event(context, event)
            else:                
                context.current_table.selected_sprite = context.player.sprite
                running = event_player_mode.handle_event(context, event)
        # Render SDL content first (SDL handles its own clearing)
        SDL_AppIterate(context)       
        # Then render ImGui over the SDL content
        sdl3.SDL_FlushRenderer(context.renderer)
        if context.gui and context.imgui:
            context.imgui.iterate()        
        # Final buffer swap to display both SDL and ImGui content
        sdl3.SDL_GL_SwapWindow(context.window)        
    # Cleanup
    sdl3.Mix_FreeMusic(context.music)
    sdl3.Mix_CloseAudio()
    sdl3.Mix_Quit()
    sdl3.SDL_DestroyRenderer(context.renderer)
    sdl3.SDL_DestroyWindow(context.window)
    sdl3.SDL_Quit()

if __name__ == "__main__":
    main()