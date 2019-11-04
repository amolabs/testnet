#!/usr/local/bin/python3

import os
import sys
import time
import subprocess
import json

import paramiko

CURRENT_PATH = os.getcwd()
ORCH_PATH = CURRENT_PATH + "/orchestration"
CONFIG_PATH =  ORCH_PATH + "/config.json"
DATA_PATH = ORCH_PATH + "/data"
DEFAULT_KEY_PATH = os.environ["HOME"] + "/.ssh/id_rsa"

SLEEP_TIME = 0.5 

IMAGE_NAME = "amolabs/amod"

AMOCLICMD = "amocli"
AMOCLIOPT = "--json"
AMOCLI = AMOCLICMD + ' ' + AMOCLIOPT

ONEAMO = 1000000000000000000

def up(ssh, amo, nodes, only_boot):
    nodes = {**nodes}
    rpc_addr = nodes["val1"]["ip_addr"] + ":26657"
    image_version = amo["image_version"] 
    amount = 100 * ONEAMO

    target = "val1"
    node = nodes[target]
    bootstrap(ssh, node, image_version, target)
    if not only_boot:
        valkey_path = os.path.join(DATA_PATH, target,
                'priv_validator_key.json')
        val_pubkey = None
        if os.path.isfile(valkey_path):
            with open(valkey_path) as file:
                valkey = json.load(file)
                val_pubkey = valkey['pub_key']['value']
        if val_pubkey is None:
            return
        print("faucet to %s: %d" % (target, amount)) 
        transfer(rpc_addr, amo["faucet_user"], node["amo_addr"], amount) 
        print("stake for %s: %d" % (target, amount)) 
        stake(rpc_addr, target, val_pubkey, amount)
    del nodes[target]

    target = "seed"
    if target in nodes:
        node = nodes[target]
        bootstrap(ssh, node, image_version, target)
        del nodes[target]

    for target, node in nodes.items():        
        bootstrap(ssh, node, image_version, target)
        if not only_boot:
            valkey_path = os.path.join(DATA_PATH, target,
                    'priv_validator_key.json')
            val_pubkey = None
            if os.path.isfile(valkey_path):
                with open(valkey_path) as file:
                    valkey = json.load(file)
                    val_pubkey = valkey['pub_key']['value']
            if val_pubkey is None:
                return
            print("faucet to %s: %d" % (target, amount))
            transfer(rpc_addr, amo["faucet_user"], node["amo_addr"], amount) 
            print("stake for %s: %d" % (target, amount))
            stake(rpc_addr, target, val_pubkey, amount) 

    nodes.clear()

def down(ssh, nodes):
    nodes = {**nodes}

    target = "val1"
    docker_stop(ssh, nodes[target], target)
    del nodes[target]

    target = "seed"
    if target in nodes:
        docker_stop(ssh, nodes[target], target)
        del nodes[target]

    for target in list(nodes.keys()):        
        docker_stop(ssh, nodes[target], target)
    
    nodes.clear()

def setup(ssh, amo, nodes):
    nodes = {**nodes}

    target = "val1"
    node = nodes[target]
    node_id = setup_node(ssh, amo, node, target, "''")
    peer = node_id + "@" + node["ip_addr"] + ":" + str(node["p2p_port"])
    #print(peer)
    del nodes[target] # exclude from loop

    target = "seed"
    if target in nodes:
        node = nodes[target]
        node_id = setup_node(ssh, amo, node, target, peer)
        peer = node_id + "@" + node["ip_addr"] + ":" + str(node["p2p_port"])
        del nodes[target] # exclude from loop

    for target in list(nodes.keys()):        
        node = nodes[target]
        setup_node(ssh, amo, node, target, peer)

    nodes.clear()

def amocli_exec(tx_type, rpc_addr, username, dest_addr, amount):
    try:
        command = "%s --rpc %s tx --user %s %s %s %d" % \
                (AMOCLI, rpc_addr, username, tx_type, dest_addr, amount)
    
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
       
        if err: raise Exception(err)

    except Exception as err:
        print(err)
        exit(1)

    return out

def stake(rpc_addr, username, val_pubkey, amount):
    result = amocli_exec("stake", rpc_addr, username, val_pubkey, amount)
    print(result.decode('utf-8'))

def transfer(rpc_addr, username, to_addr, amount):
    result = amocli_exec("transfer", rpc_addr, username, to_addr, amount)
    print(result.decode('utf-8'))

