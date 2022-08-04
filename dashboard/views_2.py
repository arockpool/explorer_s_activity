import json
import time
import decimal
import datetime
import requests
from collections import Iterable

from django.http import HttpResponse

from explorer_s_common.decorator import common_ajax_response
from explorer_s_common.utils import format_return, format_price, format_power, str_2_power, format_fil, _d
from explorer_s_common.page import Page
from explorer_s_common import inner_server, cache, consts
from explorer_s_common.third.filscout_sdk import FilscoutBase
from explorer_s_common.third.filfox_sdk import FilfoxBase

from calculator.interface import CalculatorBase
from dashboard.interface import DashboardBase


@common_ajax_response
def get_overview(request):
    '''
    获取统计信息
    '''
    overview = {
        'height': 1000, 'total_power_str': '0',
        'block_reward_24': 0, 'total_pledge': 0, 'avg_reward': 0, 'avg_pledge': 0
    }
    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))
    data = CalculatorBase().get_fil_overview(must_update_cache=must_update_cache)
    stat_info = DashboardBase().get_overview(must_update_cache=must_update_cache)

    overview.update({
        'height': data.get('height'),
        'total_power_str': data.get('total_power_str'),
        'block_reward_24': format_fil(data.get('daily_coins_mined'), 2),
        'total_rewards': format_fil(stat_info['total_rewards'], 2),
        'total_pledge': format_fil(data.get('total_pledge_collateral'), 2),
        'avg_reward': format_price(data.get('avg_reward'), 4),
        'avg_pledge': format_price(data.get('avg_pledge'), 4)
    })

    return format_return(0, data=overview)


@common_ajax_response
def get_power_trend(request):
    '''
    获取全网算力趋势
    '''
    days = int(request.POST.get('days', 6))
    data = CalculatorBase().get_fil_overview()

    data = [{
        'date': datetime.datetime.now().strftime('%Y-%m-%d'),
        'power': data.get('total_power'),
        'power_str': format_power(data.get('total_power')),
        'avg_reward': format_price(data.get('avg_reward'), 4)
    }]
    for per in CalculatorBase().get_total_power_day_records()[:days]:
        data.append({
            'date': per.date.strftime('%Y-%m-%d'),
            'power': format_price(per.power, 0),
            'power_str': format_power(per.power),
            'avg_reward': format_price(per.avg_reward, 4)
        })

    return format_return(0, data=data)


@common_ajax_response
def get_miner_ranking(request):
    '''
    获取矿工排名
    '''
    # url = '%s/pool/api/browser/get_miner_ranking' % (consts.SERVER_POOL)
    # result = requests.post(url, data={}, timeout=60).json()
    # return format_return(0, data=result['data']['data'])

    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))
    data = DashboardBase().get_miner_ranking(must_update_cache=must_update_cache)
    return format_return(0, data=data)


@common_ajax_response
def get_block_list(request):
    '''
    获取最新出块信息
    '''
    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))
    data = DashboardBase().get_block_list(must_update_cache=must_update_cache)

    return format_return(0, data=data)


@common_ajax_response
def get_power_distribution(request):
    '''
    获取算力分布
    '''
    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))
    data = DashboardBase().get_power_distribution(must_update_cache=must_update_cache)
    return format_return(0, data=data)


@common_ajax_response
def get_pool_overview(request):
    '''
    获取矿池信息
    '''
    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))
    fil_overview = inner_server.get_net_ovewview()['data']

    pool_overview = DashboardBase().get_pool_overview(must_update_cache=must_update_cache)
    pool_overview.update({
        'price': format_price(fil_overview.get('price')), 'location': '四大洲九大区域'
    })
    return format_return(0, data=pool_overview)


@common_ajax_response
def get_pool_miners(request):
    '''
    获取矿池矿工
    '''
    area_dict = {'AS': '亚洲', 'OC': '大洋洲', 'EU': '欧洲', 'AF': '非洲', 'NA': '南美洲', 'SA': '北美洲', 'AN': '南极洲'}

    page_index = int(request.POST.get('page_index', 1))
    page_size = min(int(request.POST.get('page_size', 10)), 500)
    sector_type = request.POST.get('sector_type')
    records = []

    objs = DashboardBase().get_pool_miners(sector_type=sector_type).order_by('-power')
    data = Page(objs, page_size).page(page_index)

    for per in data['objects']:
        records.append({
            'miner_address': per.miner_address,
            'power': format_power(per.power),
            'power_v': per.power,
            'increase_power': format_power(per.increase_power),
            'increase_power_v': per.increase_power,
            'increase_power_offset': format_power(per.increase_power_offset),
            'increase_power_offset_v': per.increase_power_offset,
            'luck': format_price(per.luck, 4),
            'sector_size': per.sector_size,
            'sector_size_str': format_power(per.sector_size),
            'area': per.area or 'N/A'
        })

    return format_return(0, data={
        'objs': records, 'total_page': data['total_page'], 'total_count': data['total_count']
    })


