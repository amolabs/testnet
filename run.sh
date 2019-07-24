#!/bin/bash

DATAROOT=$1
if [ -z "$DATAROOT" ]; then
	exit
fi
echo "data root = $DATAROOT"
NODE=$(basename $DATAROOT)
if [ -z "$NODE" ]; then
	exit
fi
echo "node name = $NODE"

docker run -itd --rm -v $DATAROOT/tendermint:/tendermint:Z -v $DATAROOT/amo:/amo:Z --name "$NODE" -p 26656-26657:26656-26657 amolabs/amod