def bootstrap(ssh, node, image_version, target):
    try:
        print("[%s] bootstrap node" % (target))
        
        target_ip = node["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip, node["username"])
        print("[%s] connected to %s" % (target, target_ip))

        print("[%s] execute 'run.sh' script" % (target))
        command = "sudo ./orchestration/run.sh /testnet/%s/ %s" % (target, image_version)
        ssh_exec(ssh, command)
    
        print("[%s] check docker status" % (target))
        command = "sudo docker inspect " + target
        ssh_exec(ssh, command)

        print("[%s] check rpc connection" % (target), end = ' ', flush = True)
        err = None
        command = "curl --fail --silent localhost:26657"
        while err is None or err == 52:
            print(".", end = ' ', flush = True)
            result, err = ssh_exec(ssh, command)
            time.sleep(SLEEP_TIME)

        print("FULLY UP!")

    except Exception as err:
        print("[%s] %s" % (target, err))
        ssh.close()
        exit(1)

    finally:
        ssh.close()

def docker_stop(ssh, node, target):
    try:
        target_ip = node["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip, node["username"])
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

def setup_node(ssh, amo, node, target, peer):
    node_id = ''
    try:
        print("[%s] setting up node" % (target))

        target_ip = node["ip_addr"]

        print("[%s] connecting to %s" % (target, target_ip))
        ssh = ssh_connect(ssh, target_ip, node["username"])
        print("[%s] connected to %s" % (target, target_ip))

        command = "pwd"
        output, _ = ssh_exec(ssh, command)
        orch_remote_path = output[0].strip() + "/orchestration"
        print("[%s] creating remote path: %s" % (target, orch_remote_path))
        command = "mkdir -p %s" % orch_remote_path
        ssh_exec(ssh, command)

        docker_image = IMAGE_NAME + ":" + amo["image_version"]

        print("[%s] docker pull %s" % (target, docker_image))
        command = "sudo docker pull %s" % (docker_image)
        ssh_exec(ssh, command)

        print("[%s] scp general config files" % (target))
        for f in os.listdir(CURRENT_PATH):
            local_path = os.path.join(CURRENT_PATH, f)
            remote_path = os.path.join(orch_remote_path, f)
            
            if os.path.isfile(local_path) and \
               (local_path.endswith(".sh") or \
                local_path.endswith(".in") or \
                local_path.endswith(".json")):

                ssh_transfer(ssh, local_path, remote_path)
                
                if local_path.endswith(".sh"):
                    command = "sudo chmod +x %s" % (remote_path)
                    ssh_exec(ssh, command)

        print("[%s] scp private config files" % (target))
        for f in os.listdir(DATA_PATH + "/" + target + "/"):
            local_path = os.path.join(DATA_PATH + "/" + target + "/", f)
            remote_path = os.path.join(orch_remote_path, f)

            if os.path.isfile(local_path):
                ssh_transfer(ssh, local_path, remote_path)

        genesis_file = amo["genesis_file"]

        print("[%s] scp %s file" % (target, genesis_file))
        local_path = os.path.join(CURRENT_PATH, genesis_file)
        remote_path = os.path.join(orch_remote_path, "genesis.json")
        ssh_transfer(ssh, local_path, remote_path)

        print("[%s] execute 'setup.sh' script" % (target))
        command = "cd %s; sudo ./setup.sh -e %s /testnet/%s/ %s %s" % \
                (orch_remote_path, target_ip, target, target, peer)
        output, _ = ssh_exec(ssh, command)
        node_id = output[len(output)-1].strip()

    except Exception as err:
        print("[%s] %s" % (target, err))
        ssh.close()
        exit(1)

    finally:
        ssh.close()
        return node_id
        
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

    except Exception as err:
        print(err)
        exit(1)

    return stdout.readlines(), stdout.channel.recv_exit_status()

def ssh_connect(ssh, hostname, username):
    try:
        ssh.connect(hostname, username=username,
                key_filename=config['client']['ssh_key_path'])
    except Exception as error:
        print(error)
        exit(1)

    return ssh

def main():
    global config
    # read config from json file:
    with open(CONFIG_PATH) as file:
        config = json.load(file)

    if 'client' in config:
        client = config['client']
        if 'ssh_key_path' in client:
            if client['ssh_key_path'][0] is not '/':
                client['ssh_key_path'] = os.environ['HOME'] + '/' \
                        + client['ssh_key_path']
        else:
            client['ssh_key_path'] = DEFAULT_KEY_PATH
    else:
        client = {"ssh_key_path": DEFAULT_KEY_PATH}

    config["client"] = client

    nodes = config["nodes"]
    amo = config["amo"]

    # prepare ssh module
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    cmd = sys.argv[1]
    
    if cmd == "init":
        up(ssh, amo, nodes, only_boot=False)
    elif cmd == "up": 
        up(ssh, amo, nodes, only_boot=True)
    elif cmd == "down": 
        down(ssh, nodes)
    elif cmd == "setup":
        setup(ssh, amo, nodes)
    elif cmd == "reset":
        down(ssh, nodes)
        setup(ssh, amo, nodes)
        up(ssh, amo, nodes, only_boot=False)
    else:
        usage()

def usage():
    print("Usage: python3 %s { init | up | down | setup | reset }" % (sys.argv[0]))

if __name__ == "__main__":
    if len(sys.argv) != 2: 
        usage()
        exit(1)

    main()
