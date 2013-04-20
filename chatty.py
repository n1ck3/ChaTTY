#!/usr/bin/env python

"""
Simple telnet chat server using gevent.

"""

import logging

import gevent
import gevent.server
from gevent.queue import Queue
from gevent import monkey ; monkey.patch_all()

from chatty_conf import config

__author__ = "Niclas helbro"
__version__ = "0.1"

logging.getLogger('').setLevel(logging.DEBUG)


class ChattyServer(object):
    """
    Server class that handles client states and interaction between
    connections.

    """
    def __init__(self):
        self.config = config
        self.connected_users = {}
        self.message_queues = {}

    def new_connection(self, username):
        """
        Register a new connection by username and broadcast the event to
        other users.

        """
        self.connected_users[username] = "Online"
        self.message_queues[username] = gevent.queue.Queue()
        self.send_message(username, "Joined chatty.", message_type="status")

    def end_connection(self, username):
        """
        Unregister a connection by username and broadcast the event to
        other users.

        """
        if username in self.connected_users:
            del(self.connected_users[username])

        if username in self.message_queues:
            del(self.message_queues[username])

        self.send_message(username, "Left chatty.", message_type="status")

    def set_status(self, username, status):
        """
        Set the status of a given user by username.
        Returns `True, success_msg` if successful.
        Returns `False, error_msg` if unsuccessful.

        """
        if username in self.connected_users:
            if status in self.config["STATUS_LIST"]:
                self.connected_users[username] = status
                self.send_message(
                    username,
                    "Updated status to %s." % status,
                    message_type="status"
                )
                return True, "Status updated."

            return False, "Status '%s' is not allowed. Choose one from %s." % (
                status,
                ", ".join(self.config["STATUS_LIST"])
            )
        else:
            return False, "User is not connected."

    def send_message(self, username, message, to_username=None, message_type="public"):
        """
        Sends a private or public message. This is used both for actual chat
        messages as well as broadcasting server status messages.
        Returns `True, success_msg` if successful.
        Returns `False, error_msg` if unsuccessful.

        """
        if to_username:
            # Private message
            message_type = "private"
            if not to_username in self.message_queues:
                return False, "No such user."

            elif username == to_username:
                return False, "You can't send private messages to yourself."
            else:
                self.message_queues[to_username].put_nowait((
                    "[Private message from %s] %s" % (username, message),
                    message_type
                ))
                self.message_queues[username].put_nowait((
                    "[Private message to %s] %s" % (to_username, message),
                    message_type
                ))
                logging.info("[Private message from %s to %s sent] %s" % (
                    username, to_username, message
                ))
                return True, "Private message sent"
        else:
            # Public message
            message = "[Public message from %s] %s" % (username, message)
            for user, queue in self.message_queues.items():
                queue.put_nowait((message, message_type))
            logging.info(message)
            return True, "Prublic message sent"


