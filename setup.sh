#!/bin/bash

# default setting
EXTADDR=""
DOCKER=false
RESET=false

usage() {
    echo "syntax: $0 [options] <data_root> <moniker> [peers] "
    echo "options:"
    echo "  -d  use docker"
    echo "  -r  reset data root"
    echo "  -e  external address"
    echo "  -h  print usage"
}

while getopts "dre:h" arg; do
    case $arg in
        d)
            DOCKER=true
            ;;
        r)  
            RESET=true
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
echo "docker    = $DOCKER"
echo "reset     = $RESET"
echo "extaddr   = $EXTADDR"

# reset DATAROOT
if [ "$RESET" = true ]; then
    rm -rf $DATAROOT
fi

# make sure dir struct
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

# put config.toml into DATAROOT
mv -f config.toml $DATAROOT/amo/config/

# put genesis.json if exists
if [ -f genesis.json ]; then
    cp -f genesis.json $DATAROOT/amo/config/
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

if [ "$DOCKER" = true ]; then
    # init tendermint
    docker run -it --rm -v $DATAROOT/amo:/amo amolabs/amod amod tendermint init

    # show tendermint id
    docker run -it --rm -v $DATAROOT/amo:/amo amolabs/amod amod tendermint show_node_id 2> /dev/null
else
    # prepare amod.service
    cp run.sh /root/amod_run.sh
    cp -f amod.service.in amod.service
    sed -e s#@dataroot@#$DATAROOT/amo# -i.tmp amod.service
    cp amod.service /etc/systemd/system/amod.service

    # enable amod.service
    systemctl enable amod

    # init tendermint
    amod --home $DATAROOT/amo tendermint init

    # show tendermint node id
    amod --home $DATAROOT/amo tendermint show_node_id 2> /dev/null
fi

rm -f *.tmp

