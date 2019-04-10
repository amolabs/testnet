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

mkdir -p $DATAROOT/amod0/amo
mkdir -p $DATAROOT/amod0/tendermint/config
mkdir -p $DATAROOT/amod1/amo
mkdir -p $DATAROOT/amod1/tendermint/config

cp -f config.toml.in config.toml.amod0
sed -e s/@moniker@/$MONIKER"0"/ -i.tmp config.toml.amod0
sed -e s/@seeds@/$SEEDS/ -i.tmp config.toml.amod0

cp -f config.toml.in config.toml.amod1
sed -e s/@moniker@/$MONIKER"1"/ -i.tmp config.toml.amod1
sed -e s/@seeds@/$SEEDS/ -i.tmp config.toml.amod1

cp -f docker-compose.yml.in docker-compose.yml
sed -e s/@dataroot@/$DATAROOT/ -i.tmp docker-compose.yml

mv -f config.toml.amod0 $DATAROOT/amod0/tendermint/config/config.toml
mv -f config.toml.amod1 $DATAROOT/amod1/tendermint/config/config.toml

rm -f *.tmp
