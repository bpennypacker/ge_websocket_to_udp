GE wifi-enable appliances can be controlled and monitored via the SmartHQ smartphome app. This python script uses the same websocket API that SmartHQ uses to listen for events from GE appliances and send them to another device on your network via UDP.

The impetus for this is due to the fact that the GE API is somewhat complex and has a lot of work has been done to support it in python via the [gekitchen](https://github.com/ajmarks/gekitchen) project. I was hoping to use this from directly within [Indigo ](https://www.indigodomo.com/), but unfortunately the gekitchen module relies on pycares and there are [issues installing pycares on MacOS](https://github.com/saghul/pycares/issues/94). So my solution, given I was mostly interested in receiving events from my washer and dryer, was to write a script that runs on a Rasperry Pi and sends events via UDP to my Mac, which can be easily handled within Indigo.

To use this on a Raspberry Pi (I'm using Raspbian):

1. Install the necessary python dependencies by running `/usr/bin/env python3 -m pip install -r requirements.txt`

2. Edit ge_websocket_to_udp.ini, providing your SmartHQ username & password, and the hostname or IP of the host to send the UDP messages to.

Note that each section of the configuration file that corresponds to an appliance has its own host & port definitions as well as an optional prefix. This is simply to make the script more flexible in the event you want to send messages for different appliances to different targets. Although I send all events to the same host, I use different ports to distinguish between the different appliances. Indigo makes it easy to create a virtual device for different UDP ports using the [UDP Listener](https://www.indigodomo.com/pluginstore/215/) plug-in.

If you decide you want to send events for multiple devices to the same host & port you can uncomment the optional 'prefix' entry in the configuration file to add a unique prefix to each event based on the appliance that triggered the event.

The script displays events on the console after sending them via UDP, which helps with troublehooting. I run this script in a screen session so that I can easily check on its output should I ever have any issues with it.
