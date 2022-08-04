import os
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
from explorer_s_common.utils import format_return, Validator, format_power, format_price, format_fil, str_2_power
from explorer_s_common.decorator import validate_params, cache_required
from explorer_s_common.third.filfox_sdk import FilfoxBase
from explorer_s_common.third.filscout_sdk import FilscoutBase
from explorer_s_common.third.filscan_sdk import FilscanBase
from explorer_s_common.third.bbhe_sdk import BbheBase

from explorer_s_activity.consts import ERROR_DICT
from calculator.models import TotalPower, Tipset, TipsetBlock, SearchLog, TotalPowerDay, \
    TempTipsetBlock, GasFeeDay


class CalculatorBase(object):

    def add_total_power(self, record_time, power=0, increase_power=0, block_reward=0, avg_reward=0,
                        avg_pledge=0, total_supply=0, circulating_supply=0, burnt_supply=0,
                        total_pledge_collateral=0, total_multisig_locked_balance=0,
                        total_market_pledge=0, price=0, avg_tipset_blocks=0, pre_commit_sector_total_gas=0,
                        prove_commit_sector_total_gas=0, submit_windowed_po_st_total_gas=0, base_fee=0):
        obj, created = TotalPower.objects.get_or_create(record_time=record_time)
        obj.power = power
        obj.increase_power = increase_power
        obj.block_reward = block_reward
        obj.avg_reward = avg_reward
        obj.avg_pledge = avg_pledge
        obj.total_supply = total_supply
        obj.circulating_supply = circulating_supply
        obj.burnt_supply = burnt_supply
        obj.total_pledge_collateral = total_pledge_collateral
        obj.total_multisig_locked_balance = total_multisig_locked_balance
        obj.total_market_pledge = total_market_pledge
        obj.price = price
        obj.avg_tipset_blocks = avg_tipset_blocks
        obj.pre_commit_sector_total_gas = pre_commit_sector_total_gas
        obj.prove_commit_sector_total_gas = prove_commit_sector_total_gas
        obj.submit_windowed_po_st_total_gas = submit_windowed_po_st_total_gas
        obj.base_fee = base_fee
        obj.save()

        # 按天统计
        date = record_time - datetime.timedelta(days=1)
        temp, created = TotalPowerDay.objects.get_or_create(date=date.strftime('%Y-%m-%d'))
        if created:
            temp.power = power
            temp.increase_power = increase_power
            temp.avg_reward = avg_reward
            temp.avg_pledge = avg_pledge
            temp.burnt_supply = burnt_supply
            temp.base_fee = base_fee
            temp.circulating_supply = circulating_supply
            temp.pre_commit_sector_total_gas = pre_commit_sector_total_gas
            temp.prove_commit_sector_total_gas = prove_commit_sector_total_gas
            temp.submit_windowed_po_st_total_gas = submit_windowed_po_st_total_gas
        temp.luck = LookupBase().get_luck_v(date=date)
        temp.save()
        return format_return(0, data={'obj_id': obj.id})

    def sync_total_power_day_record(self, date):
        '''更新每日数据，主要是从日报更新全网算力、算力增量、gas消耗'''
        result = BbheBase().get_net_stat(date=date)
        if not result:
            return None

        obj, created = TotalPowerDay.objects.get_or_create(date=date)
        obj.power = result['data']['actualPower']
        obj.increase_power = result['data']['dayPowerNetIncr']
        obj.create_gas = result['data']['dayPackingGasFee32'] + result['data']['dayPackingGasFee64']
        obj.keep_gas = result['data']['dayPostMaintainGasFee32'] + result['data']['dayPostMaintainGasFee64']
        obj.packing_power = _d(result['data']['dayPackingNum']) * _d(1024**4)
        obj.save()
        return format_return(0)

    def get_total_power_day_records(self):
        return TotalPowerDay.objects.filter()

    def get_current_total_power(self):
        return TotalPower.objects.filter()[0]

    def get_increase_power_per_day(self):
        # 取出现在的总算力
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        records = TotalPower.objects.filter(record_time__lte=now)
        if not records:
            return 10 * 1024 * 1024 * 1024 * 1024 * 1024
        now_power = records[0].power

        # 取出24小时以前的总算力
        yesterday = now - datetime.timedelta(hours=24)
        records = TotalPower.objects.filter(record_time__lte=yesterday)
        if not records:
            return 10 * 1024 * 1024 * 1024 * 1024 * 1024
        yesterday_power = records[0].power
        return now_power - yesterday_power

    @cache_required(cache_key='calculator_usd_rate', expire=1800 * 1)
    def get_usd_rate(self, must_update_cache=False):
        '''
        获取美元汇率
        '''
        rate = 6.68
        try:
            res = requests.get('https://api.exchangerate-api.com/v4/latest/USD').json()
            rate = res.get('rates', {}).get('CNY', 6.68)
        except Exception as e:
            print(e)
        return rate

    @cache_required(cache_key='calculator_fil_overview', expire=30 * 60)
    def get_fil_overview(self, must_update_cache=False):
        '''
        获取fil数据
        '''

        result = inner_server.get_net_ovewview()
        if not result:
            return None
        result = result['data']
        overview = {
            'height': result['height'],
            'avg_reward': format_price(result['avg_reward'], 4),
            'avg_pledge': format_price(result['avg_pledge'], 4),
            'total_power': result['power'],
            'total_power_str': format_power(result['power']),
            'block_reward': result['block_reward'],
            'block_reward_str': format_fil(result['block_reward']),
            'circulating_supply': result['circulating_supply'],
            'circulating_supply_str': format_fil(result['circulating_supply']),
            'price': format_price(result['price']),
            'avg_tipset_blocks': result['avg_tipset_blocks'],
            'total_supply': '0',
            'burnt_supply': result['burnt_supply'],
            'total_pledge_collateral': result['total_pledge'],
            'total_multisig_locked_balance': '0',
            'total_market_pledge': '0',
            'daily_coins_mined': result['block_reward_24_hour']
        }
        return overview

    @cache_required(cache_key='calculator_gas_stat', expire=30 * 60)
    def get_gas_stat(self, must_update_cache=False):
        '''
        获取gas统计
        '''
        result = inner_server.get_gas_stat_all()
        if not result:
            return None

        gas_stat = {
            'prove_commit_sector': 0, 'pre_commit_sector': 0, 'submit_windowed_po_st': 0,
            'avg_prove_commit_sector': 0, 'avg_pre_commit_sector': 0, 'avg_submit_windowed_po_st': 0
        }

        for key in result['data']:
            per = result['data'][key]
            if key == 'ProveCommitSector':
                gas_stat['prove_commit_sector'] = _d(per['total_cost']) / _d(math.pow(10, 18))
                gas_stat['avg_prove_commit_sector'] = _d(per['avg_cost']) / _d(math.pow(10, 18))
            if key == 'PreCommitSector':
                gas_stat['pre_commit_sector'] = _d(per['total_cost']) / _d(math.pow(10, 18))
                gas_stat['avg_pre_commit_sector'] = _d(per['avg_cost']) / _d(math.pow(10, 18))
            if key == 'SubmitWindowedPoSt':
                gas_stat['submit_windowed_po_st'] = _d(per['total_cost']) / _d(math.pow(10, 18))
                gas_stat['avg_submit_windowed_po_st'] = _d(per['avg_cost']) / _d(math.pow(10, 18))

        return gas_stat

    def get_avg_gas(self):
        '''
        获取7天平均的汽油费
        '''
        days = 7

        pre_commit_sector_total_gas = 0
        prove_commit_sector_total_gas = 0
        submit_windowed_po_st_total_gas = 0

        objs = TotalPower.objects.filter(pre_commit_sector_total_gas__gt=0)[:days * 24]
        if not objs:
            return self.get_gas_stat()

        for per in objs:
            pre_commit_sector_total_gas += per.pre_commit_sector_total_gas
            prove_commit_sector_total_gas += per.prove_commit_sector_total_gas
            submit_windowed_po_st_total_gas += per.submit_windowed_po_st_total_gas

        return {
            'prove_commit_sector': prove_commit_sector_total_gas / objs.count(),
            'pre_commit_sector': pre_commit_sector_total_gas / objs.count(),
            'submit_windowed_po_st': submit_windowed_po_st_total_gas / objs.count(),
        }

    def get_base_fee(self):
        result = inner_server.get_base_fee_trends()
        if not result:
            return 0

        sum_base_fee = sum([decimal.Decimal(x.get('base_fee', 0)) for x in result['data']])
        return decimal.Decimal(sum_base_fee / len(result['data']))

    def sync_increase_power_per_day(self):
        '''
        同步每日算力增量
        '''

        # ================== filfox 数据
        page_index = 0
        increase_power = decimal.Decimal(0)
        while page_index <= 10:
            result = FilfoxBase().get_power_increase(page_index=page_index, page_size=100, duration='24h')
            for per in result.get('miners', []) or []:
                # print(per.get('address'), '-->', per.get('qualityAdjPowerDelta'))
                increase_power += decimal.Decimal(per.get('qualityAdjPowerDelta', 0))

            time.sleep(1)
            page_index += 1
        print('filfox 数据-->' + format_power(increase_power))

        # ================== filscout 数据
        # page_index = 0
        # increase_power = decimal.Decimal(0)
        # while page_index <= 10:
        #     result = FilscoutBase().get_miner_list(page_index=page_index, page_size=100)
        #     for per in result.get('data', {}).get('data', []) or []:
        #         # print(per.get('miner_address'), '-->', per.get('power_growth_str', '0 bytes'))
        #         increase_power += str_2_power(per.get('power_growth_str', '0 bytes'))

        #     time.sleep(1)
        #     page_index += 1
        # print('filscout 数据-->' + format_power(increase_power))

        # ================== filscan 数据
        # page_index = 0
        # increase_power = decimal.Decimal(0)
        # while page_index <= 5:
        #     result = FilscanBase().get_miner_increase(page_index=page_index, page_size=200)
        #     for per in result.get('result', {}).get('data', []) or []:
        #         # print(per.get('miner'), '-->', format_power(per.get('increased', '0')))
        #         increase_power += decimal.Decimal(per.get('increased', '0'))

        #     time.sleep(1)
        #     page_index += 1
        # print('filscan 数据-->' + format_power(increase_power))
        return increase_power

    def get_day_reward_per_t(self, current_day, increase_power_per_day=10, current_net_power=569, avg_tipset_blocks=5):
        '''
        获取当日单T收益
        '''
        _opt = {
            'VestedReleasePerYear': 50000000 + 16666666 + 50000000 + 5373603,
            'totalPowerP_Grow_perDayLimit': increase_power_per_day,
            'totalPowerBaseLineEB': 2.5,
            'MainNetFromBlock': 148888,
            'MainNetFromPower': current_net_power,
            'avgWinCount': avg_tipset_blocks
        }
        opt = {
            'totalPowerGBBaseLine': _opt['totalPowerBaseLineEB'] * 1024 * 1024 * 1024,
            'avgWinCount': _opt['avgWinCount'],
        }

        def getSimpleBlockReward(blockNum):
            '''
            全网总算力大于2.5EiB，则直接返回770000000，否则返回330000000
            '''
            T = blockNum / 2880
            tempReward = 330000000

            if current_net_power > (_opt['totalPowerBaseLineEB'] * 1024.0):
                tempReward = 770000000

            return tempReward * math.exp(-1.09897764548444e-7 * ((T * 2880 + 1) - 1)) * (1.09897764548444e-7) / 5

        def getBaseLineBlockReward(blockNum):
            T = blockNum / 2880
            baselineBlockReword = 0.1586 * T - 0.041
            return baselineBlockReword / (opt['totalPowerGBBaseLine'] / 1024 / 1024 / 1024)

        @cache_required(cache_key='day_block_reward_%s', expire=7 * 24 * 60 * 60, cache_key_type=1)
        def getDayBlockReward(day):
            _dayBlockReward = 0
            for i in range(_opt['MainNetFromBlock'] + 2880 * (day - 1), _opt['MainNetFromBlock'] + 2880 * day):
                _dayBlockReward += decimal.Decimal(getSimpleBlockReward(i) + getBaseLineBlockReward(i)) * _opt['avgWinCount']

            return _dayBlockReward

        _dayBlockReward = getDayBlockReward(current_day)

        # 当前主网算力和算力增速统一按PiB计算，然后换算成TiB
        # _dayMainNetPower = (_opt['MainNetFromPower'] + _opt['totalPowerP_Grow_perDayLimit']) * 1024
        _dayMainNetPower = (_opt['MainNetFromPower'] + _opt['totalPowerP_Grow_perDayLimit'] * current_day) * 1024
        return decimal.Decimal(_dayBlockReward / _dayMainNetPower)

    def get_create_gas(self, day, data, package_days, create_cost_gas_per_t):
        '''
        获取当日创建的gas费
        '''
        gas = 0
        for per in data:
            if per['day'] > day:
                break

            # 是否有新增
            if per['today_new_power'] > 0:
                gas = per['today_new_power'] * create_cost_gas_per_t

        return gas

    def get_today_release(self, day, data, release_days):
        '''
        获取当日释放
        '''
        total = 0
        for per in data:
            if per['day'] >= day:
                break
            # 只取180天以内数据
            if (day - release_days) < per['day'] and per['day'] < day:
                total += per['today_reward'] * decimal.Decimal(0.75) / decimal.Decimal(release_days)
        return total

    def get_today_release_principal(self, day, data, package_days):
        '''
        获取当日释放本金
        '''

        principal = 0
        for per in data:
            if per['day'] == (day - package_days):
                principal = per['today_pledge']
                break
        return principal

    def get_total_pledge(self, day, data):
        '''
        获取累计质押
        '''
        total = 0
        for per in data:
            if per['day'] > day:
                break
            total += per['today_pledge']
        return total

    def get_total_reward(self, day, data):
        '''
        获取累计奖励
        '''
        total = 0
        for per in data:
            if per['day'] > day:
                break
            total += per['today_reward']
        return total

    def get_total_release(self, day, data):
        '''
        获取累计释放
        '''
        total = 0
        for per in data:
            if per['day'] > day:
                break
            total += per['today_release']
        return total

    def get_total_release_principal(self, day, data):
        '''
        获取累计释放本金
        '''
        total = 0
        for per in data:
            if per['day'] > day:
                break
            total += per['today_release_principal']
        return total

    def get_day_net_power_p(self, current_date, increase_power_per_day):
        '''
        获取当天的算力
        '''
        current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        objs = TotalPower.objects.filter(record_time=current_date)
        if objs:
            return decimal.Decimal(format_power(objs[0].power, 'PiB').strip('PiB'))

        # 如果没有从历史表找到，则需要计算
        now_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        objs = TotalPower.objects.filter(record_time__lte=now_date)
        now_net_power = decimal.Decimal(format_power(objs[0].power, 'PiB').strip('PiB'))
        return now_net_power + decimal.Decimal((current_date - now_date).days * increase_power_per_day)

    def generate_lookup(self, current_date, power_per_day=2, total_power=120, increase_power_per_day=10, init_power=0, luck_v='0.997', is_merge=True, direct_avg_reward_dict=None):
        '''
        生成对照表
        '''
        # today_reward_per_day = decimal.Decimal(0.2121)
        # today_pledge_per_day = decimal.Decimal(6.3104)
        _time_start = time.time()
        start_date = datetime.datetime(2020, 10, 16)
        change_date = datetime.datetime(2020, 12, 17)
        now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        run_days = (current_date - start_date).days
        overview = self.get_fil_overview()
        today_pledge_per_day = decimal.Decimal(overview.get('avg_pledge')) * 32
        avg_tipset_blocks = decimal.Decimal(overview.get('avg_tipset_blocks', 5))
        increase_power_per_day = decimal.Decimal(increase_power_per_day)

        # =============================================================
        # gas_stat = self.get_gas_stat()
        # print('gas_stat-->', gas_stat)
        # # 生产单T消耗gas
        # create_cost_gas_per_t = (gas_stat['avg_prove_commit_sector'] + gas_stat['avg_pre_commit_sector']) * _d(32)
        # print('create_cost_gas_per_t:', create_cost_gas_per_t)
        # # 维护单T消耗gas
        # current_net_power_t = decimal.Decimal(format_power(overview.get('total_power'), 'TiB').strip('TiB')) - increase_power_per_day * 1024
        # keep_cost_gas_per_t = gas_stat['submit_windowed_po_st'] / current_net_power_t
        # print('keep_cost_gas_per_t:', keep_cost_gas_per_t)
        # =============================================================
        gas_info_32 = inner_server.get_gas_cost_stat({'sector_type': '0'}).get('data', {})
        create_cost_gas_per_t = _d(gas_info_32['create_gas'])
        keep_cost_gas_per_t = _d(gas_info_32['keep_gas'])
        gas_info_64 = inner_server.get_gas_cost_stat({'sector_type': '1'}).get('data', {})
        create_cost_gas_per_t_64 = _d(gas_info_64['create_gas'])
        keep_cost_gas_per_t_64 = _d(gas_info_64['keep_gas'])

        # 每日奖励预测的对照
        avg_reward_lookups_dict = {}
        avg_pledge_lookups_dict = {}
        if not direct_avg_reward_dict:
            cache_key = '%s_%.2f' % (luck_v, increase_power_per_day)
            print('cache_key-->', cache_key)
            _offset_days = (current_date - now).days
            if is_merge:
                avg_reward_lookups = LookupBase().get_lookups(cache_key, luck_v=luck_v, increase_power=increase_power_per_day, days=541 + _offset_days, must_update_cache=True if _offset_days > 0 else False)
            else:
                avg_reward_lookups = LookupBase().get_lookups(cache_key, luck_v=luck_v, increase_power=increase_power_per_day, days=541 + _offset_days, must_update_cache=True)
            avg_reward_lookups_dict = dict([(x['date'].strftime('%Y-%m-%d'), x['avg_reward']) for x in avg_reward_lookups])
            avg_pledge_lookups_dict = dict([(x['date'].strftime('%Y-%m-%d'), x['avg_pledge']) for x in avg_reward_lookups])

        # 天数
        days = 541
        # 当日新增算力
        power_per_day = power_per_day
        # 新增封装天数
        package_days = 540
        # 释放天数
        release_days = 180
        # 当日新增算力
        today_new_power = 0
        # 当日有效算力
        today_power = 0
        # 总算力
        total_power = total_power
        # 当日质押量
        today_pledge = 0
        # 当日基础挖矿奖励
        today_reward_base = 0
        # 当日挖矿奖励
        today_reward = 0
        # 当日释放奖励
        today_release = 0
        # 当日释放本金
        today_release_principal = 0
        # 总质押
        total_pledge = 0
        # 总奖励
        total_reward = 0
        # 总释放
        total_release = 0
        # 总释放本金
        total_release_principal = 0

        data = []
        for i in range(1, days):

            index = i % package_days
            #======== 当日新增算力
            today_new_power = power_per_day
            if index > ((total_power - init_power) / power_per_day):
                if (init_power + power_per_day * (index - 1)) > total_power:
                    today_new_power = total_power - init_power - power_per_day * (index - 2)  # power_per_day - (power_per_day * (index - 1) - total_power)
                    today_new_power = max(today_new_power, 0)
                elif (init_power + power_per_day * (index - 1)) == total_power:
                    today_new_power = 0
                else:
                    today_new_power = power_per_day

            #======== 当日有效算力
            today_power = (init_power + power_per_day * index) - power_per_day
            today_power = min(today_power, total_power)

            if index == 0:
                today_new_power = 0
                today_power = total_power

            # 大于540天开始重新封装
            if i > package_days and index != 0:
                if i <= (package_days * math.floor(i / package_days) + (total_power / power_per_day)):
                    today_power = total_power - power_per_day
                else:
                    today_new_power = 0
                    today_power = total_power

            #======== 当日质押量
            temp_date = current_date + datetime.timedelta(days=i - 1)
            temp_date_str = temp_date.strftime('%Y-%m-%d')
            pledge_per_day = avg_pledge_lookups_dict.get(temp_date_str)
            # 正式服或者没有取到对照，则用老算法
            if pledge_per_day and os.getenv('DEVCODE', 'dev') != 'prod':
                today_pledge_per_day = pledge_per_day
            if today_new_power > 0:
                today_pledge = decimal.Decimal(today_new_power) * decimal.Decimal(today_pledge_per_day)
            else:
                today_pledge = 0

            #======== 当日挖矿奖励: 区块奖励-新增生产消耗gas-存量维护gas
            reward_per_day = None
            # 是否指定单日奖励
            if direct_avg_reward_dict:
                reward_per_day = direct_avg_reward_dict[i - 1]
            else:
                # _current_date = current_date + datetime.timedelta(days=i - 1)
                # current_net_power_p = self.get_day_net_power_p(current_date=_current_date, increase_power_per_day=decimal.Decimal(10))
                temp_date = current_date + datetime.timedelta(days=i - 1)
                temp_date_str = temp_date.strftime('%Y-%m-%d')
                reward_per_day_new = avg_reward_lookups_dict.get(temp_date_str, 0)

                reward_per_day_old = self.get_day_reward_per_t(
                    current_day=i + run_days, increase_power_per_day=decimal.Decimal(11.6),
                    current_net_power=decimal.Decimal(569), avg_tipset_blocks=decimal.Decimal(5)
                )

                # 是否融合
                change_rate = decimal.Decimal(min((now - change_date).days / 19, 1))
                if is_merge and change_rate < 1:
                    reward_per_day = reward_per_day_old * (1 - change_rate) + reward_per_day_new * change_rate
                else:
                    reward_per_day = reward_per_day_new
                # print('%s, change_rate->%s, old->%s, new->%s, reward_per_day->%s' % (temp_date, change_rate, reward_per_day_old, reward_per_day_new, reward_per_day))

                # 没有取到对照，则用老算法
                if not reward_per_day:
                    reward_per_day = reward_per_day_old

            # gas_offset = today_power * (create_cost_gas_per_t / package_days) + max(today_power - today_new_power, 0) * keep_cost_gas_per_t
            today_reward_base = decimal.Decimal(today_power) * reward_per_day
            # today_reward = today_reward_base - gas_offset

            data.append({
                'day': i,  # 顺序天
                'date': temp_date,
                'reward_per_day': reward_per_day,
                'pledge_per_day': today_pledge_per_day,
                'today_new_power': today_new_power,
                'package_days': package_days,
                'release_days': release_days,
                'today_power': today_power,
                'today_pledge': today_pledge,
                'today_reward_base': today_reward_base,
                'today_reward': today_reward,
                'today_release': 0,
                'today_release_principal': 0,
                'create_cost_gas_per_t': create_cost_gas_per_t,
                'create_cost_gas_per_t_64': create_cost_gas_per_t_64,
                'keep_cost_gas_per_t': keep_cost_gas_per_t,
                'keep_cost_gas_per_t_64': keep_cost_gas_per_t_64,
                'total_create_gas': 0,
                'total_keep_gas': 0
            })

        print('第一次循环:', time.time() - _time_start, 's')

        total_keep_gas = 0
        total_create_gas = 0
        total_keep_gas_64 = 0
        total_create_gas_64 = 0
        for per in data:
            #======== 当日奖励，扣除汽油费的
            per['create_gas'] = per['today_new_power'] * create_cost_gas_per_t
            total_create_gas += per['create_gas']
            per['total_create_gas'] = total_create_gas
            per['create_gas_64'] = per['today_new_power'] * create_cost_gas_per_t_64
            total_create_gas_64 += per['create_gas_64']
            per['total_create_gas_64'] = total_create_gas_64

            per['keep_gas'] = per['today_power'] * keep_cost_gas_per_t
            total_keep_gas += per['keep_gas']
            per['total_keep_gas'] = total_keep_gas
            per['keep_gas_64'] = per['today_power'] * keep_cost_gas_per_t_64
            total_keep_gas_64 += per['keep_gas_64']
            per['total_keep_gas_64'] = total_keep_gas_64

            # 查看器计算gas
            per['today_reward'] = per['today_reward_base']
            #======== 当日释放奖励
            if per['day'] > 1:
                per['today_release'] = per['today_reward'] * decimal.Decimal(0.25) + self.get_today_release(day=per['day'], data=data, release_days=release_days)
            #======== 当日释放本金，package_days天之后开始释放本金
            if per['day'] > package_days:
                per['today_release_principal'] = self.get_today_release_principal(day=per['day'], data=data, package_days=package_days)

            #======== 累计质押
            per['total_pledge'] = self.get_total_pledge(day=per['day'], data=data)

            #======== 累计奖励
            per['total_reward'] = self.get_total_reward(day=per['day'], data=data)

            #======== 累计释放
            per['total_release'] = self.get_total_release(day=per['day'], data=data)

            #======== 累计释放本金
            per['total_release_principal'] = self.get_total_release_principal(day=per['day'], data=data)

            #======== 累计释放本金 + 奖励
            per['total_already_release'] = per['total_release'] + per['total_release_principal']

        for per in data:
            per['date'] = per['date'].strftime('%Y-%m-%d')
            per['reward_per_day'] = format_price(per['reward_per_day'], 8)
            per['pledge_per_day'] = format_price(per['pledge_per_day'], 8)
            per['today_new_power'] = format_price(per['today_new_power'], 2)
            per['today_power'] = format_price(per['today_power'], 2)
            per['today_pledge'] = format_price(per['today_pledge'], 8)
            per['today_reward_base'] = format_price(per['today_reward_base'], 8)
            per['today_reward'] = format_price(per['today_reward'], 8)
            per['today_release'] = format_price(per['today_release'], 8)
            per['today_release_principal'] = format_price(per['today_release_principal'], 8)
            per['total_pledge'] = format_price(per['total_pledge'], 8)
            per['total_reward'] = format_price(per['total_reward'], 8)
            per['total_release'] = format_price(per['total_release'], 8)
            per['total_release_principal'] = format_price(per['total_release_principal'], 8)
            per['total_already_release'] = format_price(per['total_already_release'], 8)
            per['create_cost_gas_per_t'] = format_price(per['create_cost_gas_per_t'], 8)
            per['create_cost_gas_per_t_64'] = format_price(per['create_cost_gas_per_t_64'], 8)
            per['keep_cost_gas_per_t'] = format_price(per['keep_cost_gas_per_t'], 8)
            per['keep_cost_gas_per_t_64'] = format_price(per['keep_cost_gas_per_t_64'], 8)
            per['create_gas'] = format_price(per['create_gas'], 8)
            per['keep_gas'] = format_price(per['keep_gas'], 8)
            per['total_keep_gas'] = format_price(per['total_keep_gas'], 8)

        return data

    def add_search_log(self, user_id, start_date=None, speed=0, power=0, store_power=0, cost=0,
                       price=0, increase=0, store_cost=0, hardware_cost=0, depreciation_days=0,
                       search_type=0):
        obj = SearchLog.objects.create(
            user_id=user_id, start_date=start_date, speed=speed, power=power, store_power=store_power,
            cost=cost, price=price, increase=increase, store_cost=store_cost,
            hardware_cost=hardware_cost, depreciation_days=depreciation_days, search_type=search_type
        )
        return format_return(0, data={'obj_id': obj.id})

    def search_logs_for_admin(self, search_type=None):
        objs = SearchLog.objects.filter()
        if search_type is not None:
            objs = objs.filter(search_type=search_type)
        return SearchLog.objects.filter()

    def sync_gas_fee(self):

        result = inner_server.get_gas_stat_all()
        if not result:
            return None

        now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = now - datetime.timedelta(days=1)

        for method in result['data']:
            per = result['data'][method]
            obj, created = GasFeeDay.objects.get_or_create(date=yesterday.strftime('%Y-%m-%d'), method=method)
            obj.count = per.get('count', 0)
            obj.gas_limit = per.get('avg_gas_limit', 0)
            obj.gas_fee_cap = per.get('avg_gas_fee_cap', 0)
            obj.gas_premium = per.get('avg_gas_premium', 0)
            obj.gas_used = per.get('avg_gas_used', 0)
            obj.fee = per.get('avg_cost', 0)
            obj.total_fee = per.get('total_cost', 0)
            obj.save()
        return format_return(0)


