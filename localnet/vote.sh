#!/bin/zsh

AMOCLI=$HOME/go/bin/amocli

date
$AMOCLI --json --broadcast commit --user tval2 tx vote 1 1
$AMOCLI --json --broadcast commit --user tval3 tx vote 1 1
