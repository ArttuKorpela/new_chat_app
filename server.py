import socket
import threading
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client.python_chat  # Use your database name
users_collection = db.users  # Use your collection name

host = "127.0.0.1"  # localhost
port = 55555  # free port

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Internet protocol and TCP
server.bind((host, port))  # Bind the chosen IP-address and port
server.listen()  # Listen for incoming requests

clients = []  # Lists for connections
client_to_username = {}
username_to_client = {}


def add_user(username, channel, private_chat_user):
    user_document = {
        "username": username,
        "channel": channel,
        "private": private_chat_user
    }
    users_collection.insert_one(user_document)


def get_channel(username):
    user = users_collection.find_one({"username": username})
    if user:
        return user.get("channel")
    else:
        return None


def get_user(username):
    user = users_collection.find_one({"username": username})
    if user:
        return user.get("username")
    else:
        return None


def get_private(username):
    user = users_collection.find_one({"username": username})
    if user:
        return user.get("private")
    else:
        return None


def update_private_chat_status(username, partner_username=None):
    result = users_collection.update_one(
        {"username": username},
        {"$set": {"private": partner_username}}
    )

    if result.modified_count > 0:
        print(f"Updated private chat status for '{username}'.")
    else:
        print(f"Failed to update private chat status for '{username}'. User may not exist.")


def update_user_channel(username, new_channel):
    result = users_collection.update_one(
        {"username": username},
        {"$set": {"channel": new_channel}}
    )

    if result.modified_count > 0:
        return (f"User '{username}' has moved to channel '{new_channel}'.")
    else:
        return (f"Failed to move '{username}' to channel '{new_channel}'. User may not exist.")


def delete_user(username):
    # Perform the delete operation
    result = users_collection.delete_one({"username": username})

    # Check if the delete operation was successful
    if result.deleted_count > 0:
        return (f"User '{username}' was deleted from the database.")
    else:
        return (f"User '{username}' could not be found or deleted.")


# Function to sen a message to all currently connected users
def send_to_all(message, skip_user, channel_index):
    print("Sending a message")
    if skip_user is not None:
        skip_user_name = client_to_username[skip_user]
        print(skip_user_name)
        test_channel = get_channel(skip_user_name)
        print(test_channel)
    else:
        test_channel = 0

    if test_channel == -1:
        attempt_name = get_private(client_to_username[skip_user])
        if attempt_name is None:
            return  # Failure to find opposing user
        attempt = username_to_client[attempt_name]

        if message.decode().split(' ')[1] == "-quit":
            attempt.send("Conversation ended. Back to: all".encode())
            skip_user.send("Conversation ended. Back to: all".encode())
            # first_private_dictionary.pop(skip_user, None)  # None to not cause errors
            # second_private_dictionary.pop(skip_user, None)  # None to not cause errors
            # first_private_dictionary.pop(attempt, None)
            # second_private_dictionary.pop(attempt, None)

            try:
                update_user_channel(attempt_name, 0)
                update_user_channel(skip_user_name, 0)
                update_private_chat_status(attempt_name)
                update_private_chat_status(skip_user_name)
            except:
                attempt.send("Error in updating the database".encode())
                skip_user.send("Error in updating the database".encode())

            # a_index = clients.index(attempt)
            # current_channel[a_index] = 0
            # current_channel[clients.index(skip_user)] = 0

        attempt.send(message)
        return

    for client in clients:
        if client != skip_user:
            recieving_index = get_channel(client_to_username[client])
            if recieving_index == channel_index:
                client.send(message)


