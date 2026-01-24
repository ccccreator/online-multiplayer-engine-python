import socket
import threading
import tkinter as tk
from tkinter import ttk, colorchooser
import queue
import ast

# =============================================================================
# CONFIGURATION & GLOBAL STATE
# =============================================================================
SERVER_IP, SERVER_PORT = "0.0.0.0", 5555
SHAPES = ["square", "circle", "triangle", "star"]
CENTER_X, CENTER_Y = "225", "225"

players = {}         
blacklist = set()
whitelist = set()
frozen_players = set()  
game_frozen = False     
server_running = False
server_socket = None
log_queue = queue.Queue()
chat_queue = queue.Queue()
chat_history = [] 

# =============================================================================
# SERVER CORE LOGIC
# =============================================================================

def log_msg(msg):
    log_queue.put(f"> {msg}")

def chat_log(msg):
    chat_queue.put(f"{msg}")

def start_server_logic():
    global server_running, server_socket
    if not server_running:
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((SERVER_IP, SERVER_PORT))
            server_socket.listen()
            server_running = True
            status_light.config(bg="lime")
            status_label.config(text="ONLINE", fg="green")
            log_msg("SYSTEM: Engine v7.8 Live.")
            threading.Thread(target=accept_connections, daemon=True).start()
        except Exception as e:
            log_msg(f"START ERROR: {e}")

def stop_server_logic():
    global server_running, server_socket
    server_running = False
    status_light.config(bg="red")
    status_label.config(text="OFFLINE", fg="red")
    if server_socket: server_socket.close()
    log_msg("SYSTEM: Server Stopped.")

def accept_connections():
    while server_running:
        try:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except: break

def handle_client(conn, addr):
    ip = addr[0]
    if use_blacklist.get() and ip in blacklist:
        conn.send(str.encode("BANNED")); return conn.close()
    if use_whitelist.get() and ip not in whitelist:
        conn.send(str.encode("NOT_WHITELISTED")); return conn.close()

    try:
        selection_data = conn.recv(1024).decode('utf-8')
        if not selection_data: return conn.close()
        
        parts = selection_data.split('|')
        chosen_shape = parts[0]
        chosen_color = ast.literal_eval(parts[1])

        p_id = len(players) + 1
        players[addr] = {
            "id": p_id, "pos": "225,225", "shape": chosen_shape,
            "color": chosen_color, "label": f"Player {p_id}", "teleport_to": "None"
        }
        log_msg(f"JOIN: {ip} (ID: {p_id}) Choice: {chosen_shape}")

        init_str = f"{players[addr]['pos']}|{players[addr]['color']}|{players[addr]['label']}"
        conn.send(str.encode(init_str))

        while server_running:
            data = conn.recv(4096).decode('utf-8')
            if not data: break
            
            payload = data.split("|")
            move_data = payload[0]
            incoming_chat = payload[1] if len(payload) > 1 else ""

            if not (game_frozen or ip in frozen_players):
                players[addr]["pos"] = move_data
            
            if incoming_chat:
                full_msg = f"{players[addr]['label']}: {incoming_chat}"
                chat_history.append(full_msg)
                if len(chat_history) > 15: chat_history.pop(0)
                chat_log(full_msg)

            t_cmd = players[addr].get("teleport_to", "None")
            reply = f"{len(players)}|{players}|{t_cmd}|{game_frozen or ip in frozen_players}|{chat_history}"
            conn.sendall(str.encode(reply))
            players[addr]["teleport_to"] = "None"
    except: pass
    finally:
        if addr in players: del players[addr]
        log_msg(f"LEAVE: {ip}")
        conn.close()

# =============================================================================
# ADMIN UI FUNCTIONS
# =============================================================================

def apply_shape():
    sel = player_tree.selection()
    new_shape = cb_shape.get()
    if sel and new_shape in SHAPES:
        addr_str = sel[0]
        for addr in players:
            if f"{addr[0]}:{addr[1]}" == addr_str:
                players[addr]["shape"] = new_shape
                log_msg(f"SHAPE: Set {addr[0]} to {new_shape}")

