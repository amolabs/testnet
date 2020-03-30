# AMO Testnet
Testnet genesis.json files and launch scripts.

## Using setup.sh
This script helps to prepare data directory and configuration files.

### Usage
```bash
./setup.sh <data_root> <moniker> [peers]
```

### Information
- `<data_root>` is where the node's data files and configuration files reside.
  Name any direcotry where the user has `write` permission, and the script will
  create or reuse the directory. It is recommended to use the directory with
  the form of `<path_to_data_dir>/<node_name>`.
- `<moniker>` is a human-readable name for this node. Feel free to choose any
  descriptive name.
- `[peers]` is a list of peers separated by comma. A peer address has form of
  `node_id@ip_address_or_hostname:p2p_port`. `node_id` can be obtained by
  querying `http://ip_address_or_hostname:26657/status` using tools such as
  `curl`. Default `p2p_port` is 26656.

Since this script registers amod as service in `systemctl`, the service can get
controlled with its general commands such as `start`, `stop`, etc. For example,
to start node, simply execute `systemctl start amod`. Recent AMO testnet has a
seed node running on 172.104.88.12. It is recommended to use this node if you
have no knowledge of any other nodes.

## Using upgrade.sh
This script helps to upgrade node's protocol by replacing binary file with the
latest one at the very moment of upgrading protocol.

### Usage
```bash
./upgrade.sh <data_root>
```

### Information
- `<data_root>` is where the script derive node's state related values, such as
  `height` and `last_height`, which are utilized to detect the right moment of
  upgrading protocol along with `upgrade_protocol_height` from node's config
  values.

## Using orchestration/do.py
This python script provides the following features required for orchestrating
AMO nodes in parallel mode.

### Features
- `init`: boot nodes, distribute coins and stake them 
- `up`: just boot nodes
- `down`: shutdown nodes
- `restart`: process sequentially `down` -> `up`
- `setup`: copy config files located under `orchestration/data/<target>` to
  each target node
- `reset`: process sequentially `down` -> `setup` -> `init`
- `upgrade`: upgrade node protocol
- `exec`: execute user input command in nodes
- `scp`: copy files from local path to remote path in ssh

### Install required packages
```bash
pip3 install -r requirements.txt
```

### Usage
```bash
./orchestration/do.py { init | up | down | restart | setup | reset | upgrade | exec | scp }
```

### Requiries
To use the script, the preset data are required as follows:
- `$HOME/.ssh/id_rsa`: ssh private key 
- `orchestration/config.json`: node orchestration info
- `orchestration/data/<target>/node_key.json`: tendermint node key
- `orchestration/data/<target>/priv_validator_key.json`: tendermint validator
  key
- `orchestration/data/<target>/config.toml.in`: tendermint config file

The tendermint related keys located under `data` folder should correspond with
the ones written in the `orchestation/config.json`.
