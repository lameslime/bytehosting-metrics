from bytehosting_api import Bytehosting
from influx_api import Influx
import time
from threading import Thread

def main(args):
    byte_api = Bytehosting(args.bytehosting_token)
    influx_api = Influx(args.influx_url, args.influx_token, args.influx_org, args.influx_bucket, eval(args.influx_verify_ssl))
    
    service_list = byte_api.get_service_list()
    
    # Create objects from service
    service_list_objects = {}
    for service in service_list:
        service_list_objects[service['id']] = Schedule(byte_api, influx_api, service['id'])

    # Main data collection start
    while True:
        for service in service_list:
            service_list_objects[service['id']].run_tasks()

            # TODO
            # data['backup'] = byte_api.get_service_backup(service['id'])
            # data['cron'] = byte_api.get_service_cron(service['id'])

            time.sleep(4)
            
            

class Schedule():
    def __init__(self, byte_api, influx_api, sid):
        self.sid = sid
        self.byte_api = byte_api
        self.influx_api = influx_api
        self.service_details = byte_api.get_service_details(self.sid)
        self.service = self.service_details['service']

        self.schedule_i, self.schedule_l = {}, {}
        # Intervals in seconds
        self.schedule_i['details'] = 600
        self.schedule_i['status'] = 60
        self.schedule_i['ip'] = 3600
        self.schedule_i['traffic'] = 3600
        self.schedule_i['ddos_logs'] = 1800
        self.schedule_i['action_logs'] = 1800
        self.schedule_i['live_data'] = 30
        # Last update, don't edit
        self.schedule_l['details'] = 0
        self.schedule_l['status'] = 0
        self.schedule_l['ip'] = 0
        self.schedule_l['traffic'] = 0
        self.schedule_l['ddos_logs'] = 0
        self.schedule_l['action_logs'] = 0
        self.schedule_l['live_data'] = 0

    
    def run_tasks(self):
        self.time_init = time.time()
        # self.check_interval('details', self.byte_api.get_service_details, self.sid)
        self.check_interval('details', self.thread_det_details)
        self.check_interval('status', self.thread_det_status)
        self.check_interval('ip', self.thread_det_ip)
        self.check_interval('traffic', self.thread_det_traffic)
        self.check_interval('ddos_logs', self.thread_det_ddos)
        self.check_interval('action_logs', self.thread_det_logs)
        self.check_interval('live_data', self.thread_det_service_wss)

    def check_interval(self, name, func, args=None):
        if self.schedule_l[name] == 0 or self.time_init - self.schedule_l[name] >= self.schedule_i[name]:
            self.schedule_l[name] = time.time()
            # print(f'Ran {name}')
            if args == None:
                result = func()
            else:
                result = func(args)
            
            # Updates service details
            if name == 'details':
                self.service_details = result
                self.service = self.service_details['service']

    def do_thread(self, func, args):
        thread = Thread(target=func, args=args)
        thread.daemon = False
        thread.start()

    # Collectors in threads
    def thread_det_details(self):
        data = {}
        data['details'] = self.byte_api.get_service_details(self.sid)
        # print(data['details'])
        self.influx_api.service_data_send(data)
        return data['details']

    def thread_det_status(self):
        data = {}
        data['details'] = self.service_details
        data['status'] = self.byte_api.get_service_status(self.sid)
        # print(data['status'])
        self.influx_api.service_data_send(data)

    def thread_det_ip(self):
        data = {}
        data['details'] = self.service_details
        data['ip'] = self.byte_api.get_service_ip(self.sid)
        # print(data['ip'])
        self.influx_api.service_data_send(data)

    def thread_det_traffic(self):
        data = {}
        data['details'] = self.service_details
        data['traffic'] = self.byte_api.get_service_traffic(self.sid)
        # print(data['traffic'])
        self.influx_api.service_data_send(data)

    def thread_det_ddos(self):
        data = {}
        data['details'] = self.service_details
        data['ddos_logs'] = self.byte_api.get_service_ddos_logs(self.sid)
        # print(data['ddos_logs'])
        self.influx_api.service_data_send(data)

    def thread_det_logs(self):
        data = {}
        data['details'] = self.service_details
        data['action_logs'] = self.byte_api.get_service_action_logs(self.sid)
        # print(data['action_logs'])
        self.influx_api.service_data_send(data)

    def thread_det_service_wss(self):
        data = {}
        data['details'] = self.service_details
        data['live_data'] = self.byte_api.get_service_wss_data.start_log(self.sid, oneshot=True, mute_log=True)
        # print(data['live_data'])
        self.influx_api.service_data_send(data)

def is_running_in_docker():
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read() or "containerd" in f.read()
    except FileNotFoundError:
        return False

import argparse
import os
class EmulateArgs():
    def __init__(self):
        self.bytehosting_token = os.getenv('bytehosting_token')
        self.target_uids = os.getenv('target_uids')
        self.influx_token = os.getenv('influx_token')
        self.influx_org = os.getenv('influx_org')
        self.influx_bucket = os.getenv('influx_bucket')
        self.influx_url = os.getenv('influx_url')
        self.influx_verify_ssl = os.getenv('influx_verify_ssl', False)
    
    def get_val(self, value):
        return getattr(self, value)

if __name__ == '__main__':
    envs = EmulateArgs()

    parser = argparse.ArgumentParser(description='Export bytehosting metrics to InfluxDB v2')
    parser.add_argument('--bytehosting_token', default=envs.get_val('bytehosting_token'))
    parser.add_argument('--target_uids', default=envs.get_val('target_uids'), help='Provide a string of UIDs to apply filters, not implemented yet')
    parser.add_argument('--influx_token', default=envs.get_val('influx_token'))
    parser.add_argument('--influx_org', default=envs.get_val('influx_org'))
    parser.add_argument('--influx_bucket', default=envs.get_val('influx_bucket'))
    parser.add_argument('--influx_url', default=envs.get_val('influx_url'), help='Full URL to IndluxDB v2, eg: https://influx.example.com')
    parser.add_argument('--influx_verify_ssl', default=envs.get_val('influx_verify_ssl'), help='Verify Influx SSL')
    args = parser.parse_args()

    main(args)