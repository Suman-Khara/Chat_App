import asyncio
 
# write a message to a stream writer
async def write_message(writer, message):
    writer.write(message.encode())
    await writer.drain()
 
# read messages from the queue and transmit them to world chat users only
async def broadcaster():
    global queue
    while True:
        message = await queue.get()
        print(f'Broadcast (World Chat): {message.strip()}')
        global ALL_USERS, WORLD_CHAT_USERS
        # Send only to users in world chat
        tasks = [
            asyncio.create_task(write_message(ALL_USERS[user][1], message))
            for user in WORLD_CHAT_USERS if user in ALL_USERS
        ]
        _ = await asyncio.wait(tasks)

# send a message to all connected users in world chat
async def broadcast_message(message):
    global queue
    await queue.put(message)

# handle user commands
async def handle_command(name, reader, writer):
    while True:
        menu = "\nChoose an option:\n1. GLOBAL ONLINE\n2. WORLD CHAT\n3. PERSONAL CHAT\n"
        writer.write(menu.encode())
        await writer.drain()
        
        command_bytes = await reader.readline()
        command = command_bytes.decode().strip()

        if command == "GLOBAL ONLINE":
            await send_online_users(writer)
        elif command == "WORLD CHAT":
            await handle_world_chat(name, reader, writer)
        elif command == "PERSONAL CHAT":
            await handle_personal_chat(name, reader, writer)
        else:
            writer.write("Invalid command. Try again.\n".encode())
            await writer.drain()

async def send_online_users(writer):
    """Sends the list of online users with their status (busy or available)."""
    online_users = "\nOnline Members:\n"

    for user in ALL_USERS.keys():
        if user in WORLD_CHAT_USERS:
            status = " (busy - world chat)"
        elif user in PRIVATE_CHAT_USERS:
            status = " (busy - private chat)"
        else:
            status = ""  # Available users have no status

        online_users += f"{user}{status}\n"

    writer.write(online_users.encode())
    await writer.drain()

# Handle world chat interaction
async def handle_world_chat(name, reader, writer):
    # Add user to world chat
    WORLD_CHAT_USERS.add(name)
    await broadcast_message(f'{name} has joined the world chat\n')
    writer.write("You have joined the world chat. Type EXIT to leave.\n".encode())
    await writer.drain()
    try:
        while True:
            line_bytes = await reader.readline()
            line = line_bytes.decode().strip()

            if line == "EXIT":
                WORLD_CHAT_USERS.remove(name)  # Remove user from world chat
                await broadcast_message(f'{name} has left the world chat\n')
                writer.write("You have left the world chat.\n".encode())
                await writer.drain()
                break  # Return to main menu

            await broadcast_message(f'{name}: {line}\n')
    except:
        pass  # Handle disconnects gracefully

# connect a user
async def connect_user(reader, writer):
    writer.write('Asyncio Chat Server\n'.encode())
    writer.write('Enter your name:\n'.encode())
    await writer.drain()

    name_bytes = await reader.readline()
    name = name_bytes.decode().strip()
    #global ALL_USERS
    if name in ALL_USERS:
        writer.write('Username already taken. Try again.\n'.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        return None
    
    ALL_USERS[name] = (reader, writer)    
    # Show options instead of auto-joining world chat
    await handle_command(name, reader, writer)
    return name

async def handle_personal_chat(name, reader, writer):
    await write_message(writer, "Enter username to chat with:\n> ")
    target_name_bytes = await reader.readline()
    target_name = target_name_bytes.decode().strip()

    # Validate target user
    if target_name not in ALL_USERS:
        await write_message(writer, "User not found.\n> ")
        return

    if target_name == name:
        await write_message(writer, "You cannot chat with yourself.\n> ")
        return

    if target_name in WORLD_CHAT_USERS:
        await write_message(writer, f"{target_name} is in world chat.\n> ")
        return
    
    if target_name in PRIVATE_CHAT_USERS:
        await write_message(writer, f"{target_name} is in a private chat.\n> ")
        return

    target_writer = ALL_USERS[target_name][1]

    #global PRIVATE_CHAT_USERS

    # Mark both users as busy
    PRIVATE_CHAT_USERS.add(name)
    PRIVATE_CHAT_USERS.add(target_name)

    # Ask target user for permission
    await write_message(target_writer, f"{name} wants to start a private chat with you. Type 'YES' to accept or 'NO' to decline.\n> ")
    
    target_reader = ALL_USERS[target_name][0]
    response_bytes = await target_reader.readline()
    response = response_bytes.decode().strip().upper()

    if response != "YES":
        await write_message(writer, f"{target_name} declined the chat request.\n> ")
        await write_message(target_writer, "Chat request declined.\n> ")
        PRIVATE_CHAT_USERS.remove(name)
        PRIVATE_CHAT_USERS.remove(target_name)
        return

    # Notify both users
    await write_message(writer, f"You are now chatting with {target_name}. Type EXIT to leave.\n")
    await write_message(target_writer, f"You are now chatting with {name}. Type EXIT to leave.\n")

    try:
        while True:
            msg_bytes = await reader.readline()
            msg = msg_bytes.decode().strip()

            if msg == "EXIT":
                break

            await write_message(target_writer, f"{name}: {msg}\n")
    finally:
        # Remove users from busy status
        PRIVATE_CHAT_USERS.remove(name)
        PRIVATE_CHAT_USERS.remove(target_name)
        await write_message(writer, "Exited private chat.\n> ")
        await write_message(target_writer, f"{name} has left the chat.\n> ")

# disconnect a user
async def disconnect_user(name, writer):
    writer.close()
    await writer.wait_closed()
    global ALL_USERS, WORLD_CHAT_USERS
    del ALL_USERS[name]
    if name in WORLD_CHAT_USERS:
        WORLD_CHAT_USERS.remove(name)  # Remove if they were in world chat
    await broadcast_message(f'{name} has disconnected\n')
 
# handle a chat client
async def handle_chat_client(reader, writer):
    print('Client connecting...')
    name = await connect_user(reader, writer)
    try:
        while True:
            line_bytes = await reader.readline()
            line = line_bytes.decode().strip()
            if line == 'QUIT':
                break
    finally:
        await disconnect_user(name, writer)

# chat server
async def main():
    broadcaster_task = asyncio.create_task(broadcaster())
    host_address, host_port = '127.0.0.1', 8888
    server = await asyncio.start_server(handle_chat_client, host_address, host_port)
    async with server:
        print('Chat Server Running\nWaiting for chat clients...')
        await server.serve_forever()
 
ALL_USERS = {}
WORLD_CHAT_USERS = set()  # Track users in world chat
PRIVATE_CHAT_USERS = set()  # Track users in private chat
queue = asyncio.Queue()
asyncio.run(main())
