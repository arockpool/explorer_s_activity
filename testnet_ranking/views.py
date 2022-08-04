import json
import time
import datetime
from collections import Iterable

from django.http import HttpResponse
from django.db.models import Avg, Q, F, Sum, Count

from explorer_s_common.decorator import common_ajax_response
from explorer_s_common.utils import format_return, format_price
from explorer_s_common.page import Page
from explorer_s_common import inner_server, cache
from explorer_s_common.third.filscout_sdk import FilscoutBase

from explorer_s_activity import consts
from testnet_ranking.interface import RankingBase


@common_ajax_response
def get_ranking(request):
    '''
    获取排名
    '''
    area = request.POST.get('area')
    page_count = min(int(request.POST.get('page_count', 10)), 100)
    page_index = int(request.POST.get('page_index', 1))

    # 矿工
    rmd_miners = {}
    for p in RankingBase().get_rmd_miners(area=area):
        miner = RankingBase().get_miner_by_address(address=p.miner_address)
        if not miner:
            continue
        rmd_miners[p.miner_address] = {
            'miner_address': p.miner_address,
            'ranking': p.ranking,
            'asia_ranking': p.asia_ranking,
            'nick_name': miner.nick_name,
            'increased_power': miner.increased_power,
            'increased_power_str': miner.increased_power_str,
            'raw_byte_power': miner.raw_byte_power,
            'raw_byte_power_str': miner.raw_byte_power_str
        }

    # 矿工
    miners = []
    objs = RankingBase().get_miners(area=area)
    data = Page(objs, page_count).page(page_index)
    for p in data['objects']:
        miners.append({
            'id': p.id, 'miner_address': p.miner_address, 'nick_name': p.nick_name,
            'increased_power': p.increased_power, 'increased_power_str': p.increased_power_str,
            'raw_byte_power': p.raw_byte_power, 'raw_byte_power_str': p.raw_byte_power_str
        })

    # 获取最后更新时间
    last_update_time = RankingBase().get_last_update_time()

    return format_return(0, data={
        'miners': miners, 'rmd_miners': rmd_miners,
        'total_page': data['total_page'],
        'last_update_time': last_update_time.strftime('%Y-%m-%d %H:%M:%S')
    })


@common_ajax_response
def get_block_rate_ranking(request):
    '''
    出块率排行
    '''
    cache_obj = cache.Cache()
    block_rate_ranking = cache_obj.get('block_rate_ranking') or []
    return format_return(0, data=block_rate_ranking)


@common_ajax_response
def get_block_ranking(request):
    '''
    出块排行
    '''
    cache_obj = cache.Cache()
    block_list_ranking = cache_obj.get('block_list_ranking') or []
    for per in block_list_ranking['records']:
        miner = RankingBase().get_miner_by_address(address=per['address'])
        if miner:
            per['power_str'] = miner.increased_power_str
    return format_return(0, data=block_list_ranking)


@common_ajax_response
def get_activity_config(request):
    '''
    获取活动配置
    '''
    config = RankingBase().get_config()
    data = {}
    if config:
        data = {
            'rule': config.rule, 'bhp': format_price(config.bhp), 'fil': format_price(config.fil)
        }

    return format_return(0, data=data)


@common_ajax_response
def get_help_powers(request):
    rmd_user_id = request.POST.get('rmd_user_id')

    user_power = 0
    rmd_user = RankingBase().get_help_records(rmd_user_id=rmd_user_id)
    if rmd_user:
        user_power = rmd_user.aggregate(Sum('power'))['power__sum'] or 0

    totel_power = RankingBase().get_total_help_power()
    return format_return(0, data={
        'user_power': format_price(user_power),
        'totel_power': format_price(totel_power)
    })


@common_ajax_response
def get_help_records(request):
    page_count = max(int(request.POST.get('page_count', 20)), 100)
    page_index = int(request.POST.get('page_index', 1))

    objs = RankingBase().get_help_records()
    data = Page(objs, page_count).page(page_index)
    records = []
    for p in data['objects']:
        records.append({
            'rmd_user_id': p.rmd_user_id, 'rmd_user_nick': p.rmd_user_nick,
            'power': format_price(p.power), 'record_time': p.record_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    return format_return(0, data=records)


@common_ajax_response
def add_help_record(request):
    rmd_user_id = request.POST.get('rmd_user_id')
    rmd_user_nick = request.POST.get('rmd_user_nick')
    power = request.POST.get('power')
    record_time = request.POST.get('record_time')
    order_id = request.POST.get('order_id')

    return RankingBase().add_help_record(
        rmd_user_id=rmd_user_id, rmd_user_nick=rmd_user_nick, power=power,
        record_time=record_time, order_id=order_id
    )


@common_ajax_response
def get_reward_stat(request):
    '''
    获取奖励统计
    '''
    return format_return(0, data=RankingBase().get_reward_stat())


@common_ajax_response
def get_sp2_reward_stat(request):
    '''
    获取sp2奖励统计
    '''
    return format_return(0, data=RankingBase().get_sp2_reward_stat())


@common_ajax_response
def sync_reward_stat(request):
    '''
    同步奖励统计
    '''
    return RankingBase().sync_reward_stat()


@common_ajax_response
def sync_sp2_reward_stat(request):
    '''
    同步sp2奖励统计
    '''
    return RankingBase().sync_sp2_reward_stat()


@common_ajax_response
def sync_data(request):
    return RankingBase().sync_data()


@common_ajax_response
def sync_block_ranking(request):
    return RankingBase().sync_block_ranking()
