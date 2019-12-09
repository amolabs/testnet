#!/usr/local/bin/python3

import os
import sys
import time
import subprocess
import json

from pssh.clients import ParallelSSHClient
from gevent import joinall

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

#########################
# Support Parallel Mode #
#########################
# * non parallel        #
#   - all_faucet_stake  #
# * half parallel       #
#   - all_setup         #
#     + val1            #
#     + seed(dep)       #
#     + val...(dep)     #
# * full parallel       #
#   - all_up            #
#   - all_down          #
#########################

def all_up(ssh, amo, nodes):
    b_time = time.time()

    nodes = {**nodes}
    image_version = amo["image_version"] 
    
    # seed, val... : parallel
    print("bootstrap nodes")
    bootstrap(ssh, nodes, image_version)

    print()
    nodes.clear()

    return time.time() - b_time

def all_down(ssh, nodes):
    b_time = time.time()

    nodes = {**nodes}

    # seed, val... : parallel
    print("stop nodes")
    docker_stop(ssh, nodes)
    
    print()
    nodes.clear()

    return time.time() - b_time

def all_faucet_stake(ssh, amo, nodes):
    b_time = time.time()

    nodes = {**nodes}
   
    rpc_addr = nodes["val1"]["ip_addr"] + ":26657"
    amount = 100 * ONEAMO

    if "seed" in nodes:
        del nodes["seed"]

    # val... : non-parallel
    for target, node in nodes.items():
        valkey_path = os.path.join(DATA_PATH, target, 'priv_validator_key.json')
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

    print()
    nodes.clear()

    return time.time() - b_time

def all_setup(ssh, amo, nodes):
    b_time = time.time()

    nodes = {**nodes}

    print("setup nodes")
        
    # transfer to seed, val... : parallel
    transfer_config(ssh, amo, nodes) 

    # val1 : non-parallel
    target = "val1"
    ssh.hosts = [nodes[target]["ip_addr"]]
    nodes_tmp = {target:nodes[target]}

    node_id = setup_node(ssh, amo, nodes_tmp, "''")
    peer = node_id + "@" + nodes[target]["ip_addr"] + ":" + str(amo["p2p_port"])

    del nodes[target] # exclude from loop

    # seed : non-parallel
    target = "seed"
    if target in nodes:
        ssh.hosts = [nodes[target]["ip_addr"]]
        nodes_tmp = {target:nodes[target]}

        node_id = setup_node(ssh, amo, nodes_tmp, peer)
        peer = node_id + "@" + nodes[target]["ip_addr"] + ":" + str(amo["p2p_port"])
        del nodes[target] # exclude from loop

    # val... : parallel
    ssh.hosts = [h["ip_addr"] for h in nodes.values()]

    setup_node(ssh, amo, nodes, peer)

    print()
    nodes.clear()

    return time.time() - b_time

def all_exec(ssh, exec_cmd):
    b_time = time.time()

    # seed, val... : parallel
    ssh_exec(ssh, exec_cmd, wait=True, echo=True)

    return time.time() - b_time

def all_scp(ssh, local_path, remote_path):
    b_time = time.time()

    # seed, val... : parallel
    greenlets = ssh_transfer(ssh, local_path, remote_path)
    joinall(greenlets) # wait until transfer is done

    return time.time() - b_time

def amocli_exec(tx_type, rpc_addr, username, dest_addr, amount):
    try:
        command = "%s --rpc %s tx --broadcast=commit --user %s %s %s %d" % \
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

def bootstrap(ssh, nodes, image_version):
    try:
        host_args = get_host_args(ssh.hosts, nodes) 

        print("execute 'run.sh' script", end='', flush=True)
        command = "./orchestration/run.sh /testnet/%(target)s/ " + image_version
        ssh_exec(ssh, command, host_args=host_args, wait=True)
        print(" - DONE")

        print("check docker status", end='', flush=True)
        comman = "docker inspect %(target)s"
        ssh_exec(ssh, command, host_args=host_args, wait=True)
        print(" - DONE")

        print("check rpc connection ", end='', flush=True)
        check_status(ssh)

    except Exception as err:
        print(err)
        exit(1)

def docker_stop(ssh, nodes):
    try:
        host_args = get_host_args(ssh.hosts, nodes) 

        print("stop docker container:", ssh.hosts, end='', flush=True)
        command = "docker stop %(target)s"
        ssh_exec(ssh, command, host_args=host_args, wait=True)
        print(" - DONE")

    except Exception as err:
        print(err)
        exit(1)

