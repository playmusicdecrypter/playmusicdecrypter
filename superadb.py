#!/usr/bin/env python2

# superadb - adb commands with root privileges (works even if `adb root` is disabled)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

__version__ = "1.0"

import os, sys, subprocess, optparse, threading, SocketServer


class ReusableTCPServer(SocketServer.TCPServer):
    """SocketServer.TCPServer with SO_REUSEADDR option set to True"""
    allow_reuse_address = True


class CopyServerRequestHandler(SocketServer.StreamRequestHandler):
    """Request handler for CopyServer"""
    def handle(self):
        """Handle request"""
        if self.server.direction == "pull":
            self.handle_pull()
        elif self.server.direction == "push":
            self.handle_push()

    def handle_pull(self):
        """Handle pull request"""
        with open(self.server.local_file, "wb") as f:
            while True:
                data = self.rfile.read(4096)
                if data:
                    f.write(data)
                else:
                    break

    def handle_push(self):
        """Handle push request"""
        with open(self.server.local_file, "rb") as f:
            while True:
                data = f.read(4096)
                if data:
                    self.wfile.write(data)
                else:
                    break


class CopyServer(object):
    """Server for copying data from/to remote location"""
    def __init__(self, hostname="localhost", port=23456):
        self.hostname = hostname
        self.port = port
        self.server = None
        self.server_thread = None
        self.is_alive = False

    def start(self, direction, local_file):
        """Start server for sending or receiving data from/to local file, direction must be 'push' or 'pull'"""
        if self.is_alive:
            raise RuntimeError("CopyServer is already running!")

        self.is_alive = True

        self.server = ReusableTCPServer((self.hostname, self.port), CopyServerRequestHandler)
        self.server.direction = direction
        self.server.local_file = local_file

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def pull(self, local_file):
        """Start server for receiving data from remote location to local_file"""
        self.start("pull", local_file)

    def push(self, local_file):
        """Start server for sending data from local_file to remote location"""
        self.start("push", local_file)

    def stop(self):
        """Stop running server"""
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        self.is_alive = False


class SuperAdb(object):
    """Adb commands with root privileges (works even if `adb root` is disabled)"""
    def __init__(self, port=23456, executable="adb"):
        self.port = port
        self.executable = executable
        self.copyserver = CopyServer(port=self.port)

        # Start adb server and test if device is connected
        self.start_server()
        if not self.is_connected():
            raise RuntimeError("Device is not connected!")

        # Setup reverse port forwarding
        self.start_reverse_forwarding()

    def adb(self, *cmd):
        """Call adb command"""
        return subprocess.call([self.executable] + list(cmd))

    def start_server(self):
        """Start adb server"""
        return self.adb("start-server")

    def start_reverse_forwarding(self):
        """Setup reverse port forwarding"""
        return self.adb("reverse", "tcp:{}".format(self.port), "tcp:{}".format(self.port))

    def pull(self, remote_file, local_file=""):
        """Copy remote_file from device to local_file (with root privileges)"""
        if not local_file:
            local_file = os.path.basename(remote_file)
        self.copyserver.pull(local_file)
        retcode = self.adb("shell", "su -c 'nc localhost {} < {}'".format(self.port, remote_file))
        self.copyserver.stop()
        return retcode

    def push(self, local_file, remote_file):
        """Copy local_file to remote_file on device (with root privileges)"""
        self.copyserver.push(local_file)
        retcode = self.adb("shell", "su -c 'nc localhost {} > {}'".format(self.port, remote_file))
        self.copyserver.stop()
        return retcode

    def ls(self, remote_path):
        """List files in remote_path on device (with root privileges)"""
        p = subprocess.Popen([self.executable, "shell", "su -c 'ls {}'".format(remote_path)],
                             stdout=subprocess.PIPE)
        output = [l.strip("\r\n") for l in p.stdout.readlines()]
        retcode = p.wait()
        return output if retcode == 0 else None

    def is_connected(self):
        """Test if device is connected"""
        p = subprocess.Popen([self.executable, "get-state"], stdout=subprocess.PIPE)
        output = p.stdout.read().strip("\r\n")
        retcode = p.wait()
        return True if retcode == 0 and output == "device" else False

    def stop(self):
        """Kill adb server"""
        return self.adb("kill-server")


def main():
    # Parse command line options
    parser = optparse.OptionParser(description="Adb commands with root privileges (works even if `adb root` is disabled)",
                                   usage="usage: %prog [-h] [options] command [arguments]",
                                   version="%prog {}".format(__version__))
    parser.add_option("-a", "--adb", default="adb",
                      help="path to adb executable")
    parser.add_option("-l", "--list", action="store_true",
                      help="list all available commands")
    (options, args) = parser.parse_args()

    if options.list:
        print("Commands:")
        print("  push local_file remote_file   ... copy local_file to remote_file on device")
        print("  pull remote_file [local_file] ... copy remote_file from device to local_file")
        print("  ls remote_path                ... list files in remote_path on device")
        sys.exit(0)

    if len(args) < 1:
        parser.print_help()
        sys.exit(1)

    try:
        adb = SuperAdb(executable=options.adb)
    except RuntimeError:
        print("Device is not connected!")
        sys.exit(1)

    cmd = args[0]
    cmd_args = args[1:]

    if cmd == "push":
        if len(cmd_args) < 2:
            print("Missing command arguments!")
            sys.exit(1)
        adb.push(cmd_args[0], cmd_args[1])
    elif cmd == "pull":
        if len(cmd_args) < 1:
            print("Missing command arguments!")
            sys.exit(1)
        adb.pull(cmd_args[0], cmd_args[1] if len(cmd_args) > 1 else "")
    elif cmd == "ls":
        if len(cmd_args) < 1:
            print("Missing command arguments!")
            sys.exit(1)
        files = adb.ls(cmd_args[0])
        if files:
            for f in files:
                print(f)
    else:
        print("Unknown command!")
        sys.exit(1)


if __name__ == "__main__":
    main()