class ChattyTelnetHandler(object):
    """
    Telnet handler class which handles the interaction between the telnet
    client and the server.

    """
    def __init__(self, chatty_server, socket, address):
        self.config = config
        self.tick = 0.1
        self.chatty_server = chatty_server
        self.socket = socket
        self.address = address
        self.fileobj = self.socket.makefile()
        self.username = None
        self.commands = {
            "help": ("/help", "Print this help message."),
            "list": ("/list", "List connected users."),
            "message": ("/message <username> <message>", "Send private message to a user."),
            "status": ("/status (%s)" % "|".join(self.config["STATUS_LIST"]), "Set your status."),
            "quit": ("/quit", "Quit ChaTTY.")
        }

    def read(self):
        """
        Read input from the telnet client.

        """
        return self.fileobj.readline().replace("\r\n", "")

    def write(self, message, prompt=True, message_type=None):
        """
        Write output to the telnet client.

        """
        # Colorize output.
        if message_type == "status":
            message = "\x1b[34m%s\x1b[0m" % message

        elif message_type == "private":
            message = "\x1b[32m%s\x1b[0m" % message

        elif message_type == "public":
            message = "\x1b[35m%s\x1b[0m" % message

        elif message_type == "info":
            message = "\x1b[33m%s\x1b[0m" % message

        elif message_type == "warning":
            message = "\x1b[33m%s\x1b[0m" % message

        elif message_type == "error":
            message = "\x1b[31m%s\x1b[0m" % message

        if prompt:
            self.fileobj.write("%s\n" % message)
        else:
            self.fileobj.write("%s" % message)

        self.fileobj.flush()

    def set_username(self):
        """
        Called to get and set the client's username.

        """
        while not self.username:
            self.write("Username: ", prompt=False)
            username = self.read()
            username = username.strip().lower().replace(" ", "-")

            if not username:
                logging.info("Client disconnected before setting username")
                return False

            if username in self.chatty_server.connected_users:
                self.write("Error: A user with that username is already connected. Try again...", message_type="error")
                continue

            # Still here? Ok then, set the username then!
            self.username = username

    def session_start(self):
        """
        Called after the user successfully logs in.

        """
        self.chatty_server.new_connection(self.username)

        self.write("\nWelcome %s! Get chatty.\n" % self.username, message_type="info")

        self.print_help()
        self.write("\n")

        self.list_connected_users()
        self.write("\n")

        # Start the listeners
        gevent.spawn(self.message_listener)
        gevent.spawn(self.input_listener)

    def session_end(self):
        """
        Called when the user wants to log off.

        """
        self.chatty_server.end_connection(self.username)
        self.socket.shutdown(gevent.socket.SHUT_RDWR)
        self.socket.close()
        self.socket = None

    def message_listener(self):
        """
        Listen for new messages.

        """
        queue = self.chatty_server.message_queues[self.username]
        while self.socket:
            if not queue.empty():
                message, message_type = queue.get()
                self.write(message, message_type=message_type)
            gevent.sleep(self.tick)

    def input_listener(self):
        """
        Listen for new input from telnet

        """
        while self.socket:
            line = self.read()
            if line:
                if line[0] == "/":
                    # All commands start with a slash.
                    args = line.split(" ")

                    # Grab the command without the leading slash
                    command = args[0][1:]

                    if command == "list" or command == "l":
                        self.list_connected_users()

                    elif command == "message" or command == "m":
                        to_username = args[1]
                        message = " ".join(args[2:])
                        self.send_message(message, to_username=to_username)

                    elif command == "status" or command == "s":
                        status = args[1]
                        self.set_status(status)

                    elif command == "quit" or command == "q":
                        self.session_end()

                    else:
                        self.print_help()

                else:
                    self.send_message(line)

            gevent.sleep(self.tick)

    # Command methods
    def print_help(self):
        """
        Display help message to telnet client.

        """
        self.write("  Usage:", message_type="info")
        for command, command_help in self.commands.items():
            self.write("   %s: %s" % (
                command_help[0], command_help[1]),  message_type="info"
            )
        self.write("   <message>: %s" % "Send a public message to all connected users", message_type="info")

    def list_connected_users(self):
        """
        Display connected users to telnet client.

        """

        connected_users = self.chatty_server.connected_users

        self.write("  CONNECTED USERS:", message_type="status")
        for user, status in connected_users.items():
            self.write("    %s (%s)" % (user, status), message_type="status")

    def set_status(self, status):
        """
        Set status for current user

        """

        success, msg = self.chatty_server.set_status(self.username, status)

        if not success:
            self.write("ERROR: %s" % msg, message_type="error")

    def send_message(self, message, to_username=None):
        """
        Send public chat message

        """
        if message != "":
            success, msg = self.chatty_server.send_message(
                self.username, message, to_username=to_username
            )

            if not success:
                self.write("ERROR: %s" % msg, message_type="error")


def connection_handler(socket, address):

    handler = ChattyTelnetHandler(chatty_server, socket, address)

    # O HAI.
    handler.write("\nWelcome to ChaTTY.\n")

    # Make sure we set a (unique) username:
    handler.set_username()

    if handler.username:
        handler.session_start()
    else:
        handler.session_end()


if __name__ == '__main__':
    chatty_server = ChattyServer()

    gevent_server = gevent.server.StreamServer(
        (config["HOST"], int(config["PORT"])),
        connection_handler
    )

    logging.info("Started ChaTTY server on port %s.  (Ctrl-C to stop)" % (
        config["PORT"]
    ))

    try:
        gevent_server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shut down.")
