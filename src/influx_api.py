from datetime import datetime, timezone
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import json

class Influx() :
    def __init__(self, influx_url, influx_token, influx_org, influx_bucket, influx_verify_ssl):
        if influx_verify_ssl == False:
            import urllib3
            urllib3.disable_warnings()
            print(f'Disabling self-signed SSL errors')

        self.org = influx_org
        self.bucket = influx_bucket
        self.api_client = influxdb_client.InfluxDBClient(url=influx_url, token=influx_token, org=self.org, verify_ssl=influx_verify_ssl)
        self.api_write = self.api_client.write_api(write_options=SYNCHRONOUS)
        self.api_delete = self.api_client.delete_api()

        self.dry_run = False
        self.skip_details = False
    
    def service_data_send(self, records):
        # Records contain data per service
        tags = {}
        tags['id'] = records['details']['service']['id']
        tags['traffic_type'] = ''
        # name = records['details']['service']['id']
        # if not name == 'null' or not name == None:
        #     tags['name'] = name
        tags['productdisplay'] = records['details']['service']['productdisplay']
        
        for key, record in records.items():
            json_body = {}
            match key:
                case 'details':
                    if not len(records) == 1:
                        continue
                    json_body = {}
                    json_body['measurement'] = 'service'
                    json_body['tags'] = tags
                    json_body['fields'] = {}
                    json_body['fields']['serviceid'] = record['service']['id']
                    json_body['fields']['expire_at'] = datetime.fromtimestamp(record['service']['expire_at'], tz=timezone.utc).isoformat()
                    json_body['fields']['created_on'] = datetime.fromtimestamp(record['service']['created_on'], tz=timezone.utc).isoformat()
                    if record.get('lockreason') == 0:
                        json_body['fields']['delete_at'] = datetime.fromtimestamp(record['service']['delete_at'], tz=timezone.utc).isoformat()
                    json_body['fields']['daysleft'] = int(record['service']['daysleft'])
                    # json_body['fields']['ip'] = record['ip']
                    json_body['fields']['price'] = float(record['service']['price'])
                    json_body['fields']['deletedone'] = int(record['service']['deletedone'])
                    json_body['fields']['locked'] = int(record['service']['locked'])
                    if record['service'].get('lockreason') is not None:
                        json_body['fields']['lockreason'] = int(record['service']['locked'])
                    json_body['fields']['resellerrenew'] = float(record['service']['resellerrenew'])
                    json_body['fields']['reseller_locked'] = record['service']['reseller_locked']
                    if record['service'].get('reseller_locked_reasonreseller_locked_reason') is not None:
                        json_body['fields']['reseller_locked_reason'] = int(record['service']['reseller_locked_reason'])
                    if record['service'].get('affiliateid') is not None:
                        json_body['fields']['affiliate_id'] = int(record['service']['affiliateid'])
                    # TODO: Add rest of the info, when i feel like it

                case 'status':
                    json_body = {}
                    json_body['measurement'] = 'status'
                    json_body['tags'] = tags
                    json_body['fields'] = {}
                    json_body['fields']['status'] = json_body['fields']['status'] = record['status']

                case 'ip':
                    json_body = {}
                    json_body['measurement'] = 'ip'
                    json_body['tags'] = tags
                    json_body['fields'] = {}
                    json_body['fields']['ipv4_addr'] = record['ipv4'][0]['ip']
                    json_body['fields']['ipv4_gw'] = record['ipv4'][0]['gw']
                    json_body['fields']['ipv4_subnet'] = record['ipv4'][0]['subnet']
                    json_body['fields']['ipv4_rdns'] = record['ipv4'][0]['rdns']
                    json_body['fields']['ipv4_rdns_note'] = record['ipv4'][0]['note']
                    json_body['fields']['ddos_protection'] = record['ipv4'][0]['protstatus']
                    # TODO ipv6
                    # TODO ipv4 has ip's in array, likely supports multiple ips
                
                case 'traffic':
                    records_d = self.helper_parse_traffic(record['history']['last30days'], tags, traffic_type='daily')
                    self.client_write(records_d, skip_array=True)
                    records_m = self.helper_parse_traffic(record['history']['months'], tags, traffic_type='monthly')
                    self.client_write(records_m, skip_array=True)

                    json_body = {}
                    json_body['measurement'] = 'traffic'
                    json_body['tags'] = tags
                    json_body['tags']['traffic_type'] = 'current'
                    json_body['fields'] = {}
                    json_body['fields']['current_gb'] = float(record['current'].replace(',', ''))
                    json_body['fields']['max_allowed_gb'] = int(record['max']) * 1000 # Reported as TB
                    json_body['fields']['percentage'] = float(record['percentage'])

                case 'live_data':
                    json_body = {}
                    json_body['measurement'] = 'live_data'
                    json_body['tags'] = tags
                    json_body['fields'] = {}
                    json_body['fields']['cpu'] = int(record['cpu'])
                    json_body['fields']['maxmem'] = record['maxmem'] / (1024 ** 3)
                    json_body['fields']['mem'] = record['mem'] / (1024 ** 3)
                    json_body['fields']['nodecpu'] = int(record['nodecpu'])
                    # TODO it is growing value, needs logic to extract data rate, only worth without oneshot
                    # json_body['fields']['netin'] = record['netin']
                    # json_body['fields']['netout'] = record['netout']
                
                case 'action_logs':
                    action_log = self.helper_parse_action_log(record, tags)
                    self.client_write(action_log, skip_array=True)
                    continue

                case 'ddos_logs':
                    # TODO: not finished, I don't know data format
                    ddos_log = self.helper_parse_ddos_log(record['data'], tags)
                    # self.client_write(ddos_log, skip_array=True)
                    continue


            # Skip writing if not needed
            if len(json_body) > 0:
                self.client_write(json_body)
                

    def client_write(self, json_body, skip_array=False, threaded=False):
        # Needs to be in array
        if skip_array != True:
            json_body = [json_body]

        if self.dry_run == True:
            print(f'Influx dry write: {json_body}\n')
            return
        else:
             print(f'Influx write: {json_body[0]['measurement']}')

        try:
            return self.api_write.write(bucket=self.bucket, org=self.org, record=json_body, write_precision=WritePrecision.S)
        except Exception as e:
            print('Influx API fail, connection issue?')
            print(e)

    def helper_parse_traffic(self, records, tags, traffic_type):
        data = []
        for datapoint in records:
            json_body = {}
            # Don't know if server changes timezone, my guess it does. Strip time to keep it uniform.
            json_body['time'] = datetime.strptime(datapoint['date'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            json_body['measurement'] = 'traffic'
            json_body['tags'] = tags
            json_body['tags']['traffic_type'] = traffic_type
            json_body['fields'] = {}
            # Megabytes
            json_body['fields']['traffic_in'] = int(datapoint['in'])
            json_body['fields']['traffic_out'] = int(datapoint['out'])
            data.append(json_body)
        return data

    def helper_parse_action_log(self, records, tags):
        data = []
        for datapoint in records:
            json_body = {}
            # Don't know if server changes timezone, my guess it does
            json_body['time'] = datetime.strptime(datapoint['time'], '%H:%M:%S %d.%m.%Y').replace(tzinfo=timezone.utc).isoformat()
            json_body['measurement'] = 'action_log'
            json_body['tags'] = tags
            json_body['fields'] = {}
            json_body['fields']['log'] = datapoint['log']
            data.append(json_body)
        return data

    def helper_parse_ddos_log(self, records, tags):
        # TODO: Need example data!
        if len(records) > 0:
            print(f'Got proper DDoS log\n{records}')

    def delData(self, timeStart, timeStop, measurement):
        self.api_delete.delete(timeStart, timeStop, f'_measurement={measurement}', bucket=self.bucket, org=self.org)

if __name__ == "__main__":
    pass
    #influxAPI.delData("2023-01-01T00:00:00Z", "2024-01-01T00:00:00Z", 'measurement1')