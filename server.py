import socket
import threading
import os

host="0.0.0.0"
port=5000

server_files="server_files/" #path name to find the server files hardcoded just for simplicity for now as the client is not going to write the full path of file only the file_name

#dictionary having username and password which will be used for authentication also
#setting everyone's password to 101 for simplicity
users={
    "Alice":"101",
    "Bob":"101",
    "Charlie":"101",
    "David":"101",
    "Eve":"101"
}

clients={}
clients_lock=threading.Lock()

def send_line(sock,msg):
    sock.sendall((msg+"\n").encode())

def receive_line(sock,buffer):
    data=buffer
    while b"\n" not in data:
        chunk=sock.recv(1024)
        if not chunk:
            return None
        data+=chunk
    ind=data.index(b"\n")
    line=bytes(data[:ind])
    del data[:ind+1]
    # line,remaining=data.split(b"\n",1)
    return line.decode()

def receive_exact(sock, size, buffer):
    data = buffer
    while len(data) < size:
        chunk=sock.recv(4096)
        # chunk = sock.recv( min(4096, size - len(data)) )
        if not chunk:
             return None 
        data += chunk 
    d=bytes(data[:size])
    del data[:size]
    return d

def send_file(sock, filename, filepath):
    try:
        file=open(filepath,"rb")
    except FileNotFoundError:
        send_line(sock, "Error File not found")
        return False
    file.seek(0,2)
    filesize=file.tell()
    file.seek(0)

    try:
        with clients_lock:
            header=f"File {filename} {filesize}\n"
            sock.sendall(header.encode())
            while True:
                data=file.read(4096)
                if not data:
                    break
                sock.sendall(data)
        file.close()
        return True
    except Exception:
        file.close()
        return False

def valid_filename(filename):
    if filename=="":
        return False
    if filename=="." or filename=="..":
        return False
    if "/" in filename:
        return False
    if "\\" in filename:
        return False
    return True

def upload_file(client_socket, filename,buffer):
    if not valid_filename(filename):
        send_line(client_socket,"Error invalid filename")
        return
    filepath=server_files+filename
    send_line(client_socket,"READY")
    size_command=receive_line(client_socket,buffer)
    if size_command is None:
        return 
    parts=size_command.split()
    if len(parts)!=2 or parts[0].upper()!="SIZE":
        send_line(client_socket,"Error expected_size")
        return
    try:
        filesize=int(parts[1])
    except ValueError:
        send_line(client_socket,"Errror invalid size")
        return 
    if filesize<0:
        send_line(client_socket,"error invalid size")
        return 
    send_line(client_socket,"READY_FILE")
    file=open(filepath,"wb")
    try:
        remaining=filesize
        while remaining>0:
            chunk_size=min(4096, remaining)
            data=receive_exact(client_socket,chunk_size,buffer)
            if data is None:
                file.close()
                return
            file.write(data)
            remaining=remaining-len(data)
        file.close()
        send_line(client_socket,"OK upload")
        print("file uploaded: ",filename,"(",filesize," bytes)")
    except Exception:
        file.close()
        send_line(client_socket,"Error upload_failed")

def download_file(client_socket, filename):
    if not valid_filename(filename):
        send_line(client_socket,"ERROR INVALID_FILENAME")
        return
    filepath = server_files + filename
    try:
        file = open(filepath, "rb")
    except FileNotFoundError:
        send_line(client_socket,"ERROR FILE_NOT_FOUND")
        return

    file.seek(0, 2)
    filesize = file.tell()
    file.seek(0)
    try:
        send_line(client_socket,f"FILE {filename} {filesize}")
        while True:
            data=file.read(4096)
            if not data:
                break
            client_socket.sendall(data)
        file.close()
        print(
            "File downloaded:",
            filename
        )
    except Exception as e:
        file.close()
        print("Download Error: ", e)

def send_file_to_user(sender, recipient, filename):
    if not valid_filename(filename):
        with clients_lock:
            sender_socket = clients.get(sender)
        if sender_socket:
            send_line(sender_socket,"ERROR INVALID_FILENAME")
        return
    filepath = server_files + filename

    try:
        file = open(filepath, "rb")
        file.close()
    except FileNotFoundError:
        with clients_lock:
            sender_socket = clients.get(sender)
        if sender_socket:
            send_line(sender_socket,"ERROR FILE_NOT_FOUND")
        return
    # file.close()
    # Finding the recipient
    with clients_lock:
        recipient_socket = clients.get(recipient)
        sender_socket = clients.get(sender)

    if recipient_socket is None:
        send_line(sender_socket,"ERROR USER_NOT_FOUND")
        return

    file = open(filepath, "rb")
    file.seek(0, 2)
    filesize = file.tell()
    file.seek(0)
    try:
        send_line(recipient_socket, f"FILE_FROM {sender} {filename} {filesize}")
        while True:
            data=file.read(4096)
            if not data:
                break
            recipient_socket.sendall(data)
        file.close()
        send_line(sender_socket,"OK SEND")
        print(sender,"sent",filename,"to",recipient)
    except Exception:
        file.close()
        send_line(sender_socket,"ERROR: Sending failed")

