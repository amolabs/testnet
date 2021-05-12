#!/bin/bash

# stake for 3 validators

ROOT=$(realpath $(dirname $0))
DATAROOT=$ROOT/testdata
NODENUM=3
AMO=1000000000000000000

export CLI=amocli

for ((i=1; i<=NODENUM; i++))
do
	eval VALPUB=$(cat $DATAROOT/val$i/amo/config/priv_validator_key.json | jq .pub_key.value)
	VAL=$(amocli key list | grep tval$i | awk '{print $4}')
	echo for tval$1 $VAL $VALPUB
	$CLI --user tvault tx transfer $VAL ${AMO}00
	$CLI --user tval$i tx stake $VALPUB ${AMO}00
done
