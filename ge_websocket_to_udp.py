"""
Websocket client example

We're going to run the client in a pre-existing event loop.  We're also going to register some event callbacks
to update appliances every five minutes and to turn on our oven the first time we see it.  Because that is safe!
"""

import aiohttp
import asyncio
#import logging
#from datetime import timedelta
from typing import Any, Dict, Tuple
import configparser
import socket
import time


from gekitchen import (
    EVENT_ADD_APPLIANCE,
    EVENT_APPLIANCE_STATE_CHANGE,
    EVENT_APPLIANCE_INITIAL_UPDATE,
    ErdApplianceType,
    ErdCode,
    ErdCodeType,
    ErdOvenCookMode,
    GeAppliance,
    GeWebsocketClient,
    OvenCookSetting,
    OVEN_COOK_MODE_MAP
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


async def log_state_change(data: Tuple[GeAppliance, Dict[ErdCodeType, Any]]):
    appliance, state_changes = data
    if not appliance.appliance_type in machine_type:
        return

    machine = machine_type[appliance.appliance_type]

    config = configparser.ConfigParser()
    config.read('ge_websocket_to_udp.ini')

    if not (machine in config and config[machine]['enabled']):
        return

    # state_changes['0x2000'] is machine status
    if not '0x2000' in state_changes:
        return

    b = int.from_bytes(state_changes['0x2000'], "big")

    ip = socket.gethostbyname(config[machine]['host'])

    if 'prefix' in config[machine]:
        msg = "{}{}".format(config[machine]['prefix'], machine_status[b])
    else:
        msg = machine_status[b]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(bytes(msg, 'utf-8'), (ip, int(config[machine]['port'])))

    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    print ("{} : {} {}:{} {}".format(t, machine, config[machine]['host'], config[machine]['port'], msg))

async def main(loop):
    config = configparser.ConfigParser()
    config.read('ge_websocket_to_udp.ini')
    client = GeWebsocketClient(loop, config['auth']['username'], config['auth']['password'])
    client.add_event_handler(EVENT_APPLIANCE_STATE_CHANGE, log_state_change)

    session = aiohttp.ClientSession()

    asyncio.ensure_future(client.async_get_credentials_and_run(session), loop=loop) 
    await(asyncio.sleep(86400))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        try:
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print("{}: starting async loop...".format(t))
            loop.run_until_complete(main(loop))
        except Exception as e:
            print("Caught exception: {}".format(e))
            pass

        time.sleep(300)