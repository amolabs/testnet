/* vim: set sw=2 ts=2 : */
var http = require('http');
var fs = require('fs');
const sqlite3 = require('sqlite3');
const dbdir = './db';
const dbpath = dbdir+'/faucet.db';

var db;
const schema = `recp (
	id integer primary key,
	request_time text,
	transfer_time text,
	address text unique
)`;

const headers = {
	'Access-Control-Allow-Headers': '*',
	'Access-Control-Allow-Origin': '*',
};

var server = http.createServer((req, res) => {
	if (req.method == 'POST') {
		var postData = '';
		req.on('data', function (chunk) {
			postData += chunk;
		});

		req.on('end', function () {
			var item = JSON.parse(postData);
			if (item.recp) {
				db.get(`select * from recp where address = ?`,
					item.recp,
					function (err, row) {
						if (err) {
							console.error(err.message);
						} else if (row) {
							console.error('address already requested:', item.recp);
							res.writeHeader(409, headers);
							res.end(`Recipient ${item.recp} has been already requested.`);
						} else {
							// No previous request. OK to go.
							db.run(`insert into recp (request_time, address) values (
									DATETIME('now','localtime'), ?
								)`,
								item.recp,
								function (err) {
									if (err) {
										console.error(err.message);
										res.writeHeader(500, headers);
										res.end('Internal error:', err.message);
									} else {
										res.writeHeader(200, headers);
										res.end(`Recipient ${item.recp} has been recorded.`);
									}
								});
						}
					});
			} else {
				res.writeHeader(400, headers);
				res.end('Unable to read recipient info.');
			}
		});
	} else if (req.method == 'OPTIONS') {
		req.on('data', function (chunk) {
			// TODO
		});
		req.on('end', function () {
			res.writeHeader(200, headers);
			res.end();
		});
	} else {
		req.on('data', function (chunk) {
			// TODO
		});
		req.on('end', function () {
			res.writeHeader(405, headers);
			res.end();
		});
	}
});

fs.mkdir(dbdir, {recursive: true}, (err) => {
	if (err) {
		console.error(err.message);
		//process.exit(1);
	}
});

db = new sqlite3.Database(dbpath, (err) => {
	if (err) {
		console.error(err.message);
		process.exit(1);
	} else {
		console.log('DB connected on', dbpath);
		db.run(`create table ${schema}`, (err) => {
			if (err) console.error(err.message);
			server.listen(2000, function () {
				console.log('Faucet request recorder started.');
			});
		});
	}
});

