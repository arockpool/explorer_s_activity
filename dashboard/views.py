import json
import time
import decimal
import datetime
from collections import Iterable

from django.http import HttpResponse

from explorer_s_common.decorator import common_ajax_response
from explorer_s_common.utils import format_return, format_price, format_power, str_2_power, format_fil
from explorer_s_common.page import Page
from explorer_s_common import inner_server, cache
from explorer_s_common.third.filscout_sdk import FilscoutBase
from explorer_s_common.third.filfox_sdk import FilfoxBase

from explorer_s_activity import consts


@common_ajax_response
def get_overview(request):
    '''
    获取统计信息
    '''
    overview = {
        'pool_total_machines': 1000, 'total_power': 0, 'total_power_str': '0',
        'block_reward': 0, 'unit_price': '0.00', 'tipset_height': 0
    }

    data = FilscoutBase(net='spacerace').get_overview()['data']['statistic']
    alteration = float(data['price']['alteration'])
    alteration_str = format_price(alteration)
    alteration_str = '+' + alteration_str if alteration > 0 else alteration_str
    overview.update({
        'total_power': data['power']['power_in_bytes'],
        'total_power_str': format_power(data['power']['power_in_bytes']),
        'block_reward': data['block_reward'],
        'unit_price': '$%s(%s%%)' % (data['price']['unit_price'], alteration_str),
        'tipset_height': data['tipset_height']
    })

    # 获取矿机总数
    cache_obj = cache.Cache()
    # cache_obj.set('pool_total_machines', 999)
    pool_total_machines = cache_obj.get('pool_total_machines') or 1000
    overview.update({'pool_total_machines': pool_total_machines})
    return format_return(0, data=overview)


@common_ajax_response
def get_power_increase(request):
    '''
    获取矿机增长量
    '''
    data = cache.Cache().get(key='7d_power_increase')

    miner_ids = ['f02614', 'f09652', 'f010424', 'f03362', 'f020928', 'f039992']
    for miner_id in miner_ids:
        if miner_id not in data:
            data[miner_id] = 0
    return format_return(0, data=data)


@common_ajax_response
def sync_power_increase(request):
    '''
    同步矿机增长量
    '''
    net = request.POST.get('net', 'spacerace')
    # result = FilfoxBase(net=net).get_power_increase()['miners']
    result = FilscoutBase(net=net).get_miner_increase_ranking()['data']['data']
    if not result:
        return format_return(0)

    data = {}
    for per in result:
        # data[per['address']] = per['equivalentMiners']
        data[per['miner_addr']] = float(per['miner_equivalent'])

    cache_obj = cache.Cache()
    cache_obj.set(key='7d_power_increase', value=data, time_out=2 * 24 * 60 * 60)
    return format_return(0)


@common_ajax_response
def get_pool_miners(request):
    '''
    获取矿池的矿工列表
    '''
    miner_ids = ['f02614', 'f09652', 'f010424', 'f03362', 'f020928', 'f039992']

    pool_total_powers = 0
    pool_total_raw_powers = 0
    pool_total_sectors = 0
    pool_totel_balance = 0
    pool_miners = []
    for per in miner_ids:
        # data = FilscoutBase(net='spacerace').get_miner_by_address(miner_address=per)['data']
        data = FilfoxBase().get_miner_overview(miner_address=per)
        pool_miners.append({
            'miner_id': data['id'],
            'balance': data['balance'],
            'balance_str': format_fil(data['balance']),
            'peer_id': data['miner']['peerId'],
            'power': data['miner']['qualityAdjPower'],
            'power_str': format_power(data['miner']['qualityAdjPower']),
            'raw_power': data['miner']['rawBytePower'],
            'raw_power_str': format_power(data['miner']['rawBytePower']),
            'sector_number': data['miner']['sectors']['live'],
            'proving_sector_number': data['miner']['sectors']['active']
        })

        pool_total_powers += int(data['miner']['qualityAdjPower'])
        pool_total_raw_powers += int(data['miner']['rawBytePower'])
        pool_total_sectors += int(data['miner']['sectors']['live'])
        pool_totel_balance += decimal.Decimal(data['balance'])
    return format_return(0, data={
        'pool_miners': pool_miners,
        'pool_total_powers': pool_total_powers,
        'pool_total_powers_str': format_power(pool_total_powers),
        'pool_total_raw_powers': pool_total_raw_powers,
        'pool_total_raw_powers_str': format_power(pool_total_raw_powers),
        'pool_total_sectors': pool_total_sectors,
        'pool_totel_balance': format_fil(pool_totel_balance)
    })


@common_ajax_response
def get_miner_distribution(request):
    '''
    矿工地图分布
    '''
    data = [
        {'longitude': '-122.331400', 'latitude': '47.609200'},
        {'longitude': '126.782700', 'latitude': '37.498800'},
        {'longitude': '114.266500', 'latitude': '30.585600'},
        {'longitude': '104.066700', 'latitude': '30.666700'},
        {'longitude': '37.606800', 'latitude': '55.738600'},
        {'longitude': '151.184000', 'latitude': '-33.798500'},
        {'longitude': '126.782700', 'latitude': '37.498800'},
    ]
    return format_return(0, data=data)


@common_ajax_response
def get_block_list(request):
    '''
    获取区块列表
    '''
    size = min(int(request.POST.get('size', '10')), 50)
    data = FilscoutBase(net='spacerace').get_block_list()['data']

    block_list_x = data['block_list']
    block_list_y = data['list_series']

    return format_return(0, data={
        'block_list_x': block_list_x, 'block_list_y': block_list_y
    })


@common_ajax_response
def get_ranking(request):
    '''
    获取排行榜
    '''
    # ranking_list = FilscoutBase(net='spacerace').get_ranking()['data'][:10]
    ranking_list = FilfoxBase().get_power_valid()['miners'][:10]
    ranking_list.reverse()
    ranking_x = [x['address'] for x in ranking_list]
    ranking_y = [int(x['qualityAdjPower']) for x in ranking_list]

    return format_return(0, data={
        'ranking_x': ranking_x, 'ranking_y': ranking_y
    })
