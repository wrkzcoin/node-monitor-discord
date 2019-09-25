#!/usr/bin/python3.7
from typing import List, Dict
import requests
import asyncio
import aiohttp
from aiohttp import web
import time
import random
import json

REMOTE_NODES_URL = "https://raw.githubusercontent.com/wrkzcoin/wrkzcoin-nodes-json/master/wrkzcoin-nodes.json"
GITHUB = "https://github.com/wrkzcoin/wrkzcoin-nodes-json"
SLEEP_CHECK = 0.2*60  # 12s
NODE_LIVE_LIST = []

selected_node = None

# Start the work
async def getNodeList():
    resp = requests.get(url=REMOTE_NODES_URL,timeout=5.0)
    data = resp.json()['nodes']
    node_list = []  # array of nodes
    for node in data:
        try:
            node_url = 'http://'+node['url'].strip()+':'+str(node['port'])+'/getinfo'
            resp = requests.get(node_url,timeout=5)
            resp.raise_for_status()
            getinfo = resp.json()
            try:
                node_url = 'http://'+node['url'].strip()+':'+str(node['port'])+'/fee'
                resp = requests.get(node_url,timeout=5)
                resp.raise_for_status()
                getfee = resp.json()
                if all(v is not None for v in [getinfo, getfee]):
                    node_list.append({
                        'url':node['url'].strip(),
                        'port':node['port'],
                        'address':getfee['address'] if 'address' in getfee and len(getfee['address']) == 98 else "WrkzRNDQDwFCBynKPc459v3LDa1gEGzG3j962tMUBko1fw9xgdaS9mNiGMgA9s1q7hS1Z8SGRVWzcGc8Sh8xsvfZ6u2wJEtoZB",
                        'fee':int(getfee['amount']) if 'amount' in getfee else 5000,
                        'height':getinfo['height'],
                        'alt_blocks_count':getinfo['alt_blocks_count'],
                        'incoming_connections_count':getinfo['incoming_connections_count'],
                        'outgoing_connections_count':getinfo['outgoing_connections_count'],
                        'network_height':getinfo['network_height'],
                        'difficulty':getinfo['difficulty'],
                        'last_known_block_index':getinfo['last_known_block_index'],
                        'tx_count':getinfo['tx_count'],
                        'version':getinfo['version'],
                        'white_peerlist_size':getinfo['white_peerlist_size'],
                        'start_time':getinfo['start_time'],
                        'grey_peerlist_size':getinfo['grey_peerlist_size'],
                        'tx_pool_size':getinfo['tx_pool_size'],
                        'hashrate':getinfo['hashrate'],
                        'synced':str(getinfo['synced']).upper()
                        })
            except requests.exceptions.RequestException  as e:
                print(node['url'].strip())
                print(e)
                continue
        except requests.exceptions.RequestException  as e:
            node_list.append({
                'url':node['url'].strip(),
                'port':node['port'],
                'synced':"FALSE",
                'error':"Failed to connect."
                })
            print(node['url'].strip())
            print(e)
            continue
    return node_list


# /fee
async def handle_fee(request):
    global NODE_LIVE_LIST, selected_node
    if selected_node is None:
        node_list = await getNodeList()
        if len(node_list) > 0:
            # empty
            NODE_LIVE_LIST = []
            for item in node_list:
                # add to NODE_LIVE_LIST
                if 'error' not in item:
                    NODE_LIVE_LIST.append({"name": item['url']+':'+ str(item['port']), "address": item['address'], "fee": item['fee'], "last_check": int(time.time())})
    if len(NODE_LIVE_LIST) > 0:
        selected_node = random.choice(NODE_LIVE_LIST)
    else:
        await respond_internal_error()
        return
    selected_node = random.choice(NODE_LIVE_LIST)
    node_url = "http://" + selected_node['name']

    reply = {
        "address": selected_node['address'],
        "amount": selected_node['fee'],
        "status": "OK"
    }
    response_obj = reply
    json_string = json.dumps(response_obj).replace(" ", "")
    return web.Response(text=json_string, status=200)


