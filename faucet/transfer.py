#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import sqlite3
import subprocess
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
print 'totol rows:', len(rows);

for row in rows:
    print 'processing: {} ...'.format(row['address']),
    cmd = 'amocli --rpc {} --user faucet tx transfer {} 1000'\
            .format(rpcserver, row['address'])
    out = subprocess.check_output(cmd, shell=True)
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