class TipsetBase(object):

    def update_tipset_2(self, height):
        result = FilfoxBase().get_tipset(tipset=height)
        if not result or not result.get('blocks'):
            return

        tipset = Tipset.objects.filter(height=height)
        if not tipset:
            return
        tipset = tipset[0]
        total_win_count = 0
        total_reward = 0

        for per in result.get('blocks', []):
            # 计算win_count
            # t = float(per['reward_str_in_list'].replace('FIL', ''))
            # p = float(per['reward'])
            # win_count = math.floor(t / p) if p != 0 else 0

            block, created = TipsetBlock.objects.get_or_create(
                block_hash=per['cid'], record_time=tipset.record_time
            )
            block.tipset = tipset
            block.miner_address = per['miner']
            block.msg_count = per['messageCount']
            block.win_count = per['winCount']
            block.reward = decimal.Decimal(per['reward']) + decimal.Decimal(per['penalty'])
            block.height = height
            block.save()

            total_win_count += per['winCount']
            total_reward += block.reward

        tipset.total_win_count = total_win_count
        tipset.total_reward = total_reward
        tipset.save()
        return format_return(0)

    def add_tipset(self, height, blocks=[]):
        '''
        添加高度
        [{
            "block_hash": "bafy2bzacedw4lllhogemgvljwmgze2lip2kabt3h3gqrlkonwz7ude472bcei",
            "miner": "f02398",
            "message_count": 47,
            "reward": "7.25",
            "reward_str_in_list": "14.51 FIL",
            "total_reward": "14.508825125220381"
        }]
        '''
        # 主网启动时间
        launch_date = datetime.datetime(2020, 8, 25, 6, 0, 0)

        with transaction.atomic():
            tipset = Tipset.objects.filter(height=height)
            if tipset:
                return 0

            record_time = launch_date + datetime.timedelta(seconds=30 * height)
            tipset = Tipset.objects.create(height=height, record_time=record_time)

            for per in blocks:
                # 计算win_count
                t = float(per['reward_str_in_list'].replace('FIL', ''))
                p = float(per['reward'])
                win_count = math.floor(t / p) if p != 0 else 0

                block = TipsetBlock.objects.create(
                    tipset=tipset, block_hash=per['block_hash'], miner_address=per['miner'],
                    msg_count=per['message_count'], win_count=win_count,
                    reward=decimal.Decimal('%.18f' % float(per['reward_str'].replace(' FIL', ''))) * 1000000000000000000,
                    height=height, record_time=record_time
                )
                tipset.total_win_count += win_count
                tipset.total_reward += block.reward

            tipset.save()
            return 1

    def sync_tipset(self, date):
        '''
        同步区块
        '''
        # 同步开始时间
        _time_start = time.time()
        # 每页大小
        page_count = 30
        # 主网启动时间
        launch_date = datetime.datetime(2020, 8, 25, 6, 0, 0)

        end_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        start_date = end_date - datetime.timedelta(days=1)

        # 起始索引
        start_index = (start_date - launch_date).total_seconds() / 30
        start_index = max(int(start_index), 29)
        # 结束索引
        end_index = (end_date - launch_date).total_seconds() / 30
        end_index = max(int(end_index), 30)

        success_count = 0
        # 循环取
        for i in range(start_index, end_index + 30, page_count):

            result = FilscoutBase().get_tipset(end_height=i, count=page_count)
            if not result or not result.get('data'):
                continue

            for tipset in result.get('data'):
                height = int(tipset.get('height'))
                if height > end_index:
                    break
                success_count += self.add_tipset(
                    height=height, blocks=tipset.get('blocks', [])
                )

            time.sleep(1)

        print('总耗时:', time.time() - _time_start, 's')
        return format_return(0, data={'success_count': success_count})

    def add_tipset_2(self, height, blocks=[]):
        '''
        [{
            cid: "bafy2bzacebg74fq7yv2mm4lelutq4bn7lmvk53nbz2n6drbca6zcqmanwby2o",
            miner: "f02614",
            minerTag: {
                name: "RMDmine.com",
                signed: true
            },
            messageCount: 162,
            winCount: 1,
            reward: "14516487797684711682",
            penalty: "0"
        }]
        '''
        # 主网启动时间
        launch_date = datetime.datetime(2020, 8, 25, 6, 0, 0)
        record_time = launch_date + datetime.timedelta(seconds=30 * height)

        with transaction.atomic():
            tipset, created = Tipset.objects.get_or_create(height=height, record_time=record_time)

            total_win_count = 0
            total_reward = 0
            for per in blocks:
                block, c = TipsetBlock.objects.get_or_create(
                    block_hash=per['cid'], record_time=tipset.record_time
                )
                block.tipset = tipset
                block.miner_address = per['miner']
                block.msg_count = per['messageCount']
                block.win_count = per['winCount']
                block.reward = decimal.Decimal(per['reward']) + decimal.Decimal(per['penalty'])
                block.height = height
                block.save()

                total_win_count += per['winCount']
                total_reward += block.reward

            tipset.total_win_count = total_win_count
            tipset.total_reward = total_reward
            tipset.save()
            return 1 if created else 0

    def sync_tipset_2(self, date):
        # 同步开始时间
        _time_start = time.time()
        # 每页大小
        page_size = 100

        now = datetime.datetime.now()
        # 主网启动时间
        launch_date = datetime.datetime(2020, 8, 25, 6, 0, 0)
        # 开始时间戳
        start_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        start_index = (start_date - launch_date).total_seconds() / 30
        temp_index = start_index
        # 结束时间戳
        end_date = start_date - datetime.timedelta(days=1)
        end_index = (end_date - launch_date).total_seconds() / 30

        page_index = math.floor((now - start_date).total_seconds() / 30 / page_size) - 1
        result = FilfoxBase().get_tipset_list(page_size=page_size, page_index=page_index)
        while result['tipsets'][0]['height'] < temp_index:
            page_index -= 5
            page_index = max(0, page_index)
            result = FilfoxBase().get_tipset_list(page_size=page_size, page_index=page_index)
        print(page_index, start_index, end_index)

        success_count = 0
        while temp_index >= end_index:
            result = FilfoxBase().get_tipset_list(page_size=page_size, page_index=page_index)
            if result:
                tipsets = result.get('tipsets')
                while tipsets and temp_index >= tipsets[-1]['height']:
                    temp = [x for x in tipsets if x['height'] == temp_index]
                    # 找到
                    if temp:
                        success_count += self.add_tipset_2(height=temp_index, blocks=temp[0].get('blocks', []))
                    else:
                        success_count += self.add_tipset_2(height=temp_index, blocks=[])
                    temp_index -= 1
            print(temp_index)
            page_index += 1
            time.sleep(1)

        print('总耗时:', time.time() - _time_start, 's')
        return format_return(0, data={'success_count': success_count})

    def sync_temp_tipset(self):
        '''
        同步临时区块
        '''
        result = FilfoxBase().get_tipset_list(page_size=100)
        if not result:
            return format_return(0)

        # 主网启动时间
        launch_date = datetime.datetime(2020, 8, 25, 6, 0, 0)

        # 清除24小时以前的数据
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        TempTipsetBlock.objects.filter(record_time__lt=yesterday).delete()

        for tipset in result.get('tipsets', []):
            height = tipset['height']
            record_time = launch_date + datetime.timedelta(seconds=30 * height)

            for per in tipset.get('blocks', []):
                if not per.get('reward'):
                    continue
                block, c = TempTipsetBlock.objects.get_or_create(
                    block_hash=per['cid'], record_time=record_time
                )
                block.miner_address = per['miner']
                block.msg_count = per['messageCount']
                block.win_count = per['winCount']
                block.reward = decimal.Decimal(per['reward']) + decimal.Decimal(per['penalty'])
                block.height = height
                block.save()

        return format_return(0)

    def get_total_rewards(self):
        return Tipset.objects.filter().aggregate(Sum('total_reward'))['total_reward__sum'] or 0


