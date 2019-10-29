#!/bin/bash

# default setting
MODE="testnet"
EXTADDR=""

usage() {
	echo "syntax: $0 [options] <data_root> <moniker> [peers] "
	echo "options:"
	echo "  -l  setup local testnet"
	echo "  -e  external address"
	echo "  -h  print usage"
}

while getopts "le:h" arg; do
	case $arg in
		l)
			MODE="local"
			;;
		e)  
			EXTADDR=$OPTARG
			;;
		h | *)
			usage
			exit
			;;
	esac
done

shift $(( OPTIND - 1 ))

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
echo "extaddr   = $EXTADDR"

rm -rf $DATAROOT

mkdir -p $DATAROOT/amo
mkdir -p $DATAROOT/tendermint/config
mkdir -p $DATAROOT/tendermint/data
cp -f config.toml.in config.toml
sed -e s/@moniker@/$MONIKER/ -i.tmp config.toml
sed -e s/@peers@/$PEERS/ -i.tmp config.toml
if [ ! -z "$EXTADDR" ]; then
	sed -e s/@external@/tcp:\\/\\/$EXTADDR:26656/ -i.tmp config.toml
else
	sed -e s/@external@// -i.tmp config.toml
fi

mv -f config.toml $DATAROOT/tendermint/config/
if [ $MODE == "testnet" ]; then
	cp -f genesis.json $DATAROOT/tendermint/config/
else
	# this will create a new arbitrary genesis file
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
docker run --rm -v $DATAROOT/tendermint:/tendermint:Z amolabs/amod /usr/bin/tendermint --home /tendermint show_node_id 2> /dev/null

rm -f *.tmp

