#!/bin/bash

# default setting
DOCKEROPT="-itd --rm"

usage() {
	echo "syntax: $0 [options] <data_root> [image_version]"
	echo "options:"
	echo "  -f  run in foreground"
	echo "  -h  print usage"
}

while getopts "hf" arg; do
	case $arg in
		f)
			DOCKEROPT="-it"
			shift
			;;
		h | *)
			usage
			exit
			;;
	esac
done

IMAGE="amolabs/amod"
VERSION="latest"

DATAROOT=$1
if [ -z "$DATAROOT" ]; then
	usage
	exit
fi

if [ ! -z "$2" ]; then
	VERSION=$2
fi

echo "data root 	= $DATAROOT"
echo "image 		= $IMAGE:$VERSION"
NAME=$(basename $DATAROOT)
if [ -z "$NAME" ]; then
	echo "Could not determine docker container name. Using 'bogus'..."
	NAME=bogus
	exit
fi
echo "container name = $NAME"

echo -n "Stopping existing container..."
docker stop "$NAME" > /dev/null 2>&1
echo "done"
echo -n "Removing existing container..."
docker rm "$NAME" > /dev/null 2>&1
echo "done"
echo -n "Launching new container..."
CONTID=$(docker run $DOCKEROPT -v $DATAROOT/tendermint:/tendermint:Z -v $DATAROOT/amo:/amo:Z --name "$NAME" -p 26656-26657:26656-26657 "$IMAGE":"$VERSION")
if [ $? == 0 ]; then echo "done"; fi
echo "Container id = $CONTID"
