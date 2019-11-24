#!/usr/bin/python3.7
from typing import List, Dict
import requests
import asyncio
import aiohttp
from aiohttp import web
import time
import json
import time

REMOTE_NODES_URL = "https://raw.githubusercontent.com/wrkzcoin/wrkzcoin-nodes-json/master/wrkzcoin-nodes.json"
SLEEP_CHECK = 15  # 15s
NODE_LIVE_LIST = []

selected_node = None

# Start the work
async def getNodeList():
    time_out = 10
    resp = requests.get(url=REMOTE_NODES_URL,timeout=time_out)
    data = resp.json()['nodes']
    node_list = []  # array of nodes
    proto = 'http://'
    for node in data:
        getinfo = None
        getfee = None
        print(node)
        try:
            if node['ssl'] == True:
                proto = 'https://'
            else:
                proto = 'http://'
            node_url = proto + node['url'].strip()+':'+str(node['port'])+'/getinfo'
            print("Checking {}".format(node_url))
            async with aiohttp.ClientSession() as session:
                async with session.get(node_url, timeout=time_out) as response:
                    try:
                        getinfo = await response.json()
                    except Exception as e:
                        getinfo = json.loads(await response.read())
                    try:
                        node_url = proto + node['url'].strip()+':'+str(node['port'])+'/fee'
                        print("Checking {}".format(node_url))
                        async with aiohttp.ClientSession() as session:
                            async with session.get(node_url, timeout=time_out) as response:
                                try:
                                    getfee = await response.json()
                                except Exception as e:
                                    getfee = json.loads(await response.read())
                    except asyncio.TimeoutError:
                        print('TIMEOUT: {}'.format(node_url))
                        continue
        except asyncio.TimeoutError:
            print('TIMEOUT: {}'.format(node_url))
            continue
        if all(v is not None for v in [getinfo, getfee]):
            # print("Data got for {}".format(node['name']))
            node_list.append({
                'name': node['name'],
                'url': node['url'].strip(),
                'port': node['port'],
                'ssl': node['ssl'],
                'cache': node['cache'],
                'fee': {
                    'address':getfee['address'] if 'address' in getfee and len(getfee['address']) == 98 else "",
                    'fee':int(getfee['amount']) if 'amount' in getfee else 0
                },
                'online': True,
                'version': getinfo['version'],
                'timestamp': int(time.time()),
                'height': getinfo['height'],
                'alt_blocks_count': getinfo['alt_blocks_count'],
                'incoming_connections_count': getinfo['incoming_connections_count'],
                'outgoing_connections_count': getinfo['outgoing_connections_count'],
                'network_height': getinfo['network_height'],
                'difficulty': getinfo['difficulty'],
                'last_known_block_index': getinfo['last_known_block_index'],
                'tx_count': getinfo['tx_count'],
                'white_peerlist_size': getinfo['white_peerlist_size'],
                'start_time': getinfo['start_time'],
                'grey_peerlist_size': getinfo['grey_peerlist_size'],
                'tx_pool_size': getinfo['tx_pool_size'],
                'hashrate': getinfo['hashrate']
                })
        else:
            node_list.append({
                'name': node['name'],
                'url': node['url'].strip(),
                'port': node['port'],
                'ssl': node['ssl'],
                'cache': node['cache'],
                'fee': {
                    'address': "",
                    'fee': 0
                },
                'online': False,
                'version': "",
                'timestamp': 0,
                'height': 0,
                'alt_blocks_count': 0,
                'incoming_connections_count': 0,
                'outgoing_connections_count': 0,
                'network_height': 0,
                'difficulty': 0,
                'last_known_block_index': 0,
                'tx_count': 0,
                'white_peerlist_size': 0,
                'start_time': 0,
                'grey_peerlist_size': 0,
                'tx_pool_size': 0,
                'hashrate': 0,
                'synced': False
                })
    return node_list


async def handle_get_nodelist(request):
    global NODE_LIVE_LIST
    if len(NODE_LIVE_LIST) == 0:
        NODE_LIVE_LIST = await getNodeList()
    response_obj = {"nodes": NODE_LIVE_LIST}
    # json_string = json.dumps(response_obj).replace(" ", "")
    return web.json_response(response_obj, status=200)


# node_check_bg
async def node_check_bg(app):
    global NODE_LIVE_LIST
    tmp_node = []
    while True:
        node_list = None
        try:
            try:
                tmp_node = await getNodeList()
                NODE_LIVE_LIST = tmp_node
            except Exception as e:
                print(e)
            if len(tmp_node) > 0:
                print("==============")
                print("Get total nodes {}.".format(tmp_node))
                print("==============")
            else:
                print('Currently 0 nodes... Sleep {s}'.format(SLEEP_CHECK))
        except asyncio.CancelledError:
            pass
        print('Getting {} nodes live.. Sleep {}s'.format(len(NODE_LIVE_LIST), SLEEP_CHECK))
        time.sleep(SLEEP_CHECK)


async def start_background_tasks(app):
    app['get_node_live'] = asyncio.create_task(node_check_bg(app))


async def cleanup_background_tasks(app):
    app['get_node_live'].cancel()
    await app['get_node_live']


app = web.Application()
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

app.router.add_route('GET', '/node/list', handle_get_nodelist)

web.run_app(app, host='127.0.0.1', port=8080)
