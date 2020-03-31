#!/usr/local/bin/python3

import os
import sys
import time
import subprocess
import json

from pssh.clients import ParallelSSHClient
from gevent import joinall

CURRENT_PATH = os.getcwd()
ORCH_PATH = os.path.join(CURRENT_PATH,"orchestration")
CONFIG_PATH =  os.path.join(ORCH_PATH, "config.json")
COMMON_DATA_PATH = os.path.join(ORCH_PATH, "common")
DATA_PATH = os.path.join(ORCH_PATH, "data")
DEFAULT_KEY_PATH = os.path.join(os.environ["HOME"], ".ssh", "id_rsa")

ORCH_REMOTE_PATH="orchestration"
DATAROOT_REMOTE_PATH="/testnet"

SLEEP_TIME = 0.5 

RELEASE_URL = "https://github.com/amolabs/amoabci/releases/download"

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
#   - all_upgrade       #
#########################

def all_up(ssh, amo, nodes):
    b_time = time.time()

    nodes = {**nodes}
    
    # seed, val... : parallel
    print("bootstrap nodes")
    bootstrap(ssh, nodes)

    print()
    nodes.clear()

    return time.time() - b_time

def all_down(ssh, nodes):
    b_time = time.time()

    nodes = {**nodes}

    # seed, val... : parallel
    print("stop nodes")
    stop_node(ssh, nodes)
    
    print()
    nodes.clear()

    return time.time() - b_time

def all_upgrade(ssh, nodes, force=False):
    b_time = time.time()

    nodes = {**nodes}

    # seed, val... : parallel
    print("upgrade nodes")
    upgrade_node(ssh, nodes, force)

    print()
    nodes.clear()

    return time.time() - b_time

def all_faucet_stake(ssh, amo, nodes):
    b_time = time.time()

    nodes = {**nodes}

    rpc_addr = nodes["val1"]["ip_addr"] + ":26657"

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
            continue

        amount = node["stake_amount"]

        print("faucet to %s: %s" % (target, amount)) 
        transfer(rpc_addr, amo["faucet_user"], node["amo_addr"], amount) 
        print("stake for %s: %s" % (target, amount)) 
        stake(rpc_addr, target, val_pubkey, amount)

    print()
    nodes.clear()

    return time.time() - b_time

def all_setup(ssh, amo, nodes):
    b_time = time.time()

    nodes = {**nodes}

    print("setup nodes")

    # install on seed, val... : parallel
    if amo["version"] != "":
        install_node(ssh, amo, nodes)
        
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
        command = "%s --rpc %s tx --broadcast=commit --user %s %s %s %s" % \
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

def bootstrap(ssh, nodes):
    try:
        host_args = get_host_args(ssh.hosts, nodes) 

        print("start amod sercive", end='', flush=True)
        command = "systemctl start amod"
        ssh_exec(ssh, command, host_args=host_args, wait=True)
        print(" - DONE")

        print("check rpc connection ", end='', flush=True)
        check_status(ssh)

    except Exception as err:
        print(err)
        exit(1)

def stop_node(ssh, nodes):
    try:
        host_args = get_host_args(ssh.hosts, nodes) 

        print("stop amod service:", ssh.hosts, end='', flush=True)
        command = "systemctl stop amod"
        ssh_exec(ssh, command, host_args=host_args, wait=True)
        print(" - DONE")

    except Exception as err:
        print(err)
        exit(1)

def install_node(ssh, amo, nodes):
    try:
        command = "wget %s -O ./%s" % (get_amod_url(amo["version"]), get_amod_tar(amo["version"]))
        print(command + ":", ssh.hosts, end='', flush=True)
        ssh_exec(ssh, command, wait=True)
        print(" - DONE")

        command = "tar -xzf %s" % (get_amod_tar(amo["version"]))
        print(command + ":", ssh.hosts, end='', flush=True)
        ssh_exec(ssh, command, wait=True)
        print(" - DONE")

        command = "cp -f amod /usr/bin/amod"
        print(command + ":", ssh.hosts, end='', flush=True)
        ssh_exec(ssh, command, wait=True)
        print(" - DONE")

    except Exception as err:
        print(err)
        exit(1)

def upgrade_node(ssh, nodes, force):
    try:
        host_args = get_host_args(ssh.hosts, nodes) 

        print("execute 'upgrade.sh' script:", ssh.hosts, end='', flush=True)
        command = "cd " + ORCH_REMOTE_PATH + "; ./upgrade.sh "
        if force: command += "-f "
        command += DATAROOT_REMOTE_PATH + "/%(target)s"
        ssh_exec(ssh, command, host_args=host_args, wait=True, echo=True)
        print(" - DONE")

    except Exception as err:
        print(err)
        exit(1)

def transfer_config(ssh, amo, nodes):
    try:
        genesis_source_path = amo["genesis_file"]
        genesis_dest_path = os.path.join(CURRENT_PATH, "genesis.json")

        command = "ln -sf %s %s" % (genesis_source_path, genesis_dest_path)
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()

        if err: raise Exception(err)

        print("prepare config files to transfer:", ssh.hosts, end='', flush=True)
        for f in os.listdir(COMMON_DATA_PATH):
            for target in nodes.keys():
                from_path = os.path.join(CURRENT_PATH, f)
                to_path = os.path.join(DATA_PATH, target, f)

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
            remote_path = ORCH_REMOTE_PATH 
           
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
        host_args = get_host_args(ssh.hosts, nodes) 

        print("execute 'setup.sh' script:", ssh.hosts, end='', flush=True)
        command = "cd " + ORCH_REMOTE_PATH + "; " + \
                "./setup.sh -e %(ip)s " + \
                DATAROOT_REMOTE_PATH + "/%(target)s %(target)s " + peer
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

def get_amod_url(version):
    return "%s/v%s/%s" % (RELEASE_URL, version, get_amod_tar(version))

def get_amod_tar(version):
    return "amod-%s-linux-x86_64.tar.gz" % (version)
        
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
                print("host=%s" % host)
                for line in host_output.stdout:
                    print("%s" % line)

                print()

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
    elif cmd == "upgrade":
        exec_time += all_upgrade(ssh, nodes)
    elif cmd == "upgrade_f":
        exec_time += all_upgrade(ssh, nodes, True)
    elif cmd == "exec":
        # TODO: use getopt
        if len(sys.argv) >= 3:
            exec_time += all_exec(ssh, sys.argv[2])
        else:
            usage()
    elif cmd == "scp":
        if len(sys.argv) == 4:
           exec_time += all_scp(ssh, sys.argv[2], sys.argv[3]) 
        else:
            usage()
    else:
        usage()

    print("execution time:", exec_time, "s")

def usage():
    print("Usage: python3 %s { init | up | down | restart | setup | reset | upgrade | exec | scp }" % (sys.argv[0]))

if __name__ == "__main__":
    if len(sys.argv) < 2: 
        usage()
        exit(1)

    main()
