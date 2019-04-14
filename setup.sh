#!/bin/bash

DATAROOT=$1
MONIKER=$2
SEEDS=$3

echo "data root = $DATAROOT"
echo "moniker = $MONIKER"
echo "seeds = $SEEDS"

if [ $# != 3 ]; then
	echo "syntax: setup.sh <data_root> <moniker> <seeds_string>"
	exit
fi

#### amod0
mkdir -p $DATAROOT/amod0/amo
mkdir -p $DATAROOT/amod0/tendermint/config
cp -f config.toml.in config.toml
sed -e s/@moniker@/$MONIKER/ -i.tmp config.toml
sed -e s/@seeds@/$SEEDS/ -i.tmp config.toml

mv -f config.toml $DATAROOT/amod0/tendermint/config/
cp -f testnet_190415/genesis.json $DATAROOT/amod0/tendermint/config/

docker run -it --rm -v $DATAROOT/amod0/tendermint:/tendermint:Z amolabs/amod /usr/bin/tendermint --home /tendermint init
ID=$(docker run -it --rm -v $DATAROOT/amod0/tendermint:/tendermint:Z amolabs/amod /usr/bin/tendermint --home /tendermint show_node_id)
ID=${ID//}

#### amod1
mkdir -p $DATAROOT/amod1/amo
mkdir -p $DATAROOT/amod1/tendermint/config
cp -f config.toml.in config.toml
sed -e s/@moniker@/$MONIKER"_sub"/ -i.tmp config.toml
if [ -z "$SEEDS" ]; then
	SEEDS=$ID@192.167.10.2:26656
else
	SEEDS=$SEEDS,$ID@192.167.10.2:26656
fi
sed -e s/@seeds@/$SEEDS/ -i.tmp config.toml

mv -f config.toml $DATAROOT/amod1/tendermint/config/config.toml
cp -f testnet_190415/genesis.json $DATAROOT/amod1/tendermint/config/

#### docker-compose.yml
cp -f docker-compose.yml.in docker-compose.yml
DATAROOTSUB=${DATAROOT//\//\\/}
sed -e s/@dataroot@/$DATAROOTSUB/ -i.tmp docker-compose.yml
sed -e s/@moniker@/$MONIKER/ -i.tmp docker-compose.yml

rm -f *.tmp

