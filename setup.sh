#!/bin/bash

if [ $# != 3 ]; then
	echo "syntax: setup.sh <data_root> <moniker> <peers>"
	exit
fi

DATAROOT=$1
MONIKER=$2
PEERS=$3

OS=$(uname)

echo "data root = $DATAROOT"
echo "moniker = $MONIKER"
echo "peers = $PEERS"
if [ "$OS" == "Linux" ]; then
	iface=$(route -n | grep '^0.0.0.0' | awk '{print $8}')
	extaddr=$(ip -f inet a show dev $iface | grep '\<inet\>' | head -1 | awk '{print $2}' | awk -F'/' '{print $1}')
# TODO
#elif [ "$OS" == "Darwin" ]; then
fi
echo "extaddr = $extaddr"

#### amod0
mkdir -p $DATAROOT/amo
mkdir -p $DATAROOT/tendermint/config
mkdir -p $DATAROOT/tendermint/data
cp -f config.toml.in config.toml
sed -e s/@moniker@/$MONIKER/ -i.tmp config.toml
sed -e s/@peers@/$PEERS/ -i.tmp config.toml
if [ ! -z "$extaddr" ]; then
	sed -e s/@external@/tcp:\\/\\/$extaddr:26656/ -i.tmp config.toml
else
	sed -e s/@external@// -i.tmp config.toml
fi

mv -f config.toml $DATAROOT/tendermint/config/
cp -f testnet_190823/genesis.json $DATAROOT/tendermint/config/

if [ -f node_key.json ]; then
	cp -f node_key.json $DATAROOT/tendermint/config/
fi
if [ -f priv_validator_key.json ]; then
	cp -f priv_validator_key.json $DATAROOT/tendermint/config/
fi
if [ ! -f $DATAROOT/tendermint/data/priv_validator_state.json ]; then
	cp priv_validator_state.json $DATAROOT/tendermint/data/
fi

docker run -it --rm -v $DATAROOT/tendermint:/tendermint:Z amolabs/amod /usr/bin/tendermint --home /tendermint init
NODEID=$(docker run -it --rm -v $DATAROOT/tendermint:/tendermint:Z amolabs/amod /usr/bin/tendermint --home /tendermint show_node_id)
NODEID=${NODEID//}
echo "node_id = $NODEID"

rm -f *.tmp

