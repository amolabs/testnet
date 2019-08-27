#!/usr/local/bin/python3

import os
import time
import subprocess
import json

import paramiko

NODE_FILE = "nodes.json"

SSH_USERNAME = "monsieur.ahn"
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
    print("killing %s node" % (target))
    docker_stop(ssh, nodes, target)
    del nodes[target]

    target = "seed"
    print("killing %s node" % (target))
    docker_stop(ssh, nodes, target)
    del nodes[target]

    for target in list(nodes.keys()):        
        print("killing %s node" % (target))
        docker_stop(ssh, nodes, target)
    
def docker_stop(ssh, nodes, target):
    try:
        ssh = ssh_connect(ssh, nodes[target]["ip_addr"])
        print("[%s] stop docker container" % (target))
        command = "sudo docker stop %s" % (target)
        ssh_exec(ssh, command)

        #print("[%s] sleep %d seconds" % (target, SLEEP_TIME))
        #time.sleep(SLEEP_TIME)

        #print("[%s] check status" % (target))
        #command = "sudo docker inspect " + target
        #stdin, stdout, stderr = ssh_exec(ssh, command)

        #if not stderr.read(): raise Exception("container is not properly stopped")

    except Exception as err:
        print("[%s] %s" % (target, err))
        ssh.close()
        exit(1)

    finally:
        ssh.close()

def ssh_exec(ssh, command):
    try:
        return ssh.exec_command(command)
    except Exception as error:
        print(error)
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
