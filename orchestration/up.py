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

SLEEP_TIME = 3 

AMOCLI = "amocli"
OPT = "--json"
GENESIS = "genesis"
ONEAMO = 1000000000000000000

def main():
    # get data from json file:
    with open(NODE_FILE) as file:
        data = json.load(file)

    # prepare ssh module
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # get nodes info from json data
    nodes = data["nodes"]
    rpc_addr = nodes["val1"]["ip_addr"] + ":26657"

    target = "val1"
    amount = 100 * ONEAMO

    bootstrap(ssh, nodes, target)
    
    print("faucet to %s: %d" % (target, amount)) 
    transfer(rpc_addr, GENESIS, nodes[target]["amo_addr"], amount) 

    print("stake for %s: %d" % (target, amount)) 
    stake(rpc_addr, target, nodes[target]["validator_pubkey"], amount)

    del nodes[target]

    target = "seed"
    bootstrap(ssh, nodes, target)

    del nodes[target]

    for target in list(nodes.keys()):        
        bootstrap(ssh, nodes, target)

    for target in list(nodes.keys()):
        print("faucet to %s: %d" % (target, amount))
        transfer(rpc_addr, GENESIS, nodes[target]["amo_addr"], amount) 

    for target in list(nodes.keys()):
        print("stake for %s: %d" % (target, amount))
        stake(rpc_addr, target, nodes[target]["validator_pubkey"], amount) 

def amocli_exec(tx_type, rpc_addr, key_to_use, dest_addr, amount):
    try:
        command = "%s %s --rpc %s tx --user %s %s %s %d" % (AMOCLI, OPT, rpc_addr, key_to_use, 
                                                            tx_type, dest_addr, amount)
    
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
       
        if err: raise Exception(err)

    except Exception as err:
        print(err)
        exit(1)

    return out

def stake(rpc_addr, key_to_use, target_addr, amount):
    result = amocli_exec("stake", rpc_addr, key_to_use, target_addr, amount)
    print(result.decode('utf-8'))

def transfer(rpc_addr, from_key, to_addr, amount):
    result = amocli_exec("transfer", rpc_addr, from_key, to_addr, amount)
    print(result.decode('utf-8'))

def bootstrap(ssh, nodes, target):
    try:
        print("[%s] bootstrap node" % (target))
        
        target_ip = nodes[target]["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip)
        print("[%s] connected to %s" % (target, target_ip))

        print("[%s] execute 'run.sh' script" % (target))
        command = "sudo ./orchestration/run.sh /orchestration/%s/" % (target)
        ssh_exec(ssh, command)
    
        print("[%s] sleep %d seconds" % (target, SLEEP_TIME))
        time.sleep(SLEEP_TIME)

        print("[%s] check status" % (target))
        command = "sudo docker inspect " + target
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
    print("connecting to " + hostname)
    try:
        ssh.connect(hostname, username=SSH_USERNAME, key_filename=SSH_PRIVKEY_PATH)
    except Exception as error:
        print(error)
        exit(1)

    print("connected to " + hostname) 
    return ssh

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 %s <ssh_username> <ssh_privkey_path>(optional)" % (sys.argv[0]))
        exit(1)
    
    if len(sys.argv) == 3:
        SSH_PRIVKEY_PATH = sys.argv[2]

    SSH_USERNAME = sys.argv[1]

    main()