def login(client_socket,username,password):
    if username not in users:
        send_line(client_socket, "Error Invalid_username")
        return False
    if users[username]!=password:
        send_line(client_socket, "Error Invalid_password")
        return False
    with clients_lock:
        if username in clients:
            send_line(client_socket, "Error User_already_online")
            return False
        clients[username]=client_socket
    send_line(client_socket, "OK LOGIN")
    print(f"{username} logged in.")
    return True

def list_users(client_socket):
    with clients_lock:
        usernames=list(clients.keys())
    send_line(client_socket, f"Users {len(usernames)}")
    for username in usernames:
        send_line(client_socket, username)
    send_line(client_socket, "END")

def broadcast(sender, msg):
    with clients_lock:
        current_clients=list(clients.items())

    for username, sock in current_clients:
        try:
            send_line(sock, f"Broadcast_from {sender} {msg}")
        except Exception:
            pass

def private_msg(sender, recipent, msg):
    with clients_lock:
        recipent_socket=clients.get(recipent)
    if recipent_socket is None:
        return False
    try:
        send_line(recipent_socket, f"From {sender} {msg}")
        return True
    except Exception:
        return False

def handling_client(client_socket, client_address):
    username=None
    buffer=bytearray()
    print(f"Connection from {client_address}")
    try:
        send_line(client_socket, "Welcome")
        login_command=receive_line(client_socket,buffer)
        if login_command is None:
            return 
        parts=login_command.split()
        if len(parts)!=3 or parts[0].upper()!="LOGIN":
            send_line(client_socket, "Error Login required")
            return 
        username=parts[1]
        password=parts[2]
        if not login(client_socket, username, password):
            return 
        while True:
            line=receive_line(client_socket,buffer)
            if line is None:
                break
            print(f"[{username}] {line}")
            parts=line.split(maxsplit=2)
            if len(parts)==0:
                continue
            command=parts[0].upper()
            if command=="LIST":
                list_users(client_socket)
            elif command=="BROADCAST":
                if len(parts)<2:
                    send_line(client_socket, "Error message required")
                    continue
                message=line[len("BROADCAST "):]
                broadcast(username,message)
                send_line(client_socket, "OK BROADCAST")
            elif command=="MSG":
                if len(parts)<3:
                    send_line(client_socket, "Error message format")
                    continue
                recipent=parts[1]
                message=parts[2]
                success=private_msg(username, recipent, message)
                if success:
                    send_line(client_socket, "OK msg")
                else:
                    send_line(client_socket, "Error user not found")
            elif command=="UPLOAD":
                if len(parts)!=2:
                    send_line(client_socket,"Error upload format")
                    continue
                filename=parts[1]
                upload_file(client_socket,filename,buffer)
            elif command=="DOWNLOAD":
                if len(parts)!=2:
                    send_line(client_socket,"Error download format")
                    continue
                filename=parts[1]
                download_file(client_socket,filename)
            elif command=="SEND":
                send_parts=line.split()
                if len(send_parts)!=3:
                    send_line(client_socket,"error send format")
                    continue
                recipent=send_parts[1]
                filename=send_parts[2]
                send_file_to_user(username,recipent,filename)
            elif command=="LOGOUT":
                send_line(client_socket, "OK LOGOUT")
                break
            else:
                send_line(client_socket, "ERROR Unkown_command")
    except Exception as e:
        print(f"Error handling {client_address}: {e}")
    finally:
        if username is not None:
            with clients_lock:
                if clients.get(username)==client_socket:
                    del clients[username]
            print(f"{username} disconnected")
        client_socket.close()


#starting the server
server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) 
server.bind((host,port))
server.listen(10)
print(f"server listening on {host}:{port}")
while True:
    client_socket,client_address=server.accept()
    thread=threading.Thread(
        target=handling_client,
        args=(client_socket,client_address),
        daemon=True
    )
    thread.start()