import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time

class Bytehosting():
    def __init__(self, token):
        self.token = token

        self.headers = {}
        self.headers['token'] = self.token
        self.headers['Content-Type'] = 'application/json'

        self.default_host = 'backend.panel.bytehosting.cloud'
        self.http_proto = 'https'
        match self.http_proto:
            case 'https':
                self.default_verify_ssl = True
                self.default_host = f'https://{self.default_host}'
            case 'http':
                self.default_host = f'http://{self.default_host}'
        
        self.get_service_wss_data = LiveDataWSStream(self.token)
        # TODO: Check token status
        # TODO: HTTP error handling

    # API calls
    def get_service_list(self):
        uri = '/v1/service/list'
        response = self.request_get(uri, self.headers)
        return response

    def get_service_details(self, uid):
        uri = f'/v1/service/{uid}'
        response = self.request_get(uri, self.headers)
        return response

    def get_service_status(self, uid):
        uri = f'/v1/service/{uid}/status'
        response = self.request_get(uri, self.headers)
        return response

    def get_service_ip(self, uid):
        uri = f'/v1/service/{uid}/ip'
        response = self.request_get(uri, self.headers)
        return response
    
    def get_service_os(self, uid):
        uri = f'/v1/service/{uid}/os'
        response = self.request_get(uri, self.headers)
        return response
    
    def get_service_backup(self, uid):
        uri = f'/v1/service/{uid}/backup'
        response = self.request_get(uri, self.headers)
        return response
    
    def get_service_cron(self, uid):
        uri = f'/v1/service/{uid}/cron'
        response = self.request_get(uri, self.headers)
        return response

    def get_service_traffic(self, uid):
        uri = f'/v1/service/{uid}/traffic'
        response = self.request_get(uri, self.headers)
        return response
    
    def get_service_ddos_logs(self, uid):
        uri = f'/v1/service/{uid}/incidents'
        response = self.request_get(uri, self.headers)
        return response
    
    def get_service_action_logs(self, uid):
        uri = f'/v1/service/{uid}/actionlogs'
        response = self.request_get(uri, self.headers)
        return response

    def request_get(self, uri, headers, host=None):
        if host is None:
            host = self.default_host
        response = requests.get(f'{host}{uri}', headers, verify=self.default_verify_ssl)
        return response.json()


from websocket import WebSocketApp
from threading import Thread
import threading
from queue import Queue

class LiveDataWSStream:
    def __init__(self, token):
        self.token = token
        self.websocket_url = 'wss://livedata.panel.bytehosting.cloud'
        self.services = {}  # Dictionary to manage WebSocket instances

    def on_message(self, ws, message, sid, data_queue, oneshot):
        if message == "Error 3":
            print(f"[{sid}] Socket No Reconnect.")
            self.stop_log(sid)
            return

        if message == "Ping":
            ws.send("Pong")
            return

        try:
            data = json.loads(message)
            data_queue.put(data)
            if oneshot == True:
                print(f'[{sid}] Oneshot, stopping\n')
                self.stop_log(sid, mute_log=True)
        except json.JSONDecodeError:
            print(f"[{sid}] Failed to parse message")
            return

    def on_error(self, ws, error, sid):
        print(f"[{sid}] WebSocket Error: {error}")

    def on_open(self, ws, sid):
        # print(f"[{sid}] WebSocket connection opened.")
        ws.send(json.dumps({
            "token": self.token,
            "serviceid": sid
        }))

    def start_log(self, sid, data_queue=None, oneshot=False, mute_log=False):
        if sid in self.services and self.services[sid]['running'] == True:
            print(f"[{sid}] WebSocket is already running")
            return

        if data_queue is None:
            data_queue = Queue()
        else:
            data_queue = data_queue

        # Define the WebSocket instance and thread
        ws = WebSocketApp(
            self.websocket_url,
            on_message=lambda ws, message: self.on_message(ws, message, sid, data_queue, oneshot),
            on_error=lambda ws, error: self.on_error(ws, error, sid),
            on_open=lambda ws: self.on_open(ws, sid)
        )

        thread = Thread(target=self.run_ws, args=(ws, sid))
        thread.daemon = True

        # Store the service
        self.services[sid] = {
            "ws": ws,
            "thread": thread,
            "running": True,
            "data_queue": data_queue
        }

        thread.start()
        if mute_log == False:
            print(f"[{sid}] WebSocket started")
        if oneshot == True:
            return data_queue.get()
        return data_queue  # Return the queue for the main thread

    def run_ws(self, ws, sid):
        try:
            ws.run_forever()
        except Exception as e:
            print(f"[{sid}] Error in WebSocket thread: {e}")
        finally:
            if sid in self.services:
                self.services[sid]["running"] = False

    def stop_log(self, sid, mute_log=False):
        if sid not in self.services:
            print(f"[{sid}] WebSocket is not running")
            return

        # Stop the WebSocket
        service = self.services[sid]
        service['ws'].close()
        if not service['thread'].ident == threading.get_ident():
            service['thread'].join()
        
        self.services[sid]['ws'] = ''
        self.services[sid]['thread'] = ''
        self.services[sid]['ws'] = False
        if mute_log == False:
            print(f"[{sid}] WebSocket stopped")

    def restart_log(self, sid):
        print(f"[{sid}] WebSocket restarted")
        self.stop_log(sid, mute_log=True)
        if self.services[sid]['data_queue']:
            data_queue = self.services[sid]['data_queue']
        else:
            data_queue = None
        self.start_log(sid, data_queue, mute_log=True)