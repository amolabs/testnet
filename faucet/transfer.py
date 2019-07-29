#!/usr/bin/env python
# -*- coding: utf8 -*-
# vim: set expandtab :
import os
import sqlite3
import shlex, subprocess
import json

rpcserver = '139.162.116.176:26657'

# expected schema
#`recp (
#	id integer primary key,
#	request_time text,
#	transfer_time text,
#	address text unique
#)`;

cwd = os.path.dirname(os.path.abspath(__file__))
conn = sqlite3.connect(cwd+'/db/faucet.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("select * from recp where transfer_time is null order by id limit 10")

rows = c.fetchall();
if len(rows) > 0:
    print 'totol rows:', len(rows);

for row in rows:
    print 'processing: {} ...'.format(row['address']),
    cmd = 'amocli --rpc {} --json --user faucet tx transfer {} 10000'.format(
            rpcserver,
            row['address'],
            )
    args = shlex.split(cmd)

    #out = subprocess.check_output(cmd, shell=True)
    envPath = os.getenv('PATH')
    p = subprocess.Popen(args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={'PATH':envPath}
            )
    out, err = p.communicate()
    res = json.loads(out)
    if res['height'] > 0:
        c.execute(
                "update recp set transfer_time = DATETIME('now') where id = ?",
                (row['id'],)
                )
        print 'done'
    else:
        print 'error'
        print res

conn.commit()
conn.close()
