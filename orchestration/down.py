#!/usr/local/bin/python3

import os
import sys
import time
import subprocess
import json

import paramiko

CURRENT_PATH = os.getcwd()
NODE_FILE = CURRENT_PATH + "/orchestration/nodes.json"

SSH_USERNAME = ""
SSH_PRIVKEY_PATH = os.environ["HOME"] + "/.ssh/id_rsa"

SLEEP_TIME = 10 

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
    docker_stop(ssh, nodes, target)
    del nodes[target]

    target = "seed"
    docker_stop(ssh, nodes, target)
    del nodes[target]

    for target in list(nodes.keys()):        
        docker_stop(ssh, nodes, target)
    
def docker_stop(ssh, nodes, target):
    try:
        target_ip = nodes[target]["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip)
        print("[%s] connected to %s" % (target, target_ip))

        print("[%s] stop docker container" % (target))
        command = "sudo docker stop %s" % (target)
        ssh_exec(ssh, command)

    except Exception as err:
        print("[%s] %s" % (target, err))
        ssh.close()
        exit(1)

    finally:
        ssh.close()

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

    main()