def _d(num):
    return decimal.Decimal(num)


class LookupBase():

    def __init__(self):
        # 主网开始时间
        self.launch_date = datetime.datetime(2020, 8, 25, 6, 0, 0)
        # 网络基线2.5EiB,换算成 PiB
        self.net_baseline_power_p = _d(2.5 * math.pow(1024, 1))
        # 总的铸造量
        self.total_minted = _d(1100000000)
        # 总的铸造量
        self.baseline_minted = _d(770000000)
        # 总的铸造量
        self.simple_minted = _d(330000000)
        # 奖励释放天数
        self.release_days = 180

    def get_kpi_power(self, block_num):
        return self.net_baseline_power_p * _d(math.pow(2, block_num / 365 / 2880) * math.pow(1024, 5))

    def get_kpi_power_per_day(self, day):
        return self.net_baseline_power_p * _d(math.pow(2, day / 365) * math.pow(1024, 5))

    def get_simple_reward(self, block_num):
        '''
        简单奖励
        '''
        return self.simple_minted * _d(math.exp(-1.09897764548444e-7 * block_num) * (1.09897764548444e-7))

    def get_date_simple_reward(self, date):
        '''
        获取指定日期的简单奖励
        '''
        start_date = datetime.datetime(date.year, date.month, date.day)
        # 第一天特殊处理
        if start_date.strftime('%Y-%m-%d') == self.launch_date.strftime('%Y-%m-%d'):
            start_index = 0
            end_index = 2160
        else:
            start_index = int((start_date - self.launch_date).total_seconds() / 30)
            end_index = start_index + 2880

        simple_reward = 0
        for i in range(start_index, end_index):
            simple_reward += self.get_simple_reward(block_num=i)
        return simple_reward

    def get_baseline_reward(self, block_num):
        '''
        基线奖励
        '''
        return self.baseline_minted * -d(math.exp(-1.09897764548444e-7 * block_num) * (1.09897764548444e-7))

    def get_sum_baseline_reward(self, time):
        '''
        累计基线奖励
        '''
        return self.baseline_minted * _d(1 - math.exp(-time * _d(math.log(2) / (6 * 365))))

    def get_kpi_time(self, sum_power):
        '''
        计算有效时间, 单位是PiB
        '''
        return 365 / _d(math.log(2)) * _d(math.log(
            1 + _d(math.log(2)) * sum_power / _d(365 * self.net_baseline_power_p)
        ))

    def get_luck_v(self, date=None):
        '''
        获取幸运值
        '''
        if date:
            start_date = date.strftime('%Y-%m-%d') + ' 00:00:00'
            end_date = (date + datetime.timedelta(days=1)).strftime('%Y-%m-%d') + ' 00:00:00'

            sql = """
                SELECT height, SUM(win_count)
                FROM calculator_tipsetblock
                WHERE %s <= record_time AND record_time < %s
                GROUP BY height
            """
            records = raw_sql.exec_sql(sql, [start_date, end_date])
        else:
            sql = """
                SELECT height, SUM(win_count)
                FROM calculator_temptipsetblock
                GROUP BY height
            """
            records = raw_sql.exec_sql(sql)
        if not records:
            return _d(1)

        sum_win_count = 0
        for per in records:
            sum_win_count += per[1]

        luck_v = _d(sum_win_count / len(records) / 5)
        return min(1, luck_v)

    def get_sum_power(self, date):
        '''
        历史所有算力总和
        '''
        return TotalPowerDay.objects.filter(date__lte=date).aggregate(Sum('power'))['power__sum'] or 0

    def get_official_release(self, date):
        '''
        官方释放
        '''
        temp_date = datetime.datetime(date.year, date.month, date.day)
        # fixed_v = 688028 - 533571
        stage_0 = datetime.datetime(2020, 10, 15)
        stage_1 = datetime.datetime(2021, 4, 15)
        stage_2 = datetime.datetime(2021, 10, 15)
        stage_3 = datetime.datetime(2022, 10, 15)
        stage_4 = datetime.datetime(2023, 10, 15)
        stage_5 = datetime.datetime(2026, 10, 14)

        official_release = _d(0)
        if stage_0 <= temp_date and temp_date <= stage_1:
            official_release = _d(653067.36)  # _d(182548 + 351023 + fixed_v)
        elif stage_1 < temp_date and temp_date <= stage_2:
            official_release = _d(365150.35)  # _d(182548 + 185632 + fixed_v)
        elif stage_2 < temp_date and temp_date <= stage_3:
            official_release = _d(277933.82)  # _d(182548 + 79622 + fixed_v)
        elif stage_3 < temp_date and temp_date <= stage_4:
            official_release = _d(268017.40)  # _d(182548 + 65372 + fixed_v)
        elif stage_4 < temp_date and temp_date <= stage_5:
            official_release = _d(187125.59)  # _d(182548)
        return official_release

    def current_base_fee(self):
        '''
        获取最新base_fee
        '''
        return TotalPower.objects.filter()[0].base_fee

    def get_avg_create_gas(self):
        '''获取平均生成gas'''
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total = 0
        # 获取7天平均值
        for i in range(7):
            today -= datetime.timedelta(days=1)
            temp = GasFeeDay.objects.filter(date=today, method='PreCommitSector')[0]
            avg_pre = (temp.total_fee / 10**18) / temp.count
            temp = GasFeeDay.objects.filter(date=today, method='ProveCommitSector')[0]
            avg_prove = (temp.total_fee / 10**18) / temp.count

            total += _d(avg_pre + avg_prove)

        return _d(total / 7 * 32)

    def get_create_gas(self, avg_create_gas, increase_power):
        '''
        获取生产gas
        2.201*10^-6 * 当前base_fee * 全网算力增速PB + 4359.2
        '''
        # return _d(2.201 / math.pow(10, 6)) * base_fee * (increase_power / _d(math.pow(1024, 5))) + _d(4359.2)
        return avg_create_gas * (increase_power / 1024**4)

    def get_avg_keep_gas(self):
        '''获取平均维护gas'''
        total = 0
        # 获取7天平均值
        for per in TotalPowerDay.objects.filter()[:7]:
            total += _d(per.submit_windowed_po_st_total_gas / (per.power / _d(1024**4)))

        return _d(total / 7)

    def get_keep_gas(self, avg_keep_gas, power):
        '''
        获取维护gas
        4.6*10^-9 * 当前base_fee * 全网有效算力PB + 154.69
        '''
        # return _d(4.6 / math.pow(10, 9)) * base_fee * (power / _d(math.pow(1024, 5))) + _d(154.69)
        return avg_keep_gas * (power / 1024**4)

    def get_penalty_gas(self, base_fee):
        '''
        获取惩罚gas
        6.845*10^-6 * 当前base_fee * 10752
        '''
        return _d(6.845 / math.pow(10, 6)) * base_fee + _d(10752)

    @cache_required(cache_key='calculator_history_lookups', expire=30 * 60)
    def get_history_lookups(self, must_update_cache=False):
        '''
        获取历史对照
        '''
        lookups = []
        index = 0
        for per in TotalPowerDay.objects.filter().order_by('date'):
            # sum_power = self.get_sum_power(date=per.date)
            sum_power = sum([x['limit_power'] for x in lookups])
            kpi_power = self.get_kpi_power_per_day(day=index)
            kpi_time = self.get_kpi_time(sum_power=sum_power / _d(math.pow(1024, 5)))
            sum_baseline_reward = self.get_sum_baseline_reward(time=kpi_time)
            simple_reward = self.get_date_simple_reward(date=per.date)
            official_release = self.get_official_release(date=per.date)
            prev_sum_baseline_reward = lookups[index - 1]['sum_baseline_reward'] if index > 0 else _d(0)
            baseline_reward = sum_baseline_reward - prev_sum_baseline_reward
            reward = baseline_reward + simple_reward
            reward_by_luck = reward * per.luck
            # 2020-10-21之后 25%立即释放
            if per.date <= datetime.date(2020, 10, 21):
                day_release = _d(0)
                day_line_release = reward_by_luck / _d(self.release_days)
            else:
                day_release = reward_by_luck * _d(0.25)
                day_line_release = reward_by_luck * _d(0.75) / _d(self.release_days)

            temp = {
                'day': index,
                'date': per.date,
                'power': per.power,
                'limit_power': min(per.power, kpi_power),
                'sum_power': sum_power,
                'kpi_time': kpi_time,
                'kpi_power': kpi_power,
                'sum_baseline_reward': sum_baseline_reward,
                'luck_v': per.luck,
                'increase_power': per.increase_power,
                'packing_power': per.packing_power,
                'baseline_reward': baseline_reward,
                'simple_reward': simple_reward,
                'reward': reward,
                'reward_by_luck': reward_by_luck,
                'avg_reward': per.avg_reward,
                'base_fee': per.base_fee,
                'circulating_supply': per.circulating_supply,
                'create_gas': per.create_gas if per.create_gas else (per.pre_commit_sector_total_gas + per.prove_commit_sector_total_gas),
                'keep_gas': per.keep_gas if per.keep_gas else per.submit_windowed_po_st_total_gas,
                'official_release': official_release,
                'penalty_gas': self.get_penalty_gas(base_fee=per.base_fee),
                'day_release': day_release,
                'day_line_release': day_line_release,
                'day_line_release_sum': 0,
                'miner_release': 0,
                'avg_pledge': per.avg_pledge * _d(32),
                'pledge': per.avg_pledge * _d(32) * (per.increase_power / _d(math.pow(1024, 4)))
            }
            lookups.append(temp)

            # 前180天累计线性释放
            temp['day_line_release_sum'] = sum([x['day_line_release'] for x in lookups[-self.release_days:-1]])
            # 挖矿释放
            temp['miner_release'] = day_release + temp['day_line_release_sum']
            # 修正质押, 当日质押 + (奖励 - 挖矿释放)
            temp['pledge'] += temp['reward_by_luck'] - temp['miner_release']
            # 总质押量
            temp['sum_pledge'] = sum([x['pledge'] for x in lookups])

            index += 1

        return lookups

    @cache_required(cache_key='calculator_lookups_%s', expire=2 * 60 * 60)
    def get_lookups(self, ck='', luck_v='', increase_power='', days=540,  must_update_cache=False):
        '''
        获取对照
        '''
        _time_start = time.time()
        offset_day = 20
        lookups = []
        history_lookups = self.get_history_lookups(must_update_cache=must_update_cache)

        # 算力增速，取7天均值
        # increase_power = CalculatorBase().get_increase_power_per_day() if increase_power is None else increase_power * _d(math.pow(1024, 5))
        avg_increase_power = sum([x['increase_power'] for x in history_lookups[-7:]]) / 7
        increase_power = _d(avg_increase_power) if increase_power is None else increase_power * _d(math.pow(1024, 5))
        # 幸运值
        luck_v = _d(luck_v or self.get_luck_v())
        # 实时base_fee
        current_base_fee = self.current_base_fee()
        # 昨天base_fee
        yesterday_base_fee = history_lookups[-1]['base_fee']
        # 平均成产gas
        avg_create_gas = self.get_avg_create_gas()
        # 平均维护gas
        avg_keep_gas = self.get_avg_keep_gas()

        lookups.append(history_lookups[-1])
        for i in range(1, days + offset_day + 1):
            prev_day = lookups[- 1]
            today = prev_day['date'] + datetime.timedelta(days=1)

            # 基线算力值
            run_days = (today - self.launch_date.date()).days
            today_kpi_power = self.get_kpi_power_per_day(day=run_days)

            # 预测今日算力，不能超过kpi算力
            guess_today_power = max(prev_day['power'] + increase_power, _d(0))
            guess_limit_today_power = min(guess_today_power, today_kpi_power)
            # 预测今日历史汇总算力
            guess_today_sum_power = prev_day['sum_power'] + guess_limit_today_power
            # 预测今日有效时间
            guess_today_kpi_time = self.get_kpi_time(sum_power=guess_today_sum_power / _d(math.pow(1024, 5)))
            # 预测今日累计基线奖励
            guess_today_sum_baseline_reward = self.get_sum_baseline_reward(time=guess_today_kpi_time)
            # 预测今日基线奖励
            guess_today_baseline_reward = max(guess_today_sum_baseline_reward - prev_day['sum_baseline_reward'], _d(0))
            # 预测今日简单奖励
            guess_today_simple_reward = self.get_date_simple_reward(date=today)
            # 预测今日奖励
            guess_today_reward = guess_today_simple_reward + guess_today_baseline_reward
            # 计算幸运值
            guess_today_reward_by_luck = guess_today_reward * luck_v
            # 预测今日区块奖励 TiB
            guess_today_avg_reward = guess_today_reward_by_luck / (guess_today_power / _d(math.pow(1024, 4))) if guess_today_power != 0 else _d(0)
            # 官方释放
            official_release = self.get_official_release(date=today)
            # 今日立即释放
            day_release = guess_today_reward_by_luck * _d(0.25)
            # 线性释放
            day_line_release = guess_today_reward_by_luck * _d(0.75) / _d(self.release_days)

            temp = {
                'day': run_days,
                'date': today,
                'power': guess_today_power,
                'limit_power': guess_limit_today_power,
                'sum_power': guess_today_sum_power,
                'kpi_time': guess_today_kpi_time,
                'kpi_power': today_kpi_power,
                'sum_baseline_reward': guess_today_sum_baseline_reward,
                'luck_v': luck_v,
                'increase_power': increase_power,
                'packing_power': increase_power,
                'baseline_reward': guess_today_baseline_reward,
                'simple_reward': guess_today_simple_reward,
                'reward': guess_today_reward,
                'reward_by_luck': guess_today_reward_by_luck,
                'avg_reward': guess_today_avg_reward,
                'base_fee': yesterday_base_fee,
                'circulating_supply': 0,
                'create_gas': 0,
                'keep_gas': 0,
                'official_release': official_release,
                'day_release': day_release,
                'day_line_release': day_line_release,
                'day_line_release_sum': 0,
                'miner_release': 0
            }
            lookups.append(temp)

        temp_lookups = history_lookups + lookups[1:]

        i = 0
        for per in lookups[:-offset_day]:
            if i == 0:
                i += 1
                continue
            prev_day = lookups[i - 1]

            # 前180天累计线性释放
            start_index = max(per['day'] - self.release_days, 0)
            per['day_line_release_sum'] = sum([x['day_line_release'] for x in temp_lookups[start_index:per['day']]])
            # 挖矿释放
            per['miner_release'] = per['day_release'] + per['day_line_release_sum']

            # 质押逻辑：sum(当日单T收益...未来19天单T收益)  + 0.3*昨日流通量 / max(全网基线算力，全网有效算力)
            sum_reward = sum([x['avg_reward'] for x in lookups[i:i + offset_day]])
            max_power = max(per['power'], per['kpi_power'])
            prev_circulating_supply = prev_day['circulating_supply'] / _d(math.pow(10, 18))
            per['avg_pledge'] = sum_reward + _d(0.3) * prev_circulating_supply / (max_power / _d(math.pow(1024, 4)))

            # 当日质押量
            per['pledge'] = per['avg_pledge'] * (increase_power / _d(math.pow(1024, 4)))
            per['pledge'] += per['reward_by_luck'] - per['miner_release']
            # 总质押量
            per['sum_pledge'] = sum([x['pledge'] for x in temp_lookups[:per['day']]])
            # 生产gas
            per['create_gas'] = self.get_create_gas(avg_create_gas=avg_create_gas, increase_power=increase_power)
            # 维护gas
            per['keep_gas'] = self.get_keep_gas(avg_keep_gas=avg_keep_gas, power=per['power'])
            # 处罚gas
            per['penalty_gas'] = self.get_penalty_gas(base_fee=current_base_fee)
            # 新增流通量
            circulating_supply_offset = per['official_release'] + per['miner_release'] - (per['pledge'] + per['create_gas'] + per['keep_gas'] + per['penalty_gas'] - 5000)
            # 今日流通量
            per['circulating_supply'] = (prev_circulating_supply + circulating_supply_offset) * _d(math.pow(10, 18))

            i += 1

        print('对照总耗时:', time.time() - _time_start, 's')
        return history_lookups + lookups[1:-offset_day]