def apply_shape_all():
    new_shape = cb_shape.get()
    if new_shape in SHAPES:
        for addr in players:
            players[addr]["shape"] = new_shape
        log_msg(f"GLOBAL: All players set to {new_shape}")

def apply_color_all():
    color = colorchooser.askcolor()[0]
    if color:
        rgb = tuple(map(int, color))
        for addr in players:
            players[addr]["color"] = rgb
        log_msg(f"GLOBAL: All players colored to {rgb}")

def remove_blacklist():
    sel = lb_black.curselection()
    if sel:
        ip = lb_black.get(sel[0])
        blacklist.remove(ip)
        refresh_lists()
        log_msg(f"REMOVED: {ip} from Blacklist")

def remove_whitelist():
    sel = lb_white.curselection()
    if sel:
        ip = lb_white.get(sel[0])
        whitelist.remove(ip)
        refresh_lists()
        log_msg(f"REMOVED: {ip} from Whitelist")

def refresh_lists():
    lb_black.delete(0, tk.END); [lb_black.insert(tk.END, i) for i in sorted(list(blacklist))]
    lb_white.delete(0, tk.END); [lb_white.insert(tk.END, i) for i in sorted(list(whitelist))]

def send_admin_chat(event=None):
    msg = ent_top_chat.get()
    if msg:
        full_msg = f"ADMIN: {msg}"
        chat_history.append(full_msg)
        if len(chat_history) > 15: chat_history.pop(0)
        chat_log(full_msg)
        ent_top_chat.delete(0, tk.END)

def apply_teleport():
    sel = player_tree.selection()
    if sel:
        addr_str = sel[0]
        for addr in players:
            if f"{addr[0]}:{addr[1]}" == addr_str:
                tx, ty = ent_x.get(), ent_y.get()
                players[addr]["teleport_to"] = f"{tx},{ty}"
                log_msg(f"TELEPORT: {addr[0]} to {tx}, {ty}")

def teleport_all_to_coords():
    tx, ty = ent_x.get(), ent_y.get()
    for addr in players:
        players[addr]["teleport_to"] = f"{tx},{ty}"
    log_msg(f"TELEPORT ALL to {tx}, {ty}")

def pick_color():
    color = colorchooser.askcolor()[0]
    if color:
        sel = player_tree.selection()
        if sel:
            addr_str = sel[0]
            for addr in players:
                if f"{addr[0]}:{addr[1]}" == addr_str:
                    players[addr]["color"] = tuple(map(int, color))

def toggle_log_tab():
    if log_text_frame.winfo_viewable(): log_text_frame.pack_forget()
    else: log_text_frame.pack(side="left", fill="both", expand=True)

def toggle_chat_tab():
    if chat_text_frame.winfo_viewable(): chat_text_frame.pack_forget()
    else: chat_text_frame.pack(side="right", fill="both", expand=True)

def kick_player():
    sel = player_tree.selection()
    if sel:
        addr_str = sel[0]
        for addr in list(players.keys()):
            if f"{addr[0]}:{addr[1]}" == addr_str:
                del players[addr]
                log_msg(f"Kicked {addr[0]}")

def ban_selected():
    sel = player_tree.selection()
    if sel:
        addr_str = sel[0]
        ip = addr_str.split(':')[0]
        blacklist.add(ip)
        refresh_lists()
        kick_player()
        log_msg(f"BANNED {ip}")

def toggle_global_freeze():
    global game_frozen
    game_frozen = not game_frozen
    btn_fz.config(text="UNFREEZE ALL" if game_frozen else "FREEZE ALL GAME", bg="orange" if game_frozen else "SystemButtonFace")

def freeze_selected():
    for sel in player_tree.selection():
        addr_str = sel
        ip = addr_str.split(':')[0]
        if ip in frozen_players: frozen_players.remove(ip)
        else: frozen_players.add(ip)

