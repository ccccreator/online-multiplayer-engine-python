import pygame
import socket
import ast

# Networking Setup
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 5555))

# Pygame Setup
pygame.init()
win = pygame.display.set_mode((500, 500))
pygame.display.set_caption("Multiplayer Square")

x, y = 50, 50
vel = 5

run = True
while run:
    pygame.time.delay(30)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    # Movement logic
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]: x -= vel
    if keys[pygame.K_RIGHT]: x += vel
    if keys[pygame.K_UP]: y -= vel
    if keys[pygame.K_DOWN]: y += vel

    # Send position and get others
    client.send(str.encode(f"{x},{y}"))
    data = client.recv(1024).decode('utf-8')
    all_positions = ast.literal_eval(data)

    # Drawing
    win.fill((255, 255, 255))
    for pos in all_positions.values():
        px, py = map(int, pos.split(','))
        pygame.draw.rect(win, (0, 255, 0), (px, py, 50, 50))
    
    pygame.display.update()

pygame.quit()