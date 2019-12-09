# AMO Testnet
Testnet genesis.json files and launch scripts.

## Using setup.sh
This script helps to prepare data directory and configuration files.

### Usage
```bash
./setup.sh <data_root> <moniker> <peers>
```

### Information
- `<data_root>` is where the node's data files and configuration files reside.
  Name any direcotry where the user has `write` permission, and the script will
  create or reuse the directory. It is recommended to use the directory with
  the form of `<path_to_data_dir>/<node_name>`. `run.sh` will deal with this
  later.
- `<moniker>` is a human-readable name for this node. Feel free to choose any
  descriptive name.
- `<peers>` is a list of peers separated by comma. A peer address has form of
  `node_id@ip_address_or_hostname:p2p_port`. `node_id` can be obtained by
  querying `http://ip_address_or_hostname:26657/status` using tools such as
  `curl`. Default `p2p_port` is 26656.

Recent AMO testnet has a seed node running on 172.104.88.12. It is recommended
to use this node if you have no knowledge of any other nodes. 

## Using run.sh
This script will launch a docker container from the official `amolabs/amod`
(default: latest) image. The user can specify a specific version of the image 
by giving `image_version` as an argument option. The docker container's name 
will be set as described in the explanation of `<data_root>`.

### Usage
```bash
./run.sh <data_root> [image_version]
```
Since the script will run the container in detached mode, you can see the logs
from the container as follows:
```bash
docker logs -f <node_name>
```

## Using orchestration/do.py
This python script provides the following features required for orchestrating
AMO nodes in parallel mode.

### Features
- `init`: boot nodes, distribute coins and stake them 
- `up`: just boot nodes
- `down`: shutdown nodes
- `restart`: process sequentially `down` -> `up`
- `setup`: copy config files located under `orchestration/data/<target>` to each target node
- `reset`: process sequentially `down` -> `setup` -> `init`
- `exec`: execute user input command in nodes
- `scp`: copy files from local path to remote path in ssh

### Install required packages
```bash
pip3 install -r requirements.txt
```

### Usage
```bash
./orchestration/do.py { init | up | down | restart | setup | reset | exec | scp }
```

### Requiries
To use the script, the preset data are required as follows:
- `$HOME/.ssh/id_rsa`: ssh private key 
- `orchestration/config.json`: containing node info
- `orchestration/data/<target>/node_key.json`: tendermint node key
- `orchestration/data/<target>/priv_validator_key.json`: tendermint validator key

The tendermint related keys located under `data` folder should correspond with
the ones written in the `orchestation/config.json`.
