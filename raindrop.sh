#!/bin/bash
RPC=139.162.116.176:26657
TESTER0=BC4BAF38355C6CCF8422DD3D273B3DBB83B2370B 
TESTER1=61D6C533B93B5BD7F9B6A11C5356C484D17692BC

while true; do
	amocli --rpc $RPC tx transfer --user tester1 --to $TESTER0 --amount 100
	amocli --rpc $RPC tx transfer --user tester0 --to $TESTER1 --amount 100
	sleep 600
done