def transfer_config(ssh, amo, nodes):
    try:
        orch_remote_path = "orchestration/"
        docker_image = IMAGE_NAME + ":" + amo["image_version"]
       
        genesis_source_path = amo["genesis_file"]
        genesis_dest_path = os.path.join(CURRENT_PATH, "genesis.json")

        command = "ln -sf %s %s" % (genesis_source_path, genesis_dest_path)
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()

        if err: raise Exception(err)

        command = "docker pull %s" % (docker_image)
        print(command + ":", ssh.hosts, end='', flush=True)
        ssh_exec(ssh, command, wait=True)
        print(" - DONE")

        print("prepare config files to transfer:", ssh.hosts, end='', flush=True)
        for f in os.listdir(CURRENT_PATH):
            if not os.path.isfile(os.path.join(CURRENT_PATH, f)):
                continue
            if not f.endswith(".sh") and not f.endswith(".in") and not f.endswith(".json"):
                continue

            for target in nodes.keys():
                from_path = os.path.join(CURRENT_PATH, f)
                to_path = os.path.join(DATA_PATH + "/" + target + "/", f)

                command = "cp %s %s" % (from_path, to_path)
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
                out, err = proc.communicate()
       
                if err: raise Exception(err)

        print(" - DONE")

        hosts_bk = ssh.hosts

        greenlets = []

        print("transfer config files to nodes:", ssh.hosts, end='', flush=True)
        for target in nodes.keys():
            ssh.hosts = [nodes[target]["ip_addr"]]

            local_path = os.path.join(DATA_PATH, target)
            remote_path = orch_remote_path
           
            greenlet = ssh_transfer(ssh, local_path, remote_path)[0]
            greenlets.append(greenlet)

        joinall(greenlets, raise_error=True)
        print(" - DONE")

        ssh.hosts = hosts_bk 

        print("set execution permission on script files:", ssh.hosts, end='', flush=True)
        command = "chmod +x ./orchestration/*.sh"
        ssh_exec(ssh, command, wait=True)
        print(" - DONE")
    
    except Exception as err:
        print(err)
        exit(1)

def setup_node(ssh, amo, nodes, peer):
    node_id = ''
    try:
        orch_remote_path = "orchestration"
        host_args = get_host_args(ssh.hosts, nodes) 

        print("execute 'setup.sh' script:", ssh.hosts, end='', flush=True)
        command = "cd " + orch_remote_path + "; ./setup.sh -e %(ip)s /testnet/%(target)s/ %(target)s " + peer
        output = ssh_exec(ssh, command, host_args=host_args, wait=True)
        print(" - DONE")

        if len(ssh.hosts) == 1:
            output = list(output[ssh.hosts[0]].stdout)
            node_id = output[len(output)-1].strip()

    except Exception as err:
        print(err)
        exit(1)

    finally:
        return node_id
        
def check_status(ssh):
    ok_num = 0

    while ok_num < len(ssh.hosts):
        ok_num = 0
        
        command = "curl localhost:26657/status"
        output = ssh_exec(ssh, command)
        
        for host_output in output.values():
            host_output = list(host_output.stdout)
            if len(host_output) > 0:
                ok_num += 1

        time.sleep(SLEEP_TIME)
        print(".", end = '', flush = True)
    
    print(" - FULLY UP!")

def get_host_args(hosts, nodes):
    host_args = []
    for host in hosts:
        target = None
        for node, config in nodes.items():
            if config["ip_addr"] == host:
                target = node

        if target == None:
            continue

        host_args.append({"target": target, "ip": host})

    return host_args

def ssh_transfer(ssh, local_path, remote_path):
    try:
        # return greenlets
        return ssh.scp_send(local_path, remote_path, recurse=True)
    except Exception as err:
        print(err)
        exit(1)

def ssh_exec(ssh, command, host_args=None, wait=False, echo=False):
    try:
        output = ssh.run_command(
                command, 
                host_args=host_args, 
                sudo=True, 
                stop_on_errors=True)

        if wait == True: 
            ssh.join(output) # wait until all nodes' job end

        if echo == True:
            for host, host_output in output.items():
                for line in host_output.stdout:
                    print("host=%s, command=%s, output=%s" % (host, command, line))

        return output

    except Exception as err:
        print(err)
        exit(1)

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

    nodes = config["nodes"]
    amo = config["amo"]

    # prepare ssh module
    hosts = [h["ip_addr"] for h in nodes.values()]
    ssh = ParallelSSHClient(
            hosts=hosts, 
            user=client["ssh_username"],
            pkey=client["ssh_key_path"],
            allow_agent=False)

    cmd = sys.argv[1]
   
    exec_time = 0

    if cmd == "init":
        exec_time += all_up(ssh, amo, nodes)
        exec_time += all_faucet_stake(ssh, amo, nodes)
    elif cmd == "up": 
        exec_time += all_up(ssh, amo, nodes)
    elif cmd == "down": 
        exec_time += all_down(ssh, nodes)
    elif cmd == "restart":
        exec_time += all_down(ssh, nodes)
        ssh.hosts = hosts # reset
        exec_time += all_up(ssh, amo, nodes)
    elif cmd == "setup":
        exec_time += all_setup(ssh, amo, nodes)
    elif cmd == "reset":
        exec_time += all_down(ssh, nodes)
        ssh.hosts = hosts # reset
        exec_time += all_setup(ssh, amo, nodes)
        ssh.hosts = hosts # reset
        exec_time += all_up(ssh, amo, nodes)
        ssh.hosts = hosts # reset
        exec_time += all_faucet_stake(ssh, amo, nodes)
    elif cmd == "scp":
        if len(sys.argv) == 4:
           exec_time += all_scp(ssh, sys.argv[2], sys.argv[3]) 
        else:
            usage()
    elif cmd == "exec":
        # TODO: use getopt
        if len(sys.argv) >= 3:
            exec_time += all_exec(ssh, sys.argv[2])
        else:
            usage()
    else:
        usage()

    print("execution time:", exec_time, "s")

def usage():
    print("Usage: python3 %s { init | up | down | restart | setup | reset | exec | scp }" % (sys.argv[0]))

if __name__ == "__main__":
    if len(sys.argv) < 2: 
        usage()
        exit(1)

    main()
