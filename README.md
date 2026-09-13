# Multi-Client TCP Communication & File Transfer System
A Python-based client-server networking application built using TCP sockets and multithreading.
The project implements a custom application layer protocol supporting authentication, messaging, broadcasting, and file transfer between multiple clients.

# Features
* TCP client-server communication
* Username/password authentication
* Duplicate-login prevention
* Multiple simultaneous clients using server-side threads
* Private messaging
* Broadcast messaging
* Online-user listing
* File upload
* File download
* File transfer between clients
* Custom application-layer protocol
* TCP message framing and file size based transfer

## Requirements

* Python 3.x
* Standard Python libraries:
socket,threading,time

No external Python packages are required.

## Running the Application

# 1. Start the server

Open a terminal in the project directory:

bash
python server.py


The server listens on:
text
0.0.0.0:5000


# 2. Start a client

Open another terminal:

```bash
python client.py
```

Multiple client terminals can be opened to simulate multiple users.

Example users:

```text
Alice
Bob
Charlie
David
Eve
```

The current test password is:

```text
101
```

# Supported Commands

```text
LOGIN <username> <password>
LIST
MSG <username> <message>
BROADCAST <message>
UPLOAD <filename>
DOWNLOAD <filename>
SEND <username> <filename>
PING
LOGOUT
```

# Example

```text
> MSG Bob Hello Bob
> UPLOAD test.txt
> DOWNLOAD test.txt
> SEND Bob test.txt
> LIST
> PING
> LOGOUT
```

## Technical Concepts

This project demonstrates:

* TCP socket programming
* Client-server architecture
* Multithreading
* Application-layer protocol design
* TCP message framing
* Buffered file transfer
* Concurrent client handling
* Synchronization using thread locks
