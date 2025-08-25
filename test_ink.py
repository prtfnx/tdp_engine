import sdl3
import moderngl
import numpy as np
import math
import random
import ctypes
from typing import List, Tuple

class InkDrop:
    def __init__(self, x: float, y: float, initial_size: float = 5.0, width=1200, height=800):
        self.x = (2.0 * x / width) - 1.0
        self.y = 1.0 - (2.0 * y / height)
        self.size = initial_size
        self.max_size = initial_size * 3.0
        self.age = 0.0
        self.spread_speed = random.uniform(0.5, 1.5)
        self.opacity = 1.0
        self.noise_offset = random.uniform(0, 1)
        
    def update(self, dt: float):
        self.age += dt
    # Ink spreads over time
        if self.size < self.max_size:
            self.size += self.spread_speed * dt * 10
        
    # Slow fading
        if self.age > 5.0:
            self.opacity = max(0, 1.0 - (self.age - 5.0) / 10.0)

class UnstableAsset:
    def __init__(self, x: float, y: float, asset_type: str = "crystal",width=1200, height=800):
        self.x = (2.0 * x / width) - 1.0
        self.y = 1.0 - (2.0 * y / height)
        self.base_x = x
        self.base_y = y
        self.asset_type = asset_type
        self.time = 0.0
        self.scale = 1.0
        self.rotation = 0.0
        self.flicker_intensity = random.uniform(0.3, 0.8)
        self.noise_seed = random.uniform(0, 1000)
        
    def update(self, dt: float):
        self.time += dt
        
    # Unstable flickering of position
        noise_x = math.sin(self.time * 3 + self.noise_seed) * 2
        noise_y = math.cos(self.time * 2.5 + self.noise_seed) * 1.5
        self.x = self.base_x + noise_x
        self.y = self.base_y + noise_y
        
    # Flickering size
        self.scale = 1.0 + math.sin(self.time * 4) * 0.1
        
    # Smooth rotation
        self.rotation += dt * 0.5

