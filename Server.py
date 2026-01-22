import socket
import threading

# Configuration
SERVER = "127.0.0.1" # Localhost
PORT = 5555
ADDR = (SERVER, PORT)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

clients = []
positions = {}

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    connected = True
    while connected:
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data: break
            
            # Simple protocol: "x,y"
            positions[addr] = data
            
            # Send all positions to this client
            reply = str(positions)
            conn.sendall(str.encode(reply))
        except:
            break
    
    conn.close()

def start():
    server.listen()
    print(f"[LISTENING] Server is on {SERVER}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start()