async def handle_get_all(request):
    global NODE_LIVE_LIST, selected_node
    if selected_node is None:
        node_list = await getNodeList()
        if len(node_list) > 0:
            # empty
            NODE_LIVE_LIST = []
            for item in node_list:
                # add to NODE_LIVE_LIST
                if 'error' not in item:
                    NODE_LIVE_LIST.append({"name": item['url']+':'+ str(item['port']), "address": item['address'], "fee": item['fee'], "last_check": int(time.time())})
    if len(NODE_LIVE_LIST) > 0:
        selected_node = random.choice(NODE_LIVE_LIST)
    else:
        await respond_internal_error()
        return
    node_url = "http://" + selected_node['name']

    uri = str(request.rel_url).lower()
    if uri.startswith('/fee'):
        # handle_fee
        return await handle_fee(request)
    # forward all to conventional RPC
    else:
        url = node_url + uri
        try:
            async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
                async with session.get(url, ssl=False, timeout=8) as response:
                    if response.status == 200:
                        res_data = await response.read()
                        res_data = res_data.decode('utf-8')
                        return web.Response(text=res_data, status=200)
                    else:
                        return await respond_bad_request()
        except asyncio.TimeoutError:
            # If timeout, switch node
            selected_node = random.choice(NODE_LIVE_LIST)


async def handle_post_all(request):
    global NODE_LIVE_LIST, selected_node
    if selected_node is None:
        node_list = await getNodeList()
        if len(node_list) > 0:
            # empty
            NODE_LIVE_LIST = []
            for item in node_list:
                # add to NODE_LIVE_LIST
                if 'error' not in item:
                    NODE_LIVE_LIST.append({"name": item['url']+':'+ str(item['port']), "address": item['address'], "fee": item['fee'], "last_check": int(time.time())})
    if len(NODE_LIVE_LIST) > 0:
        selected_node = random.choice(NODE_LIVE_LIST)
    else:
        await respond_internal_error()
        return
    node_url = "http://" + selected_node['name']

    uri = str(request.rel_url).lower()
    # forward all to conventional RPC
    url = node_url + uri
    full_payload = await request.json()
    try:
        async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
            async with session.post(url, ssl=False, json=full_payload, timeout=8) as response:
                if response.status == 200:
                    res_data = await response.read()
                    res_data = res_data.decode('utf-8')
                    return web.Response(text=res_data, status=200)
                else:
                    return await respond_bad_request()
    except asyncio.TimeoutError:
        # If timeout, switch node
        selected_node = random.choice(NODE_LIVE_LIST)


async def respond_bad_request():
    text = "Bad Request"
    return web.Response(text=text, status=400)


async def respond_internal_error():
    text = 'Internal Server Error'
    return web.Response(text=text, status=500)


# do job to discord
async def getNodeText(app):
    global NODE_LIVE_LIST
    print('sleep 1 second')
    await asyncio.sleep(1)
    while True:
        node_list = None
        try:
            try:
                node_list = await getNodeList()
            except Exception as e:
                print(e)
            if len(node_list) > 0:
                # empty
                NODE_LIVE_LIST = []
                for item in node_list:
                    # add to NODE_LIVE_LIST
                    if 'error' not in item:
                        NODE_LIVE_LIST.append({"name": item['url']+':'+ str(item['port']), "address": item['address'], "fee": item['fee'], "last_check": int(time.time())})
                print("==============")
                print(NODE_LIVE_LIST)
                print("==============")
            else:
                print('Currently 0 nodes... Sleep {s}'.format(SLEEP_CHECK))
        except asyncio.CancelledError:
            pass
        print('Getting {} nodes live.. Sleep {}s'.format(len(NODE_LIVE_LIST), SLEEP_CHECK))
        await asyncio.sleep(SLEEP_CHECK)


async def start_background_tasks(app):
    app['get_node_live'] = asyncio.create_task(getNodeText(app))


async def cleanup_background_tasks(app):
    app['get_node_live'].cancel()
    await app['get_node_live']


app = web.Application()
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

app.router.add_route('GET', '/{tail:.*}', handle_get_all)
app.router.add_route('POST', '/{tail:.*}', handle_post_all)

web.run_app(app, host='127.0.0.1', port=8080)
