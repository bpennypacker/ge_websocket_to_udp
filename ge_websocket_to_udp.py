#!/usr/bin/env python3

import aiohttp
import asyncio
from typing import Any, Dict, Tuple
import configparser
import socket
import time

from gekitchen import (
    EVENT_ADD_APPLIANCE,
    EVENT_APPLIANCE_STATE_CHANGE,
    EVENT_APPLIANCE_INITIAL_UPDATE,
    EVENT_DISCONNECTED,
    ErdApplianceType,
    ErdCode,
    ErdCodeType,
    ErdOvenCookMode,
    GeAppliance,
    GeWebsocketClient
)

machine_status = {
    0: 'Idle',
    1: 'Standby',
    2: 'Run',
    3: 'Pause',
    4: 'EOC',
    5: 'DSMDelayRun',
    6: 'DelayRun',
    7: 'DelayPause',
    8: 'DrainTimeout',
    128: 'Clean Speak'
}

machine_type = {
    ErdApplianceType.DRYER: "DRYER",
    ErdApplianceType.WASHER: "WASHER"
}

class GEWebsocketToUDP:
    def __init__(self):
        self.sleeper = None
        self.client = None
        self.config = None

    async def log_state_change(self, data: Tuple[GeAppliance, Dict[ErdCodeType, Any]]):
        """Send state changes via UDP if desireable"""
        appliance, state_changes = data
        if not appliance.appliance_type in machine_type:
            return

        machine = machine_type[appliance.appliance_type]

        if not (machine in self.config and self.config[machine]['enabled']):
            return

        # state_changes['0x2000'] is machine status
        if not '0x2000' in state_changes:
            return

        b = int.from_bytes(state_changes['0x2000'], "big")

        ip = socket.gethostbyname(self.config[machine]['host'])

        if 'prefix' in self.config[machine]:
            msg = "{}{}".format(self.config[machine]['prefix'], machine_status[b])
        else:
            msg = machine_status[b]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(bytes(msg, 'utf-8'), (ip, int(self.config[machine]['port'])))

        t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        print ("{} : {} {}:{} {}".format(t, machine, self.config[machine]['host'], self.config[machine]['port'], msg))

    async def do_event_disconnect(self, appliance: GeAppliance):
        print ("Received disconnect...")
        self.client.disconnect()
        self.sleeper.cancel_all()
        await self.sleeper(10)

    async def main(self, loop):
        self.config = configparser.ConfigParser()
        self.config.read('ge_websocket_to_udp.ini')
        self.client = GeWebsocketClient(loop, self.config['auth']['username'], self.config['auth']['password'])
        self.client.add_event_handler(EVENT_APPLIANCE_STATE_CHANGE, self.log_state_change)
        self.client.add_event_handler(EVENT_DISCONNECTED, self.do_event_disconnect)

        session = aiohttp.ClientSession()

        asyncio.ensure_future(self.client.async_get_credentials_and_run(session), loop=loop)
        await self.sleeper(86400)

    def make_sleep(self):
        async def sleeper(delay, result=None, *, loop=None):
            coro = asyncio.sleep(delay, result=result, loop=loop)
            task = asyncio.ensure_future(coro)
            sleeper.tasks.add(task)
            try:
                return await task
            except asyncio.CancelledError:
                return result
            finally:
                sleeper.tasks.remove(task)

        sleeper.tasks = set()
        sleeper.cancel_all = lambda: sum(task.cancel() for task in sleeper.tasks)
        self.sleeper = sleeper

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        try:
            obj = GEWebsocketToUDP()
            obj.make_sleep()
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print("{}: starting async loop...".format(t))
            loop.run_until_complete(obj.main(loop))
        except Exception as e:
            print("Caught exception: {}".format(e))
            pass

        print("loop aborted. Sleeping 300 seconds...")
        time.sleep(300)
