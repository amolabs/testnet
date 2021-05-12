#!/bin/bash

# launch 3 validator nodes on local network

ROOT=$(realpath $(dirname $0))
DATAROOT=$ROOT/testdata
NODENUM=3
IMAGE=amolabs/amod:1.7.7
VAL1_NODE_ADDR=c15e92ef47d65f7a071c0344475f0579d4fef7fd

echo "pull docker image"
docker pull $IMAGE

if [ ! -f $ROOT/docker-compose.yml.in ]; then
    echo "docker-compose.yml.in doesn't exist"
    exit
fi
cp -f $ROOT/docker-compose.yml.in $ROOT/docker-compose.yml
sed -e s#__dataroot__#$DATAROOT# -i.tmp docker-compose.yml
sed -e s#__image__#$IMAGE# -i.tmp docker-compose.yml
sed -e s#__val1_node_addr__#$VAL1_NODE_ADDR# -i.tmp docker-compose.yml

rm -rf $DATAROOT

for ((i=1; i<=NODENUM; i++))
do
    mkdir -p $DATAROOT/val$i/amo/config/
    mkdir -p $DATAROOT/val$i/amo/data/
	cp -f $ROOT/config/genesis.json $DATAROOT/val$i/amo/config/
done
cp -f $ROOT/config/priv_validator_key.json $DATAROOT/val1/amo/config/
cp -f $ROOT/config/priv_validator_state.json $DATAROOT/val1/amo/data/
cp -f $ROOT/config/node_key.json $DATAROOT/val1/amo/config/

echo "Execute \`docker-compose up -d\` to run the testnet in detached mode."
echo "Execute \`docker-compose up\` to run the testnet in attached mode."
