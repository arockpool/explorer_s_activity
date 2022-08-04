import time
import math
import json
import logging
import decimal
import requests
import datetime
from lxml import etree

from django.db import transaction
from django.db.models import Avg, Q, F, Sum, Count

from explorer_s_common import debug, consts, cache, raw_sql, inner_server
from explorer_s_common.utils import format_return, Validator, format_power, format_price, format_fil, \
    str_2_power, format_fil_to_decimal, _d
from explorer_s_common.decorator import validate_params, cache_required
from explorer_s_common.third.filfox_sdk import FilfoxBase
from explorer_s_common.third.filscout_sdk import FilscoutBase
from explorer_s_common.third.filscan_sdk import FilscanBase
from explorer_s_common.third.bbhe_sdk import BbheBase
from explorer_s_common.third.fam_sdk import FamBase

from explorer_s_activity.consts import ERROR_DICT
from dashboard.models import PoolMiner, PoolMinerDay


class DashboardBase(object):

    @cache_required(cache_key='dashboard_overview', expire=12 * 60 * 60)
    def get_overview(self, must_update_cache=False):
        from calculator.interface import TipsetBase
        return {'total_rewards': TipsetBase().get_total_rewards()}

    @cache_required(cache_key='dashboard_block_list', expire=12 * 60 * 60)
    def get_block_list(self, must_update_cache=False):

        result = FilscanBase().get_block_list()
        if not result:
            return {}

        tipsets = []
        for per in result['result']['tipsets']:
            blocks = []
            for block in per['blocks']:
                blocks.append({
                    'miner_address': block['miner'], 'win_count': block['win_count'], 'block_time': block['block_time']
                })
            tipsets.append({
                'height': per['height'],
                'blocks': blocks
            })

        miners = []
        # result = FilscoutBase().get_rank_power_list(page_size=60)
        # for per in result['data']['miners']:
        #     miners.append({
        #         'miner_address': per['miner'],
        #         'block_rate': per['block_rate'],
        #         'block_ratio': per['block_ratio'],
        #         'win_count': per['win_count'],
        #         'win_count_ratio': per['win_count_ratio']
        #     })
        return {'tipsets': tipsets, 'miners': miners}

    @cache_required(cache_key='dashboard_power_distribution', expire=12 * 60 * 60)
    def get_power_distribution(self, must_update_cache=False):
        result = FilscanBase().get_power_distribution()
        if not result:
            return {}

        result = result['result']['rate']
        data = {
            'africa': result['africa'] * 100,
            'asia': result['asia'] * 100,
            'europe': result['europe'] * 100,
            'north_america': result['north america'] * 100,
            'oceania': result['oceania'] * 100,
            'south_america': result['south america'] * 100
        }
        return data

    @cache_required(cache_key='dashboard_pool_miner_info', expire=12 * 60 * 60)
    def get_pool_overview(self, must_update_cache=False):

        self.sync_pool_miners()

        # 先同步数据
        for miner_address in [x.miner_address for x in PoolMiner.objects.all()]:

            result = inner_server.get_miner_by_no({'miner_no': miner_address})
            if not result or not result['data']:
                continue

            miner, created = PoolMiner.objects.get_or_create(miner_address=miner_address)
            miner.power = result['data']['power']
            miner.increase_power = result['data']['increase_power_24']
            miner.increase_power_offset = result['data']['increase_power_offset_24']
            miner.total_reward = format_fil_to_decimal(result['data']['total_reward'])
            miner.avg_reward = result['data']['avg_reward']
            miner.luck = result['data']['lucky']
            miner.total_block_count = result['data']['total_block_count']
            miner.total_win_count = result['data']['total_win_count']
            miner.sector_size = result['data']['sector_size']
            miner.reward = format_fil_to_decimal(result['data']['block_reward'])
            miner.block_count = result['data']['block_count']
            miner.ip = ''
            miner.area = ''
            miner.save()

        miners_count = 0
        active_miners_count = 0
        total_power = 0
        total_reward = 0
        reward = 0
        increase_power = 0
        increase_power_offset = 0
        avg_reward = 0
        total_block_count = 0
        block_count = 0
        total_win_count = 0
        for miner in PoolMiner.objects.all():
            miners_count += 1
            if miner.power > 0:
                active_miners_count += 1
            total_power += miner.power
            total_reward += miner.total_reward
            increase_power += miner.increase_power
            increase_power_offset += miner.increase_power_offset
            avg_reward += miner.avg_reward
            total_block_count += miner.total_block_count
            total_win_count += miner.total_win_count
            reward += miner.reward
            block_count += miner.block_count

        return {
            'miners_count': miners_count,
            'active_miners_count': active_miners_count,
            'total_power': format_power(total_power),
            'total_power_v': total_power,
            'total_reward': total_reward,
            'reward': reward,
            'increase_power': format_power(increase_power),
            'increase_power_v': increase_power,
            'increase_power_offset': format_power(increase_power_offset),
            'increase_power_offset_v': increase_power_offset,
            'avg_reward': format_price(avg_reward / miners_count, 4),
            'total_block_count': total_block_count,
            'block_count': block_count,
            'total_win_count': total_win_count
        }

    def get_pool_miners(self, sector_type=None):
        objs = PoolMiner.objects.filter(power__gt=0)
        if sector_type is not None:
            objs = objs.filter(sector_size=34359738368 if str(sector_type) == '0' else 68719476736)
        return objs

    @cache_required(cache_key='dashboard_pool_trend_%s', expire=10 * 60)
    def get_pool_trend(self, days=7, must_update_cache=False):

        start_date = datetime.datetime.now() - datetime.timedelta(days=days - 1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        data = {}
        for per in PoolMinerDay.objects.filter(date__gte=start_date).order_by('date'):
            key = per.date.strftime('%Y-%m-%d')
            if key not in data:
                data[key] = {'power': 0, 'avg_rewards': [], 'increase_powers': [], 'increase_power': 0, 'total_block_count': 0, 'total_win_count': 0}

            data[key]['power'] += per.power
            data[key]['power_str'] = format_power(data[key]['power'])

            data[key]['avg_rewards'].append(float(per.avg_reward))
            data[key]['avg_reward'] = sum(data[key]['avg_rewards']) / len(data[key]['avg_rewards'])

            data[key]['increase_powers'].append({
                'miner_address': per.miner_address,
                'increase_power': float(per.increase_power)
            })
            data[key]['increase_power'] += float(per.increase_power)
            data[key]['increase_power_str'] = format_power(data[key]['increase_power'])

            data[key]['total_block_count'] += per.total_block_count
            data[key]['total_win_count'] += per.total_win_count

        current_data = {'power': 0, 'avg_rewards': [], 'increase_powers': [], 'increase_power': 0, 'total_block_count': 0, 'total_win_count': 0}
        # 获取当前的数据
        for per in PoolMiner.objects.filter():

            current_data['power'] += per.power
            current_data['power_str'] = format_power(current_data['power'])

            current_data['avg_rewards'].append(float(per.avg_reward))
            current_data['avg_reward'] = sum(current_data['avg_rewards']) / len(current_data['avg_rewards'])

            current_data['increase_powers'].append({
                'miner_address': per.miner_address,
                'increase_power': float(per.increase_power)
            })
            current_data['increase_power'] += float(per.increase_power)
            current_data['increase_power_str'] = format_power(current_data['increase_power'])
            current_data['total_block_count'] += per.total_block_count
            current_data['total_win_count'] += per.total_win_count
        data[datetime.datetime.now().strftime('%Y-%m-%d')] = current_data
        return data

    @cache_required(cache_key='dashboard_miner_ranking', expire=12 * 60 * 60)
    def get_miner_ranking(self, must_update_cache=False):
        '''
        获取矿工排名
        '''
        result = inner_server.get_miner_list({'page_size': 20})

        data = []
        total_power = _d(inner_server.get_net_ovewview()['data']['power'])
        for per in result['data']['objs']:
            data.append({
                'miner_address': per['miner_no'],
                'nick_name': '',
                'power': int(per['power']),
                'power_str': format_power(per['power']),
                'raw_power': int(per['raw_power']),
                'raw_power_str': format_power(per['raw_power']),
                'power_rate': format_price(_d(per['power']) / total_power * 100)
            })

        return data

    def sync_day_pool_overview(self):
        '''
        每天0点同步数据到这张表
        '''
        now = datetime.datetime.now().strftime('%Y-%m-%d') + ' 00:00:00'
        data = self.get_pool_overview(must_update_cache=True)

        for per in PoolMiner.objects.all():
            obj, created = PoolMinerDay.objects.get_or_create(date=now, miner_address=per.miner_address)
            obj.power = per.power
            obj.increase_power = per.increase_power
            obj.increase_power_offset = per.increase_power_offset
            obj.total_reward = per.total_reward
            obj.avg_reward = per.avg_reward
            obj.luck = per.luck
            obj.total_block_count = per.total_block_count
            obj.total_win_count = per.total_win_count
            obj.save()
        return format_return(0)

    def sync_pool_miners(self):
        '''同步矿池矿工'''
        # data = inner_server.get_miner_list({'is_pool': 1, 'page_size': 1000})
        # for per in data['data']['objs']:
        #     obj, created = PoolMiner.objects.get_or_create(miner_address=per['miner_no'])

        pool_miners = FamBase().get_pool_miners()['data']

        for per in PoolMiner.objects.all():
            if per.miner_address not in pool_miners:
                per.delete()

        for per in pool_miners:
            obj, created = PoolMiner.objects.get_or_create(miner_address=per)
