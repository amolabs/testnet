if [ -z "$AMOHOME" ]; then
	AMOHOME=/amo
fi
if [ -z "$TMHOME" ]; then
	TMHOME=/tendermint
fi
if [ -z "$MONIKER" ]; then
	MONIKER=default
fi

/usr/bin/tendermint --home $TMHOME init

/usr/bin/amod run &
/usr/bin/tendermint --moniker $MONIKER --home $TMHOME node

