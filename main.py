import socket
import threading

ip_address = input("Give an IP address: ")
nickname = input("Choose your nickname: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    print("Connection made")
    client.connect((ip_address, 55555))
except:
    print("Couldn't connect to server")
    exit(1)



def receive():
    while True:

        try:
            message = client.recv(1024).decode()
            if message == "NAME":
                client.send(nickname.encode())
            else:
                print(message)
        except:
            client.close()
            return



def write():
    while True:
        message = input("")
        if message == "-disconnect":
            client.send(message.encode())  # Inform server
            client.close()
            print("Disconnected")
            return
        else:
            message = f"({nickname}) {message}"
            client.send(message.encode())





receiving_thread = threading.Thread(target=receive)
receiving_thread.start()

sending_thread = threading.Thread(target=write)
sending_thread.start()




