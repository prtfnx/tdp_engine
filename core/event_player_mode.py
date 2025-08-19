import sdl3
import traceback
from tools.logger import setup_logger
logger = setup_logger(__name__)

def handle_event(cnt, event):
    # Ensure pressed_keys exists
    if not hasattr(cnt, 'pressed_keys'):
        cnt.pressed_keys = set()
    match event.type:
        case sdl3.SDL_EVENT_QUIT:
            return False
        case sdl3.SDL_EVENT_KEY_DOWN:
            try:
                cnt.pressed_keys.add(event.key.scancode)
                update_player_acceleration(cnt)
                print(f"Pressed keys: {cnt.pressed_keys}")
                return True
            except Exception as e:
                logger.error(f"Error handling key down: {e}")
            return True
        case sdl3.SDL_EVENT_KEY_UP:
            try:
                cnt.pressed_keys.discard(event.key.scancode)
                update_player_acceleration(cnt)
                return True
            except Exception as e:
                logger.error(f"Error handling key up: {e}")
            return True
        case sdl3.SDL_EVENT_MOUSE_BUTTON_DOWN:
            try:
                # Left mouse button triggers shooting
                if hasattr(event, 'button') and event.button.button == sdl3.SDL_BUTTON_LEFT:
                    if hasattr(cnt.player, 'shoot'):
                        cnt.player.shoot()
                # If you want to keep other mouse button logic, call handle_mouse_button_down
                # handle_mouse_button_down(cnt, event)
                return True
            except Exception as e:
                logger.error(f"Error handling mouse button down: {e}")
                return True
        case sdl3.SDL_EVENT_MOUSE_BUTTON_UP:
            try:
                # handle_mouse_button_up(cnt, event)
                return True
            except Exception as e:
                logger.error(f"Error handling mouse button up: {e}")
                return True
        case sdl3.SDL_EVENT_MOUSE_MOTION:
            try:
                # Track mouse position and update weapon direction
                if hasattr(event, 'motion'):
                    mouse_x = event.motion.x
                    mouse_y = event.motion.y
                    cnt.mouse_pos = (mouse_x, mouse_y)
                    if hasattr(cnt.player, 'set_weapon_direction'):
                        cnt.player.set_weapon_direction(mouse_x, mouse_y)  
                return True
            except Exception as e:
                logger.error(f"Error handling mouse motion: {e}")
                return True
        case _:
            # Handle other events if necessary
            logger.debug(f"Unhandled event type: {event.type}")
            return True

# New function to update player acceleration based on pressed keys
def update_player_acceleration(cnt):
    """Update player acceleration based on currently pressed keys."""
    # Define key mappings
    up_keys = {sdl3.SDL_SCANCODE_W, sdl3.SDL_SCANCODE_UP}
    down_keys = {sdl3.SDL_SCANCODE_S, sdl3.SDL_SCANCODE_DOWN}
    left_keys = {sdl3.SDL_SCANCODE_A, sdl3.SDL_SCANCODE_LEFT}
    right_keys = {sdl3.SDL_SCANCODE_D, sdl3.SDL_SCANCODE_RIGHT}

    ax = 0
    ay = 0
    # Y axis: up is negative, down is positive
    if cnt.pressed_keys & up_keys:
        ay -= 1
    if cnt.pressed_keys & down_keys:
        ay += 1
    # X axis: left is negative, right is positive
    if cnt.pressed_keys & left_keys:
        ax -= 1
    if cnt.pressed_keys & right_keys:
        ax += 1
    cnt.player.set_acceleration(ax, ay)