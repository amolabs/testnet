#!/usr/local/bin/python3

import os
import sys
import time
import subprocess
import json

import paramiko

SSH_PRIVKEY_PATH = os.environ["HOME"] + "/.ssh/id_rsa"

CURRENT_PATH = os.getcwd()
NODE_FILE = CURRENT_PATH + "/orchestration/nodes.json"
CONFIG_LOCAL_PATH = CURRENT_PATH + "/orchestration/config/"

SLEEP_TIME = 3 

AMOCLI = "amocli"
OPT = "--json"
GENESIS = "genesis"
ONEAMO = 1000000000000000000

def up(ssh, nodes, only_boot):
    nodes = {**nodes}
    rpc_addr = nodes["val1"]["ip_addr"] + ":26657"

    target = "val1"
    amount = 100 * ONEAMO

    bootstrap(ssh, nodes, target)
    
    if not only_boot:
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

    if not only_boot:
        for target in list(nodes.keys()):
            print("faucet to %s: %d" % (target, amount))
            transfer(rpc_addr, GENESIS, nodes[target]["amo_addr"], amount) 

        for target in list(nodes.keys()):
            print("stake for %s: %d" % (target, amount))
            stake(rpc_addr, target, nodes[target]["validator_pubkey"], amount) 

    nodes.clear()

def down(ssh, nodes):
    nodes = {**nodes}

    target = "val1"
    docker_stop(ssh, nodes, target)
    del nodes[target]

    target = "seed"
    docker_stop(ssh, nodes, target)
    del nodes[target]

    for target in list(nodes.keys()):        
        docker_stop(ssh, nodes, target)
    
    nodes.clear()

def setup(ssh, nodes):
    nodes = {**nodes}

    target = "val1"
    setup_node(ssh, nodes, target, "''")

    peer = nodes[target]["node_id"] + "@" + nodes[target]["ip_addr"] + ":26656"
    del nodes[target]

    target = "seed"
    setup_node(ssh, nodes, target, peer)

    peer = nodes[target]["node_id"] + "@" + nodes[target]["ip_addr"] + ":26656"
    del nodes[target]

    for target in list(nodes.keys()):        
        setup_node(ssh, nodes, target, peer)

    nodes.clear()

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
        ssh = ssh_connect(ssh, target_ip, nodes[target]["username"])
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

def docker_stop(ssh, nodes, target):
    try:
        target_ip = nodes[target]["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip, nodes[target]["username"])
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

def setup_node(ssh, nodes, target, peer):
    try:
        print("[%s] setting up node" % (target))

        target_ip = nodes[target]["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip, nodes[target]["username"])
        print("[%s] connected to %s" % (target, target_ip))

        command = "pwd"
        config_remote_path = ssh_exec(ssh, command)[0].strip() + "/orchestration/"

        print("[%s] scp script files" % (target))
        for f in os.listdir(CURRENT_PATH):
            local_path = os.path.join(CURRENT_PATH, f)
            remote_path = os.path.join(config_remote_path, f)
            
            if os.path.isfile(local_path) and local_path.endswith(".sh"):
                ssh_transfer(ssh, local_path, remote_path)
                command = "sudo chmod +x %s" % (remote_path)
                ssh_exec(ssh, command)

        print("[%s] scp general config files" % (target))
        for f in os.listdir(CONFIG_LOCAL_PATH):
            local_path = os.path.join(CONFIG_LOCAL_PATH, f)
            remote_path = os.path.join(config_remote_path, f)

            if os.path.isfile(local_path): ssh_transfer(ssh, local_path, remote_path)

        print("[%s] scp private config files" % (target))
        for f in os.listdir(CONFIG_LOCAL_PATH + target + "/"):
            local_path = os.path.join(CONFIG_LOCAL_PATH + target + "/", f)
            remote_path = os.path.join(config_remote_path, f)

            if os.path.isfile(local_path): ssh_transfer(ssh, local_path, remote_path)

        print("[%s] execute 'setup.sh' script" % (target))
        command = "cd %s; sudo ./setup.sh /orchestration/%s/ %s %s %s" % (config_remote_path,
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

    return stdout.readlines()

def ssh_connect(ssh, hostname, username):
    try:
        ssh.connect(hostname, username=username, key_filename=SSH_PRIVKEY_PATH)
    except Exception as error:
        print(error)
        exit(1)

    return ssh

def main():
    # get data from json file:
    with open(NODE_FILE) as file:
        data = json.load(file)

    # prepare ssh module
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # get nodes info from json data
    nodes = data["nodes"]

    cmd = sys.argv[1]
    
    if cmd == "init":
        up(ssh, nodes, only_boot=False)
    elif cmd == "up": 
        up(ssh, nodes, only_boot=True)
    elif cmd == "down": 
        down(ssh, nodes)
    elif cmd == "setup":
        setup(ssh, nodes)
    elif cmd == "reset":
        down(ssh, nodes)
        setup(ssh, nodes)
        up(ssh, nodes, only_boot=False)
    else:
        usage()

def usage():
    print("Usage: python3 %s { init | up | down | setup | reset }" % (sys.argv[0]))

if __name__ == "__main__":
    if len(sys.argv) != 2: 
        usage()
        exit(1)

    main()