def process_queues():
    while not log_queue.empty():
        msg = log_queue.get()
        terminal_log.config(state='normal')
        terminal_log.insert(tk.END, f"{msg}\n")
        terminal_log.see(tk.END); terminal_log.config(state='disabled')
    while not chat_queue.empty():
        msg = chat_queue.get()
        terminal_chat.config(state='normal')
        terminal_chat.insert(tk.END, f"{msg}\n")
        terminal_chat.see(tk.END); terminal_chat.config(state='disabled')
    root.after(100, process_queues)

# =============================================================================
# UI LAYOUT
# =============================================================================
root = tk.Tk()
root.title("Multiplayer Management Engine v7.8")
root.geometry("1250x1000")

# Header
top = tk.Frame(root, pady=10)
top.pack(fill="x")
tk.Button(top, text="START", bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), command=start_server_logic, width=10).pack(side="left", padx=10)
tk.Button(top, text="STOP", bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), command=stop_server_logic, width=10).pack(side="left", padx=5)
status_light = tk.Canvas(top, width=15, height=15, bg="red", highlightthickness=0); status_light.pack(side="left", padx=(20, 5))
status_label = tk.Label(top, text="OFFLINE", fg="red", font=("Arial", 10, "bold")); status_label.pack(side="left")

# Security
sec_frame = tk.LabelFrame(root, text=" Security & Access Management ")
sec_frame.pack(fill="x", padx=10, pady=2)

use_blacklist, use_whitelist = tk.BooleanVar(), tk.BooleanVar()
tk.Checkbutton(sec_frame, text="Active Blacklist", variable=use_blacklist).grid(row=0, column=0, sticky="w")
tk.Checkbutton(sec_frame, text="Active Whitelist", variable=use_whitelist).grid(row=0, column=1, sticky="w")

ent_ip = tk.Entry(sec_frame, width=30); ent_ip.grid(row=0, column=2, padx=10)
tk.Button(sec_frame, text="+ ADD TO BLACK", bg="#fab1a0", command=lambda: [blacklist.add(ent_ip.get()), refresh_lists()]).grid(row=0, column=3, padx=2)
tk.Button(sec_frame, text="+ ADD TO WHITE", bg="#55efc4", command=lambda: [whitelist.add(ent_ip.get()), refresh_lists()]).grid(row=0, column=4, padx=2)

# Listbox labels
tk.Label(sec_frame, text="--- BLACKLISTED IPS ---", font=("Arial", 8, "bold")).grid(row=1, column=0, columnspan=2, pady=(5,0))
tk.Label(sec_frame, text="--- WHITELISTED IPS ---", font=("Arial", 8, "bold")).grid(row=1, column=2, columnspan=3, pady=(5,0))

lb_black = tk.Listbox(sec_frame, height=4, width=50); lb_black.grid(row=2, column=0, columnspan=2, padx=5, pady=2)
lb_white = tk.Listbox(sec_frame, height=4, width=50); lb_white.grid(row=2, column=2, columnspan=3, padx=5, pady=2)

tk.Button(sec_frame, text="REMOVE SELECTED FROM BLACK", bg="#ff7675", fg="white", command=remove_blacklist).grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
tk.Button(sec_frame, text="REMOVE SELECTED FROM WHITE", bg="#00b894", fg="white", command=remove_whitelist).grid(row=3, column=2, columnspan=3, sticky="ew", padx=5, pady=2)

# Admin Controls
admin_f = tk.LabelFrame(root, text=" Global Admin & Chat Console ")
admin_f.pack(fill="x", padx=10, pady=5)
chat_bar_f = tk.Frame(admin_f); chat_bar_f.pack(fill="x", pady=5)
tk.Label(chat_bar_f, text="ADMIN CHAT:").pack(side="left", padx=5)
ent_top_chat = tk.Entry(chat_bar_f, bg="#fdfd96"); ent_top_chat.pack(side="left", fill="x", expand=True, padx=5)
ent_top_chat.bind("<Return>", send_admin_chat)
btn_fz = tk.Button(admin_f, text="FREEZE ALL", command=toggle_global_freeze); btn_fz.pack(side="left", padx=5)
tk.Button(admin_f, text="FREEZE SEL", command=freeze_selected).pack(side="left", padx=5)
tk.Button(admin_f, text="KICK SEL", bg="#e67e22", fg="white", command=kick_player).pack(side="right", padx=5)
tk.Button(admin_f, text="BAN SEL", bg="#c0392b", fg="white", command=ban_selected).pack(side="right", padx=10)

