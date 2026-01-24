import pygame
import socket
import ast
import sys
import math
import random

# =============================================================================
# CONFIGURATION
# =============================================================================
pygame.init()
WIDTH, HEIGHT = 750, 500 
GAME_WIDTH = 500 
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiplayer Client v8.0 - Global Sync")

# Fonts
font = pygame.font.SysFont("Arial", 18, bold=True)
small_font = pygame.font.SysFont("Arial", 14)
chat_font = pygame.font.SysFont("Consolas", 12)
large_font = pygame.font.SysFont("Arial", 40, bold=True)

COLORS = [(255,59,48), (52,199,89), (0,122,255), (255,204,0), (175,82,222), (255,45,85)]
SHAPES = ["square", "circle", "triangle", "star"]

# =============================================================================
# HELPERS
# =============================================================================

def draw_player_shape(surface, shape, color, pos, size=30):
    """Draws the player shape centered on the position."""
    x, y = pos
    if shape == "circle":
        pygame.draw.circle(surface, color, (x, y), size//2)
    elif shape == "triangle":
        # Centered triangle points
        pts = [(x, y - size//2), (x - size//2, y + size//2), (x + size//2, y + size//2)]
        pygame.draw.polygon(surface, color, pts)
    elif shape == "star":
        pts = []
        for i in range(10):
            angle = math.radians(i * 36)
            r = size//2 if i % 2 == 0 else size//4
            pts.append((x + r * math.sin(angle), y - r * math.cos(angle)))
        pygame.draw.polygon(surface, color, pts)
    else: # Square
        pygame.draw.rect(surface, color, (x - size//2, y - size//2, size, size))

def connect_to_server(ip, shape, color):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(3) 
    try:
        client.connect((ip, 5555))
        client.send(str.encode(f"{shape}|{color}"))
        data = client.recv(4096).decode('utf-8')
        
        if data == "BANNED": return None, "BANNED"
        if data == "NOT_WHITELISTED": return None, "WHITELIST ONLY"
        
        return client, data.split('|')
    except: return None, "SERVER OFFLINE"

# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    game_state = "INPUT_IP"
    user_text = "127.0.0.1"
    chat_input = ""
    chat_history = []
    chat_visible = True 
    
    selected_shape = "square"
    selected_color = COLORS[0]
    
    client, error_msg = None, ""
    my_x, my_y, my_label = 225, 225, ""
    client_addr = None # Stores our local (IP, Port) to identify ourselves in dict
    
    run = True
    clock = pygame.time.Clock()

    while run:
        win.fill((235, 235, 235))
        events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.QUIT: run = False
            
            # --- IP INPUT ---
            if game_state == "INPUT_IP" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: game_state = "SELECT_CHAR"
                elif event.key == pygame.K_BACKSPACE: user_text = user_text[:-1]
                else: user_text += event.unicode
            
            # --- SELECTION SCREEN ---
            elif game_state == "SELECT_CHAR" and event.type == pygame.MOUSEBUTTONDOWN:
                for i, col in enumerate(COLORS):
                    if pygame.Rect(150 + i*40, 270, 30, 30).collidepoint(event.pos): selected_color = col
                for i, shp in enumerate(SHAPES):
                    if pygame.Rect(150 + i*60, 350, 45, 45).collidepoint(event.pos): selected_shape = shp
                if pygame.Rect(320, 235, 100, 30).collidepoint(event.pos):
                    selected_color, selected_shape = random.choice(COLORS), random.choice(SHAPES)
                if pygame.Rect(175, 420, 150, 50).collidepoint(event.pos): game_state = "CONNECTING"

            # --- GAME CONTROLS ---
            elif game_state == "PLAYING" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB: chat_visible = not chat_visible
                elif event.key == pygame.K_BACKSPACE: chat_input = chat_input[:-1]
                elif event.key == pygame.K_RETURN: pass # Handled in network send
                else:
                    if len(chat_input) < 35: chat_input += event.unicode

        # --- RENDERING STATES ---
        if game_state == "INPUT_IP":
            win.blit(font.render("ENTER SERVER IP:", True, (50,50,50)), (180, 200))
            pygame.draw.rect(win, (255,255,255), (150, 240, 200, 40))
            win.blit(font.render(user_text, True, (0,0,0)), (160, 250))

        elif game_state == "SELECT_CHAR":
            win.blit(large_font.render("CHARACTER SETUP", True, (0,0,0)), (110, 50))
            draw_player_shape(win, selected_shape, selected_color, (225, 150), 60)
            for i, col in enumerate(COLORS):
                rect = pygame.Rect(150 + i*40, 270, 30, 30)
                pygame.draw.rect(win, col, rect)
                if selected_color == col: pygame.draw.rect(win, (0,0,0), rect, 3)
            for i, shp in enumerate(SHAPES):
                rect = pygame.Rect(150 + i*60, 350, 45, 45)
                pygame.draw.rect(win, (255,255,255), rect, 0, 5)
                draw_player_shape(win, shp, (100,100,100), (172 + i*60, 372), 30)
                if selected_shape == shp: pygame.draw.rect(win, (0,122,255), rect, 2, 5)
            pygame.draw.rect(win, (46, 204, 113), (175, 420, 150, 50), 0, 10)
            win.blit(font.render("JOIN GAME", True, (255,255,255)), (205, 435))

        elif game_state == "CONNECTING":
            client, result = connect_to_server(user_text, selected_shape, selected_color)
            if client:
                client_addr = client.getsockname() # Store our socket identity
                my_x, my_y = map(int, result[0].split(','))
                my_label, game_state = result[2], "PLAYING"
            else: error_msg, game_state = result, "ERROR"

        elif game_state == "PLAYING":
            view_width = GAME_WIDTH if chat_visible else WIDTH
            pygame.draw.rect(win, (255,255,255), (0,0, view_width, HEIGHT))
            
            keys = pygame.key.get_pressed()
            dx, dy = (keys[pygame.K_RIGHT]-keys[pygame.K_LEFT])*5, (keys[pygame.K_DOWN]-keys[pygame.K_UP])*5

            try:
                chat_out = ""
                if keys[pygame.K_RETURN] and chat_input:
                    chat_out, chat_input = chat_input, ""

                # Send current state
                client.send(str.encode(f"{my_x + dx},{my_y + dy}|{chat_out}"))
                data_in = client.recv(8192).decode('utf-8')
                
                if not data_in: 
                    game_state, error_msg = "ERROR", "KICKED"
                else:
                    resp = data_in.split('|')
                    players_dict = ast.literal_eval(resp[1])
                    tp_cmd = resp[2]
                    is_frozen = resp[3] == "True"
                    chat_history = ast.literal_eval(resp[4])

                    # --- SYNC LOGIC ---
                    # Update local choice if Admin changed us on the server
                    if client_addr in players_dict:
                        selected_shape = players_dict[client_addr].get("shape", selected_shape)
                        selected_color = players_dict[client_addr].get("color", selected_color)

                    if tp_cmd != "None": my_x, my_y = map(int, tp_cmd.split(','))
                    elif not is_frozen: my_x, my_y = my_x + dx, my_y + dy

                    # Render All Players
                    for addr, p in players_dict.items():
                        px, py = map(int, p["pos"].split(','))
                        is_me = (addr == client_addr)
                        draw_player_shape(win, p.get("shape", "square"), p["color"], (px, py), 30)
                        lbl_color = (0,120,255) if is_me else (50,50,50)
                        win.blit(small_font.render(p["label"], True, lbl_color), (px - 20, py - 35))

                # Sidebar UI
                if chat_visible:
                    pygame.draw.rect(win, (44, 62, 80), (GAME_WIDTH, 0, 250, HEIGHT))
                    win.blit(font.render("CHAT (TAB TO HIDE)", True, (255,255,255)), (GAME_WIDTH+10, 10))
                    for i, m in enumerate(chat_history[-25:]):
                        win.blit(chat_font.render(m, True, (255,255,100) if "ADMIN" in m else (255,255,255)), (GAME_WIDTH+10, 40 + i*15))
                
                pygame.draw.rect(win, (30,30,30), (0, HEIGHT-40, view_width, 40))
                win.blit(chat_font.render(f"> {chat_input}", True, (0,255,0)), (10, HEIGHT-25))

            except:
                game_state, error_msg = "ERROR", "DISCONNECTED"

        elif game_state == "ERROR":
            pygame.draw.rect(win, (44, 62, 80), (0,0, WIDTH, HEIGHT))
            win.blit(large_font.render("CONNECTION LOST", True, (255,255,255)), (WIDTH//2 - 180, 150))
            win.blit(font.render(f"REASON: {error_msg}", True, (231, 76, 60)), (WIDTH//2 - 100, 220))
            # Buttons (Simplified for base)
            pygame.draw.rect(win, (52, 152, 219), (WIDTH//2 - 75, 320, 150, 50), 0, 10)
            win.blit(font.render("BACK TO IP", True, (255,255,255)), (WIDTH//2 - 55, 335))
            if pygame.mouse.get_pressed()[0] and pygame.Rect(WIDTH//2 - 75, 320, 150, 50).collidepoint(pygame.mouse.get_pos()):
                game_state = "INPUT_IP"

        pygame.display.update()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()