def handle(client):
    while True:
        try:
            current_channel_index = get_channel(client_to_username[client])
            # Whenever the server receives a message it broadcasts it to all
            message = client.recv(1024)
            message_array = message.decode().split(' ')
            s_message = message_array[1]
            print(s_message)
            if s_message == "-channel":
                channel_change(client)
            elif s_message == "-private":
                print("private")
                request_username = message_array[2]
                try:
                    # i_user = names.index(request_username)
                    user = get_user(request_username)
                    if user is not None:
                        private_messages(client, username_to_client[user])
                except ValueError:
                    client.send("   No such user exists".encode())
            elif s_message == "-close":
                close_connection(client)
            elif s_message == "-disconnect":
                close_connection(client)
                return
            else:
                send_to_all(message, client, current_channel_index)
        except:
            # If an issue occurs the user is removed and connection closed
            print(f"Connection closed with {client_to_username[client]}")
            close_connection(client)
            break



def receive():
    while True:
        new_client, address = server.accept()
        print(f"Connection from {address}")

        new_client.send('NAME'.encode())
        name = new_client.recv(1024).decode()
        # DATABASE
        add_user(name, 0, None)
        client_to_username[new_client] = name
        username_to_client[name] = new_client

        clients.append(new_client)

        send_to_all(f"{name} joined the server".encode(), None, 0)
        new_client.send("Connected".encode())

        thread = threading.Thread(target=handle, args=(new_client,))
        thread.start()


def close_connection(client):
    delete_name = client_to_username[client]
    delete_user(delete_name)
    del client_to_username[client]
    del username_to_client[delete_name]

    clients.remove(client)
    client.close()

    send_to_all((f"{delete_name} left the chat".encode()), None, 0)


def channel_change(client):
    # Define a dictionary mapping channel indices to names
    channels = {
        0: "All",
        1: "Gamers",
        2: "Robots",
        3: "Other idk"
    }

    # Send the channel selection prompt to the client
    channel_prompt = "Choose a channel by typing its number\n"
    for index, name in channels.items():
        channel_prompt += f"   {index}) {name}\n"
    client.send(channel_prompt.encode())

    # Receive the channel selection from the client
    try:
        channel_index = int(client.recv(1024).decode().split(' ')[1])
        # Validate the channel selection and update the client's current channel
        if channel_index in channels:
            try:
                message = update_user_channel(client_to_username[client], channel_index)
                client.send(message.encode())
            except:
                client.send("Error in saving to database".encode())
            ##index = clients.index(client)
            ##current_channel[
            ##  index] = channel_index  #  current_channel is a list tracking each client's current channel
            client.send(f"Channel: {channels[channel_index]}".encode())
        else:
            raise ValueError
    except ValueError:
        client.send("Choose a valid number corresponding to a channel".encode())


def private_messages(requesting_client, accepting_client):
    r_name = client_to_username[requesting_client]
    a_name = client_to_username[accepting_client]

    print(r_name)
    print(a_name)

    r_channel = get_channel(r_name)
    a_channel = get_channel(a_name)

    # r_index = clients.index(requesting_client)
    # _index = clients.index(accepting_client)

    # The user can't ask for a private chat while in one or ask another user if they are in one
    if r_channel == -1:
        requesting_client.send("    Exit the current private chat to request another".encode())
        return
    if a_channel == -1:
        requesting_client.send(f"    {a_name} is currently chatting with someone else".encode())
        return

    accepting_client.send(f"  Join a privare chat with {r_name}?\n"
                          f"    Type 'yes' to accept and 'no' to decline".encode())
    response = accepting_client.recv(1024).decode()
    if response.split(' ')[1] == "yes":

        try:
            update_user_channel(r_name, -1)
            update_user_channel(a_name, -1)
            update_private_chat_status(r_name, a_name)
            update_private_chat_status(a_name, r_name)
        except:
            requesting_client.send("Error in updating database".encode())
            accepting_client.send("Error in updating database".encode())

        # first_private_dictionary[requesting_client] = accepting_client
        # second_private_dictionary[accepting_client] = requesting_client

        # current_channel[a_index] = -1
        # current_channel[r_index] = -1

        requesting_client.send(f"   Staring a private conversation with {a_name}".encode())
        accepting_client.send(f"   Staring a private conversation with {r_name}".encode())
    else:
        requesting_client.send(f"   {a_name} declined your request to chat".encode())


receive()