# Player Info
manage = tk.LabelFrame(root, text=" Player Info & Control ")
manage.pack(fill="both", expand=True, padx=10, pady=5)

style_f = tk.Frame(manage); style_f.pack(fill="x", pady=5)
tk.Label(style_f, text="X:").pack(side="left")
ent_x = tk.Entry(style_f, width=5); ent_x.pack(side="left", padx=2); ent_x.insert(0, "225")
tk.Label(style_f, text="Y:").pack(side="left")
ent_y = tk.Entry(style_f, width=5); ent_y.pack(side="left", padx=2); ent_y.insert(0, "225")
tk.Button(style_f, text="TP SELECTED", bg="#3498db", fg="white", command=apply_teleport).pack(side="left", padx=5)
tk.Button(style_f, text="TP ALL", bg="#2980b9", fg="white", command=teleport_all_to_coords).pack(side="left", padx=5)

tk.Button(style_f, text="COLOR SEL", bg="#8e44ad", fg="white", command=pick_color).pack(side="left", padx=5)
tk.Button(style_f, text="COLOR ALL", bg="#9b59b6", fg="white", command=apply_color_all).pack(side="left", padx=5)

cb_shape = ttk.Combobox(style_f, values=SHAPES, width=10); cb_shape.set("square"); cb_shape.pack(side="left", padx=5)
tk.Button(style_f, text="APPLY SHAPE", bg="#2c3e50", fg="white", command=apply_shape).pack(side="left", padx=2)
tk.Button(style_f, text="SHAPE ALL", bg="#34495e", fg="white", command=apply_shape_all).pack(side="left", padx=2)

cols = ("id", "ip", "color", "shape", "pos", "status")
player_tree = ttk.Treeview(manage, columns=cols, show="headings")
for c in cols: player_tree.heading(c, text=c.upper()); player_tree.column(c, width=140, anchor="center")
player_tree.pack(fill="both", expand=True)

# Footer Tabs
tab_control = tk.Frame(root); tab_control.pack(side="bottom", fill="x")
tk.Button(tab_control, text="TOGGLE SYSTEM LOG", bg="#34495e", fg="white", command=toggle_log_tab).pack(side="left", fill="x", expand=True)
tk.Button(tab_control, text="TOGGLE GLOBAL CHAT", bg="#2980b9", fg="white", command=toggle_chat_tab).pack(side="left", fill="x", expand=True)

console_area = tk.Frame(root, height=180); console_area.pack(side="bottom", fill="x", padx=10, pady=5)
log_text_frame = tk.Frame(console_area); log_text_frame.pack(side="left", fill="both", expand=True)
terminal_log = tk.Text(log_text_frame, height=8, bg="black", fg="#00FF00", font=("Consolas", 9), state='disabled'); terminal_log.pack(fill="both", expand=True)
chat_text_frame = tk.Frame(console_area); chat_text_frame.pack(side="right", fill="both", expand=True)
terminal_chat = tk.Text(chat_text_frame, height=8, bg="#1a1a1a", fg="white", font=("Consolas", 9), state='disabled'); terminal_chat.pack(fill="both", expand=True)

def refresh_table():
    selected_iids = player_tree.selection()
    for i in player_tree.get_children(): 
        player_tree.delete(i)
    
    for addr, d in players.items():
        addr_str = f"{addr[0]}:{addr[1]}"
        st = "FROZEN" if (game_frozen or addr[0] in frozen_players) else "Active"
        player_tree.insert("", "end", iid=addr_str, values=(d["id"], addr[0], d["color"], d["shape"], d["pos"], st))
    
    for iid in selected_iids:
        if player_tree.exists(iid):
            player_tree.selection_set(iid)
            player_tree.focus(iid)

    root.after(1000, refresh_table)

refresh_table(); process_queues(); root.mainloop()