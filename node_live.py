#!/usr/bin/python3.7
from typing import List, Dict
import asyncio, aiohttp
from aiohttp import web
import time, json
import pymysql.cursors
# For some environment variables
import os

DBHOST = os.getenv('NODEWRKZ_MYSQL_HOST', 'localhost')
DBUSER = os.getenv('NODEWRKZ_MYSQL_USER', 'user')
DBNAME = os.getenv('NODEWRKZ_MYSQL_NAME', 'dbname')
DBPASS = os.getenv('NODEWRKZ_MYSQL_PASS', 'dbpassword')
        
REMOTE_NODES_URL = "https://raw.githubusercontent.com/wrkzcoin/wrkzcoin-nodes-json/master/wrkzcoin-nodes.json"
SLEEP_CHECK = 15  # 15s
NODE_LIVE_LIST = []
REMOTE_NODES_JSON = None

conn = None

# Open Connection
def openConnection():
    global conn
    try:
        if conn is None:
            conn = pymysql.connect(DBHOST, user=DBUSER, passwd=DBPASS, db=DBNAME, charset='utf8', 
                cursorclass=pymysql.cursors.DictCursor, connect_timeout=5)
        elif (not conn.open):
            conn = pymysql.connect(DBHOST, user=DBUSER, passwd=DBPASS, db=DBNAME, charset='utf8mb4', 
            cursorclass=pymysql.cursors.DictCursor, connect_timeout=5)    
    except:
        print("ERROR: Unexpected error: Could not connect to MySql instance.")
        sys.exit()


def insert_nodes(nodelist):
    global conn
    openConnection()
    try:
        with conn.cursor() as cursor:
            sql = """ INSERT INTO `pubnodes_wrkz` (`name`, `url`, `port`, `url_port`, `ssl`, 
                      `cache`, `fee_address`, `fee_fee`, `online`, `version`, `timestamp`, `getinfo_dump`) 
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """
            for each in nodelist:
                list = tuple([value for k, value in each.items()])
                cursor.execute(sql, (list))
            conn.commit()
    finally:
        conn.close()


# Start the work
async def getNodeList():
    global REMOTE_NODES_JSON
    time_out = 10
    async with aiohttp.ClientSession() as session:
        async with session.get(REMOTE_NODES_URL, timeout=time_out) as response:
            try:
                resp = await response.json()
            except Exception as e:
                resp = json.loads(await response.read())
    data = resp['nodes']
    REMOTE_NODES_JSON = data
    node_list = []  # array of nodes
    proto = 'http://'
    for node in data:
        getinfo = None
        getfee = None
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
            node_list.append({
                'name': node['name'],
                'url': node['url'].strip(),
                'port': node['port'],
                'url_port': node['url'].strip().lower() + ':' + str(node['port']),
                'ssl': 1 if node['ssl'] == True else 0,
                'cache': 1 if node['cache'] == True else 0,
                'fee_address': getfee['address'] if 'address' in getfee and len(getfee['address']) == 98 else "",
                'fee_fee': int(getfee['amount']) if 'amount' in getfee else 0,
                'online': 1,
                'version': getinfo['version'],
                'timestamp': int(time.time()),
                'getinfo_dump': json.dumps(getinfo)
                })
        else:
            node_list.append({
                'name': node['name'],
                'url': node['url'].strip(),
                'port': node['port'],
                'url_port': node['url'].strip().lower() + ':' + str(node['port']),
                'ssl': 1 if node['ssl'] == True else 0,
                'cache': 1 if node['cache'] == True else 0,
                'fee_address': "",
                'fee_fee': 0,
                'online': 0,
                'version': "",
                'timestamp': 0,
                'getinfo_dump': ''
                })
    return node_list


async def handle_get_nodelist(request):
    global conn, REMOTE_NODES_URL, REMOTE_NODES_JSON
    time_out = 10
    node_list = []
    if REMOTE_NODES_JSON is None:
        async with aiohttp.ClientSession() as session:
            async with session.get(REMOTE_NODES_URL, timeout=time_out) as response:
                try:
                    resp = await response.json()
                except Exception as e:
                    resp = json.loads(await response.read())
        REMOTE_NODES_JSON = resp['nodes']  
    openConnection()
    try:
        with conn.cursor() as cursor:
            for each in REMOTE_NODES_JSON:
                node = each['url'].strip().lower() + ':' + str(each['port'])
                sql = """ SELECT SUM(`online`) FROM (SELECT `pubnodes_wrkz`.`online`, `pubnodes_wrkz`.`timestamp` 
                          FROM `pubnodes_wrkz` WHERE `pubnodes_wrkz`.`url_port` = %s 
                          ORDER BY `pubnodes_wrkz`.`timestamp` DESC LIMIT 100) AS `availability` """
                cursor.execute(sql, (node))
                node_avail = cursor.fetchone()
                if node_avail:
                    sql = """ SELECT `name`, `url`, `port`, `ssl`, `cache`, `fee_address`, `fee_fee`, `online`, `version`, `timestamp`
                              FROM `pubnodes_wrkz` WHERE `pubnodes_wrkz`.`url_port` = %s 
                              ORDER BY `pubnodes_wrkz`.`timestamp` DESC LIMIT 1 """
                    cursor.execute(sql, (node))
                    node_data = cursor.fetchone()
                    if node_data:
                        node_list.append({
                            'name': node_data['name'],
                            'url': node_data['url'],
                            'port': node_data['port'],
                            'ssl': True if node_data['ssl'] == 1 else False,
                            'cache': True if node_data['cache'] == 1 else False,
                            'fee': {'address': node_data['fee_address'], 'amount': node_data['fee_fee']},
                            'availability': int(node_avail['SUM(`online`)']) or 0,
                            'online': True if node_data['online'] == 1 else False,
                            'version': node_data['version'],
                            'timestamp': node_data['timestamp']
                        })
    finally:
        conn.close()
    response_obj = {"nodes": node_list}
    # json_string = json.dumps(response_obj).replace(" ", "")
    return web.json_response(response_obj, status=200)


# node_check_bg
async def node_check_bg(app):
    global NODE_LIVE_LIST
    tmp_node = []
    while True:
        try:
            try:
                tmp_node = await getNodeList()
                insert_nodes(tmp_node)
            except Exception as e:
                print(e)
            if len(tmp_node) > 0:
                print("==============")
                print("Get total nodes {}.".format(len(tmp_node)))
                print("==============")
            else:
                print('Currently 0 nodes... Sleep {s}'.format(SLEEP_CHECK))
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(SLEEP_CHECK)


async def start_background_tasks(app):
    app['get_node_live'] = asyncio.create_task(node_check_bg(app))


async def cleanup_background_tasks(app):
    app['get_node_live'].cancel()
    await app['get_node_live']


app = web.Application()
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

app.router.add_route('GET', '/list', handle_get_nodelist)

web.run_app(app, host='127.0.0.1', port=8080)
