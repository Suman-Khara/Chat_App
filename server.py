import asyncio
 
# write a message to a stream writer
async def write_message(writer, msg_bytes):
    writer.write(msg_bytes)
    await writer.drain()
 
# read messages from the queue and transmit them to world chat users only
async def broadcaster():
    global queue
    while True:
        message = await queue.get()
        print(f'Broadcast (World Chat): {message.strip()}')
        msg_bytes = message.encode()
        global ALL_USERS, WORLD_CHAT_USERS
        # Send only to users in world chat
        tasks = [
            asyncio.create_task(write_message(ALL_USERS[user][1], msg_bytes))
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
        menu = "\nChoose an option:\n1. GLOBAL ONLINE\n2. WORLD CHAT\n"
        writer.write(menu.encode())
        await writer.drain()
        
        command_bytes = await reader.readline()
        command = command_bytes.decode().strip()

        if command == "GLOBAL ONLINE":
            online_users = "\nOnline Members:\n" + "\n".join(ALL_USERS.keys()) + "\n"
            writer.write(online_users.encode())
            await writer.drain()
        elif command == "WORLD CHAT":
            # Add user to world chat
            WORLD_CHAT_USERS.add(name)
            await broadcast_message(f'{name} has joined the world chat\n')
            writer.write("You have joined the world chat. Type EXIT to leave.\n".encode())
            await writer.drain()
            await handle_world_chat(name, reader, writer)
        else:
            writer.write("Invalid command. Try again.\n".encode())
            await writer.drain()

# Handle world chat interaction
async def handle_world_chat(name, reader, writer):
    try:
        while True:
            line_bytes = await reader.readline()
            line = line_bytes.decode().strip()

            if line == "EXIT":
                WORLD_CHAT_USERS.remove(name)  # Remove user from world chat
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
    global ALL_USERS
    ALL_USERS[name] = (reader, writer)

    # Show options instead of auto-joining world chat
    await handle_command(name, reader, writer)

    return name
 
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
queue = asyncio.Queue()
asyncio.run(main())
