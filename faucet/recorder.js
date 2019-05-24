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

var server = http.createServer((req, res) => {
	if (req.method == 'POST') {
		var postData = '';
		req.on('data', function (chunk) {
			postData += chunk;
		});

		req.on('end', function () {
			var item = JSON.parse(postData);
			if (item.recp) {
				db.run(`insert into recp (request_time, address) values (
						DATETIME('now','localtime'),
						'${item.recp}'
					)`,
					(err) => {
					if (err) console.error(err.message);
				});

				res.writeHeader(200, {
					'Access-Control-Allow-Origin': '*',
					'Access-Control-Allow-Headers': '*',
				});
				res.end('Recipient ' + item.recp + ' has been recorded.');
			} else {
				res.writeHeader(400, {
					'Access-Control-Allow-Origin': '*',
					'Access-Control-Allow-Headers': '*',
				});
				res.end('Unable to read recipient info.');
			}
		});
	} else {
		req.on('data', function (chunk) {
		});
		req.on('end', function () {
			res.writeHeader(200, {
				'Access-Control-Allow-Origin': '*',
				'Access-Control-Allow-Headers': '*',
			});
			res.end();
		});
	}
});

fs.mkdir(dbdir, {recursive: true}, (err) => {
	if (err) {
		console.error(err.message);
		process.exit(1);
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
		});
		server.listen(2000, function () {
			console.log('Faucet request recorder started.');
		});
	}
});
