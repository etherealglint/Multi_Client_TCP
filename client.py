import socket
import threading
import time

server_ip = "127.0.0.1"
server_port = 5000

client_files = "client_files/"
received_files = "received_files/"

ready_event = threading.Event()
ready_file_event = threading.Event()

def receive_messages(socket):
    buffer = bytearray()
    while True:
        try:
            data = socket.recv(4096)
            if not data:
                print("\nDisconnected from server.")
                break
            buffer += data
            while b"\n" in buffer:
                index = buffer.index(b"\n")
                line = bytes(buffer[:index])
                del buffer[:index + 1]
                message = line.decode()

                if message == "READY":
                    ready_event.set()

                elif message == "READY_FILE":
                    ready_file_event.set()

                elif message.startswith("FILE "):
                    parts = message.split()
                    if len(parts) != 3:
                        print("\nInvalid file message from server.")
                        continue
                    filename = parts[1]
                    try:
                        filesize = int(parts[2])
                    except ValueError:
                        print("\nInvalid file size.")
                        continue

                    receive_file(
                        socket,
                        filename,
                        filesize,
                        buffer
                    )

                    # receive_file may consume bytes
                    # from the socket directly.
                    # buffer = b""

                elif message.startswith("FILE_FROM "):
                    parts = message.split()
                    if len(parts) != 4:
                        print("\nInvalid FILE_FROM message.")
                        continue
                    sender = parts[1]
                    filename = parts[2]
                    try:
                        filesize = int(parts[3])
                    except ValueError:
                        print("\nInvalid file size.")
                        continue
                    print(
                        f"\nReceiving {filename} from {sender}..."
                    )
                    receive_file(socket,filename,filesize,buffer)
                    # buffer = b""
                elif message.startswith("BENCH_FILE "):
                    parts = message.split()
                    if len(parts) != 3:
                        print("\nInvalid benchmark file message.")
                        continue
                    filename = parts[1]
                    filesize = int(parts[2])
                    receive_file(socket, filename, filesize, buffer)
                    socket.sendall(b"FILE_DONE\n")
                elif message=="PONG":
                    pass
                else:
                    print(f"\nSERVER: {message}")
                    print("> ",end="",flush=True)
        except Exception as e:
            print("\nReceiver error:",e)
            break


def receive_file(socket,filename,filesize,buffer):
    filepath = received_files + filename
    try:
        file = open(filepath,"wb")
    except Exception as e:
        print("\nCould not create file:",e)
        return
    remaining = filesize

    try:
        while len(buffer)>0 and remaining>0:
            amount = min(len(buffer),remaining)
            file.write(buffer[:amount])
            del buffer[:amount]
            remaining =remaining-amount
            # buffer = buffer[amount:]

        while remaining > 0:
            data = socket.recv(min(4096, remaining))
            if not data:
                print("\nConnection lost during file transfer.")
                file.close()
                return
            file.write(data)
            remaining =remaining-len(data)
        file.close()
        print(f"\nFile received: {filename}")
        print(f"Saved to: {filepath}")
        print("> ",end="",flush=True)
    except Exception as e:
        file.close()
        print("\n File receive error:",e)

def upload_file(filename):
    filepath = client_files + filename
    try:
        file = open(
            filepath,
            "rb"
        )
    except FileNotFoundError:
        print(
            f"File not found: {filepath}"
        )
        return

    file.seek(0, 2)
    filesize = file.tell()
    file.seek(0)
    print(
        f"Uploading {filename} ({filesize} bytes)..."
    )

    ready_event.clear()
    ready_file_event.clear()

    client.sendall(
        f"UPLOAD {filename}\n".encode()
    )
    ready_event.wait()
    client.sendall(
        f"SIZE {filesize}\n".encode()
    )
    ready_file_event.wait()
    while True:
        data = file.read(4096)
        if not data:
            break
        client.sendall(data)
    file.close()
    print(
        "File uploaded successfully."
    )
client = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)
client.connect(
    (
        server_ip,
        server_port
    )
)
print("Connected to server.")


data = client.recv(1024)
print(data.decode().strip())
username = input("Username: ")
password = input("Password: ")
login_message = (f"LOGIN {username} {password}\n")
client.sendall(login_message.encode())

client_files = "client_files/" + username + "/"
received_files = "received_files/" + username + "/"

response = client.recv(1024).decode().strip()
print("Server:",response)

if not response.startswith("OK"):
    client.close()
    exit()


receiver = threading.Thread(
    target=receive_messages,
    args=(client,),
    daemon=True
)
receiver.start()

while True:
    command = input("> ")
    if not command:
        continue
    parts = command.split()
    command_name = parts[0].upper()
    if command_name == "UPLOAD":
        if len(parts) != 2:
            print("Usage: UPLOAD <filename>")
            continue
        filename = parts[1]
        upload_file(filename)
    elif command_name=="PING":
        start=time.perf_counter()
        client.sendall(b"PING\n")
        while True:
            data=client.recv(1024).decode().strip()
            if data=="PONG":
                break
        end=time.perf_counter()
        rtt=(end-start)*1000
        print(f"RTT: {rtt:.3f} ms")
    else:
        client.sendall(
            (command + "\n").encode()
        )
    if command_name == "LOGOUT":
        break

client.close()
print("Client closed.")
