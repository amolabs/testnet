#!/bin/bash

DATAROOT=$1

echo "data root = $DATAROOT"

docker run -it --rm -v $DATAROOT/tendermint:/tendermint:Z -v $DATAROOT/amo:/amo:Z amolabs/amod
