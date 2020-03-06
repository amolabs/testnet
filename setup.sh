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
echo "version 	= $VERSION"
echo "peers     = $PEERS"
echo "extaddr   = $EXTADDR"

# reset DATAROOT
rm -rf $DATAROOT
mkdir -p $DATAROOT/amo/config
mkdir -p $DATAROOT/amo/data

# build config.toml
cp -f config.toml.in config.toml
sed -e s/@moniker@/$MONIKER/ -i.tmp config.toml
sed -e s/@peers@/$PEERS/ -i.tmp config.toml
if [ ! -z "$EXTADDR" ]; then
	sed -e s/@external@/tcp:\\/\\/$EXTADDR:26656/ -i.tmp config.toml
else
	sed -e s/@external@// -i.tmp config.toml
fi

# prepare amod.service 
cp run.sh /root/amod_run.sh
sed -e s#@dataroot@#$DATAROOT/amo# -i.tmp amod.service
cp amod.service /etc/systemd/system/amod.service

# enable amod.service
systemctl enable amod

# put config.toml into DATAROOT
mv -f config.toml $DATAROOT/amo/config/
if [ $MODE == "testnet" ]; then
	cp -f genesis.json $DATAROOT/amo/config/
else
	# this will create a new arbitrary genesis file
	rm -f $DATAROOT/amo/config/genesis.json
fi

# put node_key.json, priv_validator_key.json, priv_validator_state.json into DATAROOT
if [ -f node_key.json ]; then
	cp -f node_key.json $DATAROOT/amo/config/
fi
if [ -f priv_validator_key.json ]; then
	cp -f priv_validator_key.json $DATAROOT/amo/config/
fi
if [ ! -f $DATAROOT/amo/data/priv_validator_state.json ]; then
	cp priv_validator_state.json $DATAROOT/amo/data/
fi

# init tendermint
/usr/bin/amod --home $DATAROOT/amo tendermint init

# show tendermint node id
/usr/bin/amod --home $DATAROOT/amo tendermint show_node_id 2> /dev/null

rm -f *.tmp

