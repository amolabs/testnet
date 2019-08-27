#!/bin/bash

# default setting
MODE="testnet"

usage() {
	echo "syntax: $0 [options] <data_root> <moniker> [peers]"
	echo "options:"
	echo "  -l  setup local testnet"
	echo "  -h  print usage"
}

while getopts "hl" arg; do
	case $arg in
		l)
			MODE="local"
			shift
			;;
		h | *)
			usage
			exit
			;;
	esac
done

DATAROOT=$1
MONIKER=$2
PEERS=$3

OS=$(uname)

if [ -z "$DATAROOT" -o -z "$MONIKER" ]; then
	usage
	exit
fi

echo "data root = $DATAROOT"
echo "moniker   = $MONIKER"
echo "peers     = $PEERS"
if [ "$OS" == "Linux" ]; then
	iface=$(route -n | grep '^0.0.0.0' | awk '{print $8}')
	extaddr=$(ip -f inet a show dev $iface | grep '\<inet\>' | head -1 | awk '{print $2}' | awk -F'/' '{print $1}')
# TODO
#elif [ "$OS" == "Darwin" ]; then
fi
echo "extaddr = $extaddr"

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
if [ $MODE == "testnet" ]; then
	cp -f testnet_190823/genesis.json $DATAROOT/tendermint/config/
else
	rm -f $DATAROOT/tendermint/config/genesis.json
fi

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

