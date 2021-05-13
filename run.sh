#!/bin/bash

DOCKER=false
IMAGE_VERSION=latest

usage() {
	echo "syntax: $0 [options] <data_root>"
	echo "options:"
	echo "  -d  use docker with specified image version"
	echo "  -h  print usage"
}

while getopts "d:h" arg; do
	case $arg in
		d)
			DOCKER=true
			IMAGE_VERSION=$OPTARG
			;;
		h | *)
			usage
			exit
			;;
	esac
done

shift $(( OPTIND - 1 ))

DATAROOT=$1
if [ -z "$DATAROOT" ]; then
	usage
	exit
fi

echo "data root     = $DATAROOT"

if [ "$DOCKER" = true ]; then
	echo "docker image  = $IMAGE_VERSION"
	docker run -it --rm -p 26657 -v $DATAROOT/amo:/amo amolabs/amod:$IMAGE_VERSION amod run --home /amo
else
	amod run --home $DATAROOT/amo
fi
