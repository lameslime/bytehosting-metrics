### Collects all sorts of data from user accessible APIs from Bytehosting and sends them to InfluxDB v2
- Service info
- Status
- IP
- Traffic
- Live data
- Action logs

Some metrics aren't colleted as of now
- Multiple ipv4 and ipv6 overall
- DDoS logs (don't know formatting)
- Cron and backups
- Can't stream WSS live data (per second)

Grafana dashboard is planned.

### Settings
- main.py > class Schedule, in init are values for intervals
- example `launch.json`
```json
"version": "0.2.0",
"configurations": [
    {
        "name": "Run Debug",
        "type": "debugpy",
        "request": "launch",
        "program": "${workspaceFolder}/src/main.py",
        "cwd": "${workspaceFolder}",
        "args": [
            "--bytehosting_token", "tokenbyte",
            "--influx_token", "tokeninflux",
            "--influx_org", "influxorg",
            "--influx_bucket", "bytehosting",
            "--influx_url", "https://influx.example.com",
            "--influx_verify_ssl", "True",
        ]
    }
]
```
- or use env variables in docker-compose

### Run with
- Git clone and `docker compose up --build`
- If running manually, don't forget venv (optional) and `pip install -r requirements.txt`