class InkWorldDemo:
    def __init__(self, width: int = 1200, height: int = 800):
        self.width = width
        self.height = height
        
    # SDL3 initialization
        if not sdl3.SDL_Init(sdl3.SDL_INIT_VIDEO):
            err = sdl3.SDL_GetError()
            raise RuntimeError(f"SDL3 init failed: {err.decode() if err else 'Unknown error'}")

        # OpenGL attribute setup
        sdl3.SDL_GL_SetAttribute(sdl3.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
        sdl3.SDL_GL_SetAttribute(sdl3.SDL_GL_CONTEXT_MINOR_VERSION, 3)
        sdl3.SDL_GL_SetAttribute(sdl3.SDL_GL_CONTEXT_PROFILE_MASK, sdl3.SDL_GL_CONTEXT_PROFILE_CORE)
        sdl3.SDL_GL_SetAttribute(sdl3.SDL_GL_DOUBLEBUFFER, 1)
        sdl3.SDL_GL_SetAttribute(sdl3.SDL_GL_DEPTH_SIZE, 24)

        # Window creation
        self.window = sdl3.SDL_CreateWindow(
            b"Ink World Demo - PySDL3",
            width, height,
            sdl3.SDL_WINDOW_OPENGL | sdl3.SDL_WINDOW_RESIZABLE
        )
        
        if not self.window:
            err = sdl3.SDL_GetError()
            raise RuntimeError(f"Window creation failed: {err.decode() if err else 'Unknown error'}")
        
    # OpenGL context creation
        self.gl_context = sdl3.SDL_GL_CreateContext(self.window)
        if not self.gl_context:
            err = sdl3.SDL_GetError()
            raise RuntimeError(f"GL context creation failed: {err.decode() if err else 'Unknown error'}")
        
    # Enable VSync
        sdl3.SDL_GL_SetSwapInterval(1)
        
    # ModernGL initialization
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
    # Game objects
        self.ink_drops: List[InkDrop] = []
        self.unstable_assets: List[UnstableAsset] = []
        
    # For tracking drawing
        self.is_drawing = False
        self.last_mouse_pos = None
        
        self.running = True
        self.last_time = sdl3.SDL_GetTicks() / 1000.0
        
        self.setup_shaders()
        print(self.get_startup_message())
        
    def get_startup_message(self):
        return """=== INK WORLD - DEMO (PySDL3 + ModernGL) ===

    Controls:
    • Left mouse button + move: draw ink lines
    • Right mouse button: create unstable cyberpunk asset
    • ESC: exit

    Effects:
    • Ink slowly spreads into puddles
    • Assets flicker and move unstably
    • Procedural shape and color generation
    • Dark cyberpunk atmosphere

    Tech: PySDL3 + ModernGL + OpenGL shaders
    """
        
    def setup_shaders(self):
    # Simple shader for ink rendering
        vertex_shader = '''
        #version 330 core
        layout(location = 0) in vec2 in_position;
        layout(location = 1) in float in_size;
        layout(location = 2) in float in_opacity;

        uniform mat4 projection;
        uniform float time;

        out float v_opacity;
        out float v_size;
        out vec2 v_center;

        void main() {
            v_opacity = in_opacity;
            v_size = in_size;
            v_center = in_position;
            // Dummy usage to prevent optimization out
            float dummy = in_position.x + in_position.y + in_size + in_opacity;
            gl_Position = projection * vec4(in_position, 0.0, 1.0);
            gl_PointSize = in_size * 2.0;
        }
        '''
        
        fragment_shader = '''
        #version 330 core
        in float v_opacity;
        in float v_size;
        in vec2 v_center;
        
        uniform float time;
        
        out vec4 fragColor;
        
        float noise(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }
        
        void main() {
            vec2 coord = gl_PointCoord - 0.5;
            float dist = length(coord);
            
            // Create unstable ink shape
            float noise_val = noise(v_center * 0.01 + time * 0.1);
            float distortion = 0.3 + noise_val * 0.4;
            
            if (dist > 0.5 * distortion) discard;
            
            // Gradient from center
            float alpha = (1.0 - dist * 2.0) * v_opacity;
            alpha = smoothstep(0.0, 1.0, alpha);
            
            // Ink color with slight blue tint
            vec3 ink_color = vec3(0.1, 0.15, 0.3) + vec3(0.0, 0.1, 0.2) * noise_val;
            
            fragColor = vec4(ink_color, alpha);
        }
        '''
        
        self.ink_program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        
    # Shader for unstable assets
        asset_vertex = '''
        #version 330 core
        in vec2 in_position;
        in float in_scale;
        in float in_rotation;
        
        uniform mat4 projection;
        uniform float time;
        
        out vec2 v_uv;
        out float v_time;
        
        void main() {
            v_time = time;
            
            // Create quad for asset
            vec2 vertices[4] = vec2[](
                vec2(-1.0, -1.0), vec2(1.0, -1.0), 
                vec2(-1.0, 1.0), vec2(1.0, 1.0)
            );
            
            vec2 vertex = vertices[gl_VertexID % 4] * 20.0 * in_scale;
            
            // Rotation
            float cos_r = cos(in_rotation);
            float sin_r = sin(in_rotation);
            vec2 rotated = vec2(
                vertex.x * cos_r - vertex.y * sin_r,
                vertex.x * sin_r + vertex.y * cos_r
            );
            
            vec2 world_pos = in_position + rotated;
            gl_Position = projection * vec4(world_pos, 0.0, 1.0);
            v_uv = vertices[gl_VertexID % 4];
        }
        '''
        
        asset_fragment = '''
        #version 330 core
        in vec2 v_uv;
        in float v_time;
        
        out vec4 fragColor;
        
        float noise(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }
        
        void main() {
            float dist = length(v_uv);
            if (dist > 1.0) discard;
            
            // Create crystalline structure
            float angle = atan(v_uv.y, v_uv.x);
            float sectors = floor(angle / (3.14159 / 3.0));
            
            float noise_val = noise(v_uv * 5.0 + v_time * 0.5);
            float flicker = 0.7 + 0.3 * sin(v_time * 8.0 + noise_val * 10.0);
            
            // Cyberpunk colors
            vec3 color = mix(
                vec3(0.2, 0.8, 1.0),  // Синий
                vec3(0.8, 0.2, 1.0),  // Пурпурный
                noise_val
            ) * flicker;
            
            float alpha = (1.0 - dist) * 0.8;
            fragColor = vec4(color, alpha);
        }
        '''
        
        self.asset_program = self.ctx.program(vertex_shader=asset_vertex, fragment_shader=asset_fragment)
        
        # Настройка проекции
        projection = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
            ], dtype=np.float32)
            
        self.ink_program['projection'].write(projection.astype('f4').tobytes())
        self.asset_program['projection'].write(projection.astype('f4').tobytes())
    
    def handle_events(self):
        event = sdl3.SDL_Event()
        while sdl3.SDL_PollEvent(ctypes.byref(event)):
            if event.type == sdl3.SDL_EVENT_QUIT:
                self.running = False
                
            elif event.type == sdl3.SDL_EVENT_MOUSE_BUTTON_DOWN:
                print(f"Mouse click: button={event.button.button}, pos=({event.button.x}, {event.button.y})")
                
                if event.button.button == sdl3.SDL_BUTTON_LEFT:
                    print("LMB - adding ink drop")
                    self.is_drawing = True
                    self.last_mouse_pos = (event.button.x, event.button.y)
                    self.add_ink_drop(event.button.x, event.button.y)
                elif event.button.button == sdl3.SDL_BUTTON_RIGHT:
                    print("RMB - adding asset")
                    y_flipped = self.height - event.button.y
                    self.unstable_assets.append(UnstableAsset(event.button.x, y_flipped))
                    
            elif event.type == sdl3.SDL_EVENT_MOUSE_BUTTON_UP:
                if event.button.button == sdl3.SDL_BUTTON_LEFT:
                    print("LMB released - stop drawing")
                    self.is_drawing = False
                    self.last_mouse_pos = None
                    
            elif event.type == sdl3.SDL_EVENT_MOUSE_MOTION:
                if self.is_drawing:
                    current_pos = (event.motion.x, event.motion.y)
                    if self.last_mouse_pos:
                        print(f"Drawing line from {self.last_mouse_pos} to {current_pos}")
                        self.draw_ink_line(self.last_mouse_pos, current_pos)
                    self.last_mouse_pos = current_pos
                    
            elif event.type == sdl3.SDL_EVENT_KEY_DOWN:
                if event.key.key == sdl3.SDLK_ESCAPE:
                    self.running = False
                    
            elif event.type == sdl3.SDL_EVENT_WINDOW_RESIZED:
                self.width = event.window.data1
                self.height = event.window.data2
                print(f"Window resized: {self.width}x{self.height}")
                self.ctx.viewport = (0, 0, self.width, self.height)
                # Обновляем матрицу проекции
                projection = np.array([
                    [2.0/self.width, 0, 0, -1],
                    [0, -2.0/self.height, 0, 1],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ], dtype=np.float32)
                self.ink_program['projection'].write(projection.tobytes())
                self.asset_program['projection'].write(projection.tobytes())
    
    def add_ink_drop(self, x: float, y: float):
        # Toggle for Y-flip to test mapping
        USE_Y_FLIP = False # Set to False to test without Y-flip
        y_mapped = self.height - y if USE_Y_FLIP else y
        drop = InkDrop(x, y_mapped)
        self.ink_drops.append(drop)
        print(f"Added ink drop at ({x}, {y_mapped}), total drops: {len(self.ink_drops)}")
    
    def draw_ink_line(self, start: Tuple[float, float], end: Tuple[float, float]):
        # Создаем чернильные капли вдоль линии
        # Create ink drops along the line
        distance = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        steps = max(1, int(distance / 8))  # Каждые 8 пикселей
        
        for i in range(steps + 1):
            t = i / steps if steps > 0 else 0
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            self.add_ink_drop(x, y)
    
    def update(self, dt: float):
        # Обновляем чернила
        # Update ink drops
        self.ink_drops = [drop for drop in self.ink_drops if drop.opacity > 0.01]
        for drop in self.ink_drops:
            drop.update(dt)
        
        # Обновляем нестабильные ассеты
        # Update unstable assets
        for asset in self.unstable_assets:
            asset.update(dt)
    
    def render(self):
        self.ctx.clear(0.05, 0.05, 0.1, 1.0)  # Темно-синий фон
        
        current_time = sdl3.SDL_GetTicks() / 1000.0
        # Set time uniform for animation in shaders
        self.ink_program['time'].value = current_time
        self.asset_program['time'].value = current_time
        # Debug: print viewport and projection matrix 
        
        # Отладочная информация
        #if len(self.ink_drops) > 0 or len(self.unstable_assets) > 0:
            #print(f"Рендер: чернил={len(self.ink_drops)}, ассетов={len(self.unstable_assets)}")
        
        # Рендер чернил
        if self.ink_drops:
            #print(f"Рендерим {len(self.ink_drops)} чернильных капель")
            # Подготовка данных для чернил
            positions = []
            sizes = []
            opacities = []
            for i, drop in enumerate(self.ink_drops):
                positions.extend([drop.x, drop.y])
                sizes.append(drop.size)
                opacities.append(drop.opacity)
                # Debug: print NDC coordinates for each drop
                ndc_x = (2.0 * drop.x / self.width) - 1.0
                ndc_y = 1.0 - (2.0 * drop.y / self.height)
                #print(f"Ink drop {i}: window=({drop.x:.1f},{drop.y:.1f}) NDC=({ndc_x:.3f},{ndc_y:.3f})")
            # Debug: print positions for ink drops
            # print("Ink drop positions:", positions)
            # print("Ink drop sizes:", sizes)
            # print("Ink drop opacities:", opacities)
            # Создание буферов
            pos_buffer = self.ctx.buffer(np.array(positions, dtype=np.float32).tobytes())
                    # Prepare data for ink drops
            size_buffer = self.ctx.buffer(np.array(sizes, dtype=np.float32).tobytes())
            opacity_buffer = self.ctx.buffer(np.array(opacities, dtype=np.float32).tobytes())
            
            # VAO для чернил
            vao = self.ctx.vertex_array(
                self.ink_program,
                [(pos_buffer, '2f', 'in_position'),
                 (size_buffer, '1f', 'in_size'),
                 (opacity_buffer, '1f', 'in_opacity')]
            )
            # Debug print for ink drops can be enabled if needed
            
            # Включаем точки большого размера
                    # Create buffers
            self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
            
            
            vao.render(moderngl.POINTS)
            
                    # VAO for ink drops
            # Освобождаем буферы
            pos_buffer.release()
            size_buffer.release()
            opacity_buffer.release()
            vao.release()
        
        # Рендер нестабильных ассетов - упрощенная версия для отладки
            # Render unstable assets - use asset shader and correct buffer layout
            if self.unstable_assets:
                # print(f"Rendering {len(self.unstable_assets)} assets")
                positions = []
                scales = []
                rotations = []
                for asset in self.unstable_assets:
                    positions.extend([asset.x, asset.y])
                    scales.append(asset.scale)
                    rotations.append(asset.rotation)
                # Debug: print positions for assets
                print("Asset positions:", positions)
                print("Asset scales:", scales)
                print("Asset rotations:", rotations)
                if positions:
                    pos_buffer = self.ctx.buffer(np.array(positions, dtype=np.float32).tobytes())
                    scale_buffer = self.ctx.buffer(np.array(scales, dtype=np.float32).tobytes())
                    rotation_buffer = self.ctx.buffer(np.array(rotations, dtype=np.float32).tobytes())
                    vao = self.ctx.vertex_array(
                        self.asset_program,
                        [
                            (pos_buffer, '2f', 'in_position'),
                            (scale_buffer, '1f', 'in_scale'),
                            (rotation_buffer, '1f', 'in_rotation')
                        ]
                    )
                    vao.render(moderngl.POINTS)
                    pos_buffer.release()
                    scale_buffer.release()
                    rotation_buffer.release()
                    vao.release()
        
        sdl3.SDL_GL_SwapWindow(self.window)
    
    def run(self):
        while self.running:
            current_time = sdl3.SDL_GetTicks() / 1000.0
            dt = current_time - self.last_time
            self.last_time = current_time
            
            self.handle_events()
            self.update(dt)
            self.render()
            
            # Ограничение FPS (~60)
            sdl3.SDL_Delay(16)
        
        self.cleanup()
    
    def cleanup(self):
        if self.gl_context:
            sdl3.SDL_GL_DestroyContext(self.gl_context)
        if self.window:
            sdl3.SDL_DestroyWindow(self.window)
        sdl3.SDL_Quit()

if __name__ == "__main__":
    try:
        demo = InkWorldDemo()
        demo.run()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have installed: pysdl3, moderngl, numpy")
        import traceback
        traceback.print_exc()