@common_ajax_response
def get_pool_trend(request):
    '''
    获取趋势
    '''
    days = int(request.POST.get('days', 7))
    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))

    data = DashboardBase().get_pool_trend(days, must_update_cache=must_update_cache)
    return format_return(0, data=data)


@common_ajax_response
def get_pool_mines(request):

    miners_dict = dict([(per.miner_address, per.power) for per in DashboardBase().get_pool_miners()])

    data = [{
        'name': '成都数据中心', 'scale': '313000平米', 'frames': '25000', 'machines': '313',
        'total_power': format_power(miners_dict.get('f02614', 0) + miners_dict.get('f09652', 0) + miners_dict.get('f020928', 0) + miners_dict.get('f0104654', 0)),
        'img': 'https://jackandme1.oss-cn-chengdu.aliyuncs.com/dashboard__chengdu_mine.jpg',
        'longitude': 104.07217, 'latitude': 30.664022
    }, {
        'name': '宁夏中卫数据中心', 'scale': '400000平米', 'frames': '25000', 'machines': '172',
        'total_power': format_power(miners_dict.get('f039992', 0) + miners_dict.get('f0100033', 0)),
        'img': 'https://jackandme1.oss-cn-chengdu.aliyuncs.com/dashboard__ningxia_mine.jpg',
        'longitude': 106.236286, 'latitude': 38.489532
    }, {
        'name': '雅安数据中心', 'scale': '76000平米', 'frames': '10000', 'machines': '119',
        'total_power': format_power(miners_dict.get('f082095', 0) + miners_dict.get('f096087', 0) + miners_dict.get('f095970', 0) + miners_dict.get('f096072', 0)),
        'img': 'https://jackandme1.oss-cn-chengdu.aliyuncs.com/dashboard__yaan_mine.jpg?v=1',
        'longitude': 102.29, 'latitude': 27.92
    }, {
        'name': '澳洲数据中心', 'scale': '700平方米', 'frames': '300', 'machines': '33',
        'total_power': format_power(miners_dict.get('f010424', 0)),
        'img': 'https://jackandme1.oss-cn-chengdu.aliyuncs.com/dashboard__aozhou_mine.jpg',
        'longitude': 133.922314, 'latitude': -25.341295
    }, {
        'name': '欧洲数据中心', 'scale': '60000平米', 'frames': '20000', 'machines': '38',
        'total_power': format_power(miners_dict.get('f03362', 0)),
        'img': 'https://jackandme1.oss-cn-chengdu.aliyuncs.com/dashboard__ouzhou_mine.jpg',
        'longitude': -1.755245, 'latitude': 36.623451
    }, {
        'name': '青海共和数据中心', 'scale': '53000平米', 'frames': '6800', 'machines': '38',
        'total_power': format_power(miners_dict.get('f03362', 0)),
        'img': 'https://jackandme1.oss-cn-chengdu.aliyuncs.com/dashboard__qinghai_mine.jpg',
        'longitude': 101.829002, 'latitude': 36.593785
    }, {
        'name': '内蒙数据中心', 'scale': '648000平米', 'frames': '2453', 'machines': '38',
        'total_power': format_power(miners_dict.get('f03362', 0)),
        'img': 'https://jackandme1.oss-cn-chengdu.aliyuncs.com/dashboard__neimeng_mine.jpg',
        'longitude': 111.746735, 'latitude': 40.848919
    }]
    return format_return(0, data=data)


@common_ajax_response
def get_pool_last_block_info(request):
    '''
    获取矿池最新出块信息
    '''
    data = DashboardBase().get_block_list()

    miners = []
    for per in DashboardBase().get_pool_miners():
        miners.append(per.miner_address)

    is_break = False
    block_miner = []

    for tipset in data['tipsets']:
        for block in tipset['blocks']:
            if block['miner_address'] in miners:
                block_miner = {'miner_address': block['miner_address'], 'block_time': block['block_time']}
                is_break = True
                break
        if is_break:
            break

    return format_return(0, data=block_miner)


@common_ajax_response
def sync_day_pool_overview(request):
    '''
    同步每天数据
    '''
    return DashboardBase().sync_day_pool_overview()
