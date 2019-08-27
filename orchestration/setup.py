#!/usr/local/bin/python3

import os
import glob
import time
import subprocess
import json

import paramiko

SSH_USERNAME = "monsieur.ahn"
SSH_PRIVKEY_PATH = os.environ["HOME"] + "/.ssh/id_rsa"

NODE_FILE = "nodes.json"

NODE_LOCAL_PATH = "./config/"
NODE_REMOTE_PATH = "/home/%s/orchestration/" % (SSH_USERNAME)

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
    print("setting up %s node" % (target))
    setup(ssh, nodes, target, "''")

    peer = nodes[target]["node_id"] + "@" + nodes[target]["ip_addr"] + ":26656"
    del nodes[target]

    target = "seed"
    print("setting up %s node" % (target))
    setup(ssh, nodes, target, peer)

    peer = nodes[target]["node_id"] + "@" + nodes[target]["ip_addr"] + ":26656"
    del nodes[target]

    for target in list(nodes.keys()):        
        print("setting up %s node" % (target))
        setup(ssh, nodes, target, peer)
    
def setup(ssh, nodes, target, peer):
    try:
        target_ip = nodes[target]["ip_addr"]
        ssh = ssh_connect(ssh, target_ip)

        print("[%s] scp config files" % (target))
        for f in os.listdir(NODE_LOCAL_PATH):
            local_path = os.path.join(NODE_LOCAL_PATH, f)
            if os.path.isfile(local_path):
                remote_path = os.path.join(NODE_REMOTE_PATH, f)
                ssh_transfer(ssh, local_path, remote_path)
                if remote_path.endswith(".sh"):
                    command = "sudo chmod +x %s" % (remote_path)
                    stdin, stdout, stderr = ssh_exec(ssh, command)

        for f in os.listdir(NODE_LOCAL_PATH + target + "/"):
            local_path = os.path.join(NODE_LOCAL_PATH + target + "/", f)
            if os.path.isfile(local_path):
                remote_path = os.path.join(NODE_REMOTE_PATH, f)
                ssh_transfer(ssh, local_path, remote_path)

        print("[%s] rmdir" % (target)) 
        command = "cd ./orchestration; sudo ./reset.sh /orchestration/%s" % (target)
        stdin, stdout, stderr = ssh_exec(ssh, command)

        print("[%s] execute 'setup.sh' script" % (target))
        command = "cd ./orchestration; sudo ./setup.sh /orchestration/%s %s %s %s" % (target, 
                                                                                target,
                                                                                peer,
                                                                                target_ip)
        stdin, stdout, stderr = ssh_exec(ssh, command)

    except Exception as err:
        print("[%s] %s" % (target, err))
        ssh.close()
        exit(1)

    finally:
        ssh.close()

def ssh_mkdir(ssh, path):
    try:
        t = ssh.open_sftp()
        t.mkdir(path)
    except Exception as err:
        print(err)
        ssh.close()
        exit(1)

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
        return ssh.exec_command(command)
    except Exception as error:
        print(error)
        ssh.close()
        exit(1)

def ssh_connect(ssh, hostname):
    print("connecting to " + hostname)
    try:
        ssh.connect(hostname, username=SSH_USERNAME, key_filename=SSH_PRIVKEY_PATH)
    except Exception as error:
        print(error)
        exit(1)

    print("connected to " + hostname) 
    return ssh

if __name__ == "__main__":
    main()
