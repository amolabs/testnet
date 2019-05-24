#!/usr/bin/env python
# -*- coding: utf8 -*-
import sqlite3
import subprocess
import json

# expected schema
#`recp (
#	id integer primary key,
#	request_time text,
#	transfer_time text,
#	address text unique
#)`;

conn = sqlite3.connect('./db/faucet.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("select * from recp where transfer_time is null order by id limit 10")
print c.rowcount

for row in c.fetchall():
    print 'processing: {} ...'.format(row['address']),
    cmd = 'amocli {} --user faucet tx transfer {} 1000'\
            .format('', row['address'])
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

conn.commit()
conn.close()
