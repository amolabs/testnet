#!/bin/bash

DATAROOT=$1
MONIKER=$2
SEEDS=$3

echo "data root = $DATAROOT"
echo "moniker = $MONIKER"
echo "seeds = $SEEDS"

if [ $# != 3 ]; then
	echo "syntax: setup.sh <data_root> <moniker> <seeds>"
	exit
fi

#### amod0
mkdir -p $DATAROOT/amo
mkdir -p $DATAROOT/tendermint/config
mkdir -p $DATAROOT/tendermint/data
cp -f config.toml.in config.toml
sed -e s/@moniker@/$MONIKER/ -i.tmp config.toml
sed -e s/@seeds@/$SEEDS/ -i.tmp config.toml
if [ "$MONIKER" == "seed" ]; then
	sed -e s/seed_mode\.*$/seed_mode\ =\ true/ -i.tmp config.toml
fi

mv -f config.toml $DATAROOT/tendermint/config/
cp -f testnet_190724/genesis.json $DATAROOT/tendermint/config/

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

