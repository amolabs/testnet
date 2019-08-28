#!/usr/local/bin/python3

import os
import sys
import glob
import time
import subprocess
import json

import paramiko

SSH_USERNAME = ""
SSH_PRIVKEY_PATH = os.environ["HOME"] + "/.ssh/id_rsa"

CURRENT_PATH = os.getcwd()
NODE_FILE = CURRENT_PATH + "/orchestration/nodes.json"

CONFIG_LOCAL_PATH = CURRENT_PATH + "/orchestration/config/"
CONFIG_REMOTE_PATH = "/home/%s/orchestration/" % (SSH_USERNAME)

SLEEP_TIME = 3 

def main():
    # get data from json file:
    with open(NODE_FILE) as file:
        data = json.load(file)

    # prepare ssh module
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # get nodes info from json data
    nodes = data["nodes"]

    target = "val1"
    setup(ssh, nodes, target, "''")

    peer = nodes[target]["node_id"] + "@" + nodes[target]["ip_addr"] + ":26656"
    del nodes[target]

    target = "seed"
    setup(ssh, nodes, target, peer)

    peer = nodes[target]["node_id"] + "@" + nodes[target]["ip_addr"] + ":26656"
    del nodes[target]

    for target in list(nodes.keys()):        
        setup(ssh, nodes, target, peer)
    
def setup(ssh, nodes, target, peer):
    try:
        print("[%s] setting up node" % (target))

        target_ip = nodes[target]["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip)
        print("[%s] connected to %s" % (target, target_ip))

        print("[%s] scp script files" % (target))
        for f in os.listdir(CURRENT_PATH):
            local_path = os.path.join(CURRENT_PATH, f)
            remote_path = os.path.join(CONFIG_REMOTE_PATH, f)
            
            if os.path.isfile(local_path) and local_path.endswith(".sh"):
                ssh_transfer(ssh, local_path, remote_path)
                command = "sudo chmod +x %s" % (remote_path)
                ssh_exec(ssh, command)

        print("[%s] scp general config files" % (target))
        for f in os.listdir(CONFIG_LOCAL_PATH):
            local_path = os.path.join(CONFIG_LOCAL_PATH, f)
            remote_path = os.path.join(CONFIG_REMOTE_PATH, f)

            if os.path.isfile(local_path): ssh_transfer(ssh, local_path, remote_path)

        print("[%s] scp private config files" % (target))
        for f in os.listdir(CONFIG_LOCAL_PATH + target + "/"):
            local_path = os.path.join(CONFIG_LOCAL_PATH + target + "/", f)
            remote_path = os.path.join(CONFIG_REMOTE_PATH, f)

            if os.path.isfile(local_path): ssh_transfer(ssh, local_path, remote_path)

        print("[%s] execute 'setup.sh' script" % (target))
        command = "cd %s; sudo ./setup.sh /orchestration/%s/ %s %s %s" % (CONFIG_REMOTE_PATH,
                                                                          target, target,
                                                                          target_ip, peer)
        ssh_exec(ssh, command)

    except Exception as err:
        print("[%s] %s" % (target, err))
        ssh.close()
        exit(1)

    finally:
        ssh.close()

def ssh_transfer(ssh, local_path, remote_path):
    try:
        t = ssh.open_sftp()
        t.put(local_path, remote_path)
    except Exception as err:
        print(err)
        ssh.close()
        exit(1)

def ssh_exec(ssh, command):
    try:
        stdin, stdout, stderr = ssh.exec_command(command)

        if stdout.channel.recv_exit_status(): 
            raise Exception("couldn't execute: %s" % (command))

    except Exception as err:
        print(err)
        exit(1)

def ssh_connect(ssh, hostname):
    try:
        ssh.connect(hostname, username=SSH_USERNAME, key_filename=SSH_PRIVKEY_PATH)
    except Exception as error:
        print(error)
        exit(1)

    return ssh

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 %s <ssh_username> <ssh_privkey_path>(optional)" % (sys.argv[0]))
        exit(1)
    
    if len(sys.argv) == 3:
        SSH_PRIVKEY_PATH = sys.argv[2]

    SSH_USERNAME = sys.argv[1]
    CONFIG_REMOTE_PATH = "/home/%s/orchestration/" % (SSH_USERNAME)
    
    main()
