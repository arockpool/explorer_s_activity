import json
import math
import time
import decimal
import datetime
from collections import Iterable

from django.http import HttpResponse

from explorer_s_common.decorator import common_ajax_response
from explorer_s_common.utils import format_return, format_price, format_power, str_2_power, format_coin_to_str, _d
from explorer_s_common.page import Page
from explorer_s_common import inner_server, cache
from explorer_s_common.third.filscout_sdk import FilscoutBase
from explorer_s_common.third.filfox_sdk import FilfoxBase

from explorer_s_activity import consts
from calculator.interface import CalculatorBase, LookupBase, TipsetBase


@common_ajax_response
def get_calculate_info(request):
    '''
    获取计算信息
    '''
    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))
    rate = CalculatorBase().get_usd_rate()
    overview = CalculatorBase().get_fil_overview(must_update_cache=must_update_cache)
    increase_power_per_day = CalculatorBase().get_increase_power_per_day()
    gas_stat = CalculatorBase().get_gas_stat(must_update_cache=must_update_cache)

    create_cost_gas_per_t = (gas_stat['avg_prove_commit_sector'] + gas_stat['avg_pre_commit_sector']) * _d(32)
    keep_cost_gas_per_t = gas_stat['submit_windowed_po_st'] / (_d(overview['total_power']) / _d(math.pow(1024, 4)))

    # gas相关
    gas_info_32 = inner_server.get_gas_cost_stat({'sector_type': '0'}).get('data', {})
    gas_info_64 = inner_server.get_gas_cost_stat({'sector_type': '1'}).get('data', {})
    info = {
        'total_power_str': overview.get('total_power_str'),
        'avg_reward': overview.get('avg_reward'),
        'avg_pledge': format_price(decimal.Decimal(overview.get('avg_pledge', 0)) * 32, 4),
        'price': overview.get('price'),
        'rate': rate,
        'increase_power_per_day_str': format_price(increase_power_per_day / (1024 * 1024 * 1024 * 1024 * 1024)),
        'increase_power_per_day': format_price(increase_power_per_day, 0),
        'gas_stat': {
            'prove_commit_sector': format_price(gas_stat['prove_commit_sector'], 8),
            'pre_commit_sector': format_price(gas_stat['pre_commit_sector'], 8),
            'submit_windowed_po_st': format_price(gas_stat['submit_windowed_po_st'], 8),
            'avg_prove_commit_sector': format_price(gas_stat['avg_prove_commit_sector'], 8),
            'avg_pre_commit_sector': format_price(gas_stat['avg_pre_commit_sector'], 8),
            'avg_submit_windowed_po_st': format_price(gas_stat['avg_submit_windowed_po_st'], 8)
        },
        'create_cost_gas_per_t': format_price(max(_d(gas_info_32['create_gas']), 0.0001), 8),
        'keep_cost_gas_per_t': format_price(max(_d(gas_info_32['keep_gas']), 0.0001), 8),
        'create_cost_gas_per_t_64': format_price(max(_d(gas_info_64['create_gas']), 0.0001), 8),
        'keep_cost_gas_per_t_64': format_price(max(_d(gas_info_64['keep_gas']), 0.0001), 8)
    }

    return format_return(0, data=info)


@common_ajax_response
def get_calculate_sum(request):
    '''
    矿机产出计算
    '''
    power_per_day = decimal.Decimal(request.POST.get('power_per_day', '2'))
    total_power = decimal.Decimal(request.POST.get('total_power', '120'))
    init_power = decimal.Decimal(request.POST.get('init_power', '0'))
    cost = decimal.Decimal(request.POST.get('cost', '1'))
    price = decimal.Decimal(request.POST.get('price', '1'))
    current_date = request.POST.get('current_date')
    current_date = datetime.datetime.strptime(current_date, '%Y-%m-%d') if current_date else datetime.datetime.now()
    increase_power_per_day = float(request.POST.get('increase_power_per_day', '10'))
    search_type = request.POST.get('search_type', '0')
    luck_v = request.POST.get('luck_v', '0.997')
    is_merge = json.loads(request.POST.get('is_merge', '1'))
    is_use_gas = json.loads(request.POST.get('is_use_gas', '0'))

    data = CalculatorBase().generate_lookup(
        current_date=current_date, power_per_day=power_per_day, total_power=total_power,
        increase_power_per_day=increase_power_per_day, init_power=init_power, luck_v=luck_v,
        is_merge=is_merge
    )
    rate = CalculatorBase().get_usd_rate()
    overview = CalculatorBase().get_fil_overview()
    win_day = 0

    records = []
    for per in data:
        # 平衡日
        temp = decimal.Decimal(per['total_reward']) * price * decimal.Decimal(rate)
        if is_use_gas:
            temp = (decimal.Decimal(per['total_reward']) - decimal.Decimal(per['total_create_gas']) - decimal.Decimal(
                per['total_keep_gas'])) * price * decimal.Decimal(rate)

        if temp >= cost:
            records.append(per)
            win_day = per['day']
            break

    # 封满日
    full_day = math.ceil((total_power - init_power) / power_per_day)
    # 预质押量
    pre_pledge = 0

    for per in data:
        if per['day'] in [180, 360, 540, full_day]:
            records.append(per)

        # 计算预质押量，当日释放量大于质押量
        if pre_pledge == 0 and float(per['today_release']) >= float(per['today_pledge']):
            pre_pledge = float(per['total_pledge']) - float(per['total_release']) + float(per['today_release'])

    pre_pledge = max(pre_pledge, 0)

    # 排序
    sorted_records = sorted(records, key=lambda x: x['day'])

    # 记录日志
    user_id = request.POST.get('user_id')
    if user_id:
        CalculatorBase().add_search_log(
            user_id=user_id, search_type=search_type, start_date=current_date,
            speed=power_per_day, store_power=total_power, cost=cost, price=price,
            increase=increase_power_per_day
        )

    return format_return(0, data={
        'records': sorted_records, 'win_day': win_day, 'full_day': full_day,
        'pre_pledge': format_price(pre_pledge, 4)
    })


@common_ajax_response
def get_calculate_detail(request):
    '''
    获取计算汇总详情
    '''
    power_per_day = decimal.Decimal(request.POST.get('power_per_day', '2'))
    total_power = decimal.Decimal(request.POST.get('total_power', '120'))
    init_power = decimal.Decimal(request.POST.get('init_power', '0'))
    current_date = request.POST.get('current_date')
    current_date = datetime.datetime.strptime(current_date,
                                              '%Y-%m-%d') if current_date else datetime.datetime.now().replace(hour=0,
                                                                                                               minute=0,
                                                                                                               second=0,
                                                                                                               microsecond=0)
    increase_power_per_day = float(request.POST.get('increase_power_per_day', '10'))
    luck_v = request.POST.get('luck_v', '0.997')
    is_merge = json.loads(request.POST.get('is_merge', '1'))

    data = CalculatorBase().generate_lookup(
        current_date=current_date, power_per_day=power_per_day, total_power=total_power,
        increase_power_per_day=increase_power_per_day, init_power=init_power, luck_v=luck_v,
        is_merge=is_merge
    )

    return format_return(0, data=data)


def _get_lookup(total_power, avg_reward):
    data = []
    days = 541
    release_days = 180
    today_reward = total_power * avg_reward

    for i in range(1, days):
        data.append({
            'day': i,
            'today_reward': today_reward,
            'today_release': 0,
            'total_release': 0
        })

    for per in data:
        # ======== 当日释放奖励
        if per['day'] > 1:
            per['today_release'] = per['today_reward'] * decimal.Decimal(0.25) + CalculatorBase().get_today_release(
                day=per['day'], data=data, release_days=release_days)

        # ======== 累计释放
        per['total_release'] = CalculatorBase().get_total_release(day=per['day'], data=data)

    return data


@common_ajax_response
def get_quick_calculate_sum(request):
    '''
    有效算力产出计算
    '''
    total_power = decimal.Decimal(request.POST.get('total_power', '120'))
    cost = decimal.Decimal(request.POST.get('cost', '1'))
    price = decimal.Decimal(request.POST.get('price', '1'))
    overview = CalculatorBase().get_fil_overview()
    rate = CalculatorBase().get_usd_rate()

    # 每天收益人民币
    avg_reward = decimal.Decimal(overview.get('avg_reward', 0))
    avg_pledge = decimal.Decimal(overview.get('avg_pledge', 0))
    day_reward = total_power * avg_reward * price * decimal.Decimal(rate)

    data = []
    lookups = _get_lookup(total_power, avg_reward)

    for win_day in [math.ceil(cost / day_reward), 180, 360, 540]:
        win_fil = win_day * total_power * avg_reward
        win_pledge = total_power * avg_pledge * 32
        temp = lookups[win_day - 1]
        data.append({
            'win_day': win_day, 'win_fil': win_fil, 'win_pledge': win_pledge,
            'total_release': format_price(temp['total_release'], 4),
            'total_un_release': format_price(win_fil - temp['total_release'], 4)
        })

    # 记录日志
    user_id = request.POST.get('user_id')
    if user_id:
        search_type = 0

        CalculatorBase().add_search_log(
            user_id=user_id, search_type=search_type, power=total_power, cost=cost, price=price
        )

    return format_return(0, data=data)


@common_ajax_response
def get_cost_calculate_sum(request):
    '''
    有效算力成本计算
    '''
    user_id = request.POST.get('user_id')
    if not user_id:
        return format_return(0)

    search_type = 2
    cost = request.POST.get('cost')
    store_cost = request.POST.get('store_cost')
    hardware_cost = request.POST.get('hardware_cost')
    speed = request.POST.get('power_per_day')
    depreciation_days = request.POST.get('depreciation_days')

    return CalculatorBase().add_search_log(
        user_id=user_id, search_type=search_type, cost=cost, store_cost=store_cost,
        hardware_cost=hardware_cost, speed=speed, depreciation_days=depreciation_days
    )


@common_ajax_response
def get_lookups(request):
    '''
    获取对照信息
    '''
    luck_v = request.POST.get('luck_v', '')
    increase_power = request.POST.get('increase_power', '')
    days = int(request.POST.get('days', 540))
    cache_key = '%s_%s_%s' % (luck_v, increase_power, days)
    print('cache_key---->', cache_key)
    increase_power = decimal.Decimal(increase_power) if increase_power else None
    must_update_cache = json.loads(request.POST.get('must_update_cache', '0'))

    lookups = LookupBase().get_lookups(
        cache_key, luck_v=luck_v, increase_power=increase_power, days=days, must_update_cache=must_update_cache
    )

    for per in lookups:
        per['day'] = per['day'] + 1
        per['date'] = per['date'].strftime('%Y-%m-%d')
        per['power_str'] = format_power(per['power'])
        per['limit_power_str'] = format_power(per['limit_power'])
        per['sum_power_str'] = format_power(per['sum_power'])
        per['kpi_time'] = format_price(per['kpi_time'], 8)
        per['kpi_power_str'] = format_power(per['kpi_power'])
        per['sum_baseline_reward'] = format_price(per['sum_baseline_reward'], 8)
        per['luck_v'] = format_price(per['luck_v'], 8)
        per['increase_power_str'] = format_power(per['increase_power'])
        per['packing_power_str'] = format_power(per['packing_power'])
        per['baseline_reward'] = format_price(per['baseline_reward'], 8)
        per['simple_reward'] = format_price(per['simple_reward'], 8)
        per['reward'] = format_price(per['reward'], 8)
        per['reward_by_luck'] = format_price(per['reward_by_luck'], 8)
        per['avg_reward'] = format_price(per['avg_reward'], 8)
        per['base_fee_str'] = format_coin_to_str(per['base_fee']) + 'FIL'
        per['circulating_supply_str'] = format_coin_to_str(per['circulating_supply']) + 'FIL'
        per['avg_pledge'] = format_price(per['avg_pledge'], 8)

    return format_return(0, data=lookups)


@common_ajax_response
def get_power_overview(request):
    date = request.POST.get('date')
    if date:
        obj = CalculatorBase().get_total_power_day_records().filter(date=date)
        obj = obj[0] if obj else None
    else:
        obj = CalculatorBase().get_current_total_power()

    data = {}
    if obj:
        data = {
            'date': date, 'power': obj.power,
            'avg_reward': obj.avg_reward, 'avg_pledge': obj.avg_pledge,
            'burnt_supply': obj.burnt_supply, 'base_fee': obj.base_fee,
            'circulating_supply': obj.circulating_supply
        }
    return format_return(0, data=data)


@common_ajax_response
def get_calculate_sum_v2(request):
    '''计算版本2'''

    rate = _d(CalculatorBase().get_usd_rate())
    overview = CalculatorBase().get_fil_overview()
    gas_stat = CalculatorBase().get_gas_stat()

    price = _d(overview.get('price'))  # fil单价
    base_cost = _d(4399)
    base_days = _d(330)
    base_fil = base_cost / 22 / rate
    base_avg_reward = _d(base_fil / base_days)

    tag_days = int(base_cost / price / rate / base_avg_reward)
    print('tag_days--->', tag_days, rate)

    def _get_day_data(d, day):
        day_data = {}
        for per in d:
            if per['day'] == day:
                day_data = per
                break
        return day_data

    increase_power_per_day = _d(request.POST.get('increase_power_per_day') or '10')
    luck_v = request.POST.get('luck_v', LookupBase().get_luck_v())
    current_date = request.POST.get('current_date')
    current_date = datetime.datetime.strptime(current_date, '%Y-%m-%d') if current_date else datetime.datetime.now()
    cache_key = '%s_%.2f' % (luck_v, increase_power_per_day)
    now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    _offset_days = (current_date - now).days
    avg_reward_lookups = LookupBase().get_lookups(cache_key, luck_v=luck_v, increase_power=increase_power_per_day,
                                                  days=541 + _offset_days,
                                                  must_update_cache=True if _offset_days > 0 else False)
    avg_reward_lookups_dict = dict([(x['date'].strftime('%Y-%m-%d'), x['avg_reward']) for x in avg_reward_lookups])
    avg_reward = avg_reward_lookups_dict.get(current_date.strftime('%Y-%m-%d'),
                                             _d(overview.get('avg_reward')))  # 当前平均奖励/T
    if current_date.strftime('%Y-%m-%d') == datetime.datetime.now().strftime('%Y-%m-%d'):
        avg_reward = _d(overview.get('avg_reward'))
    print('avg_reward---->', avg_reward)
    power_per_day = _d(request.POST.get('power_per_day', '1'))
    total_power = _d(request.POST.get('total_power', '120'))
    init_power = _d(request.POST.get('init_power', '0'))
    cost = _d(request.POST.get('cost', '1'))
    is_merge = json.loads(request.POST.get('is_merge', '1'))
    is_use_gas = json.loads(request.POST.get('is_use_gas', '0'))

    direct_avg_reward_dict = [avg_reward for i in range(1, 541)]
    data = CalculatorBase().generate_lookup(
        current_date=current_date, power_per_day=power_per_day, total_power=total_power,
        increase_power_per_day=increase_power_per_day, init_power=init_power, luck_v=luck_v,
        is_merge=is_merge, direct_avg_reward_dict=direct_avg_reward_dict
    )
    # 平衡日
    win_day = 0
    for per in data:
        # 平衡日
        temp = decimal.Decimal(per['total_reward']) * price * rate
        if is_use_gas:
            temp = (_d(per['total_reward']) - _d(per['total_create_gas']) - _d(per['total_keep_gas'])) * price * rate

        if temp >= cost:
            win_day = per['day']
            break

    slope = (base_fil - (avg_reward * 330)) / sum([x for x in range(1, 331)])
    print('slope---->', slope)
    direct_avg_reward_dict = [max(avg_reward + (i * slope), _d(0.0001)) for i in range(1, 541)]
    # 330天回本数据字典
    base_data = CalculatorBase().generate_lookup(
        current_date=current_date, power_per_day=power_per_day, total_power=total_power,
        increase_power_per_day=increase_power_per_day, init_power=init_power, luck_v=luck_v,
        is_merge=is_merge, direct_avg_reward_dict=direct_avg_reward_dict
    )

    # 平衡日
    base_win_day = 0
    for per in base_data:
        # 平衡日
        temp = decimal.Decimal(per['total_reward']) * price * rate
        if is_use_gas:
            temp = (_d(per['total_reward']) - _d(per['total_create_gas']) - _d(per['total_keep_gas'])) * price * rate

        if temp >= cost:
            base_win_day = per['day']
            break

    # 封满日
    full_day = math.ceil((total_power - init_power) / power_per_day)

    records = {}
    # 拼装数据
    if win_day:
        win_keep_gas = sorted([_d(_get_day_data(data, win_day)['total_keep_gas']),
                               _d(_get_day_data(base_data, base_win_day)['total_keep_gas'])])
        win_keep_gas_64 = sorted([_d(_get_day_data(data, win_day)['total_keep_gas_64']),
                                  _d(_get_day_data(base_data, base_win_day)['total_keep_gas_64'])])
        win_create_gas = _d(_get_day_data(data, win_day)['total_create_gas'])
        win_create_gas_64 = _d(_get_day_data(data, win_day)['total_create_gas_64'])
        win_reward = sorted(
            [_d(_get_day_data(data, win_day)['total_reward']), _d(_get_day_data(base_data, win_day)['total_reward'])])
        win_reward_base = sorted([_d(_get_day_data(data, base_win_day)['total_reward']),
                                  _d(_get_day_data(base_data, base_win_day)['total_reward'])])

        win_release_reward = sorted(
            [_d(_get_day_data(data, win_day)['total_release']), _d(_get_day_data(base_data, win_day)['total_release'])])
        win_release_reward_base = sorted([_d(_get_day_data(data, base_win_day)['total_release']),
                                          _d(_get_day_data(base_data, base_win_day)['total_release'])])

        win_unrelease_reward = [win_reward[0] - win_release_reward[0], win_reward[1] - win_release_reward[1]]
        win_unrelease_reward_base = [win_reward_base[0] - win_release_reward_base[0],
                                     win_reward_base[1] - win_release_reward_base[1]]

        win_pledge = _d(_get_day_data(data, win_day)['total_pledge'])
        records = {
            'win_day': {
                'days': sorted([win_day, base_win_day]),
                'keep_gas': [format_price(x, 4) for x in win_keep_gas],
                'keep_gas_64': [format_price(x, 4) for x in win_keep_gas_64],
                'create_gas': format_price(win_create_gas, 4),
                'create_gas_64': format_price(win_create_gas_64, 4),
                'reward': [[format_price(x, 4) for x in win_reward], [format_price(x, 4) for x in win_reward_base]],
                'release_reward': [[format_price(x, 4) for x in win_release_reward],
                                   [format_price(x, 4) for x in win_release_reward_base]],
                'unrelease_reward': [[format_price(x, 4) for x in win_unrelease_reward],
                                     [format_price(x, 4) for x in win_unrelease_reward_base]],
                'pledge': format_price(win_pledge, 4)
            }
        }

    for day in [full_day, 180, 360, 540]:
        if day == 0:
            continue
        temp_keep_gas = _d(_get_day_data(data, day)['total_keep_gas'])
        temp_keep_gas_64 = _d(_get_day_data(data, day)['total_keep_gas_64'])
        temp_create_gas = _d(_get_day_data(data, day)['total_create_gas'])
        temp_create_gas_64 = _d(_get_day_data(data, day)['total_create_gas_64'])
        temp_reward = sorted(
            [_d(_get_day_data(data, day)['total_reward']), _d(_get_day_data(base_data, day)['total_reward'])])
        temp_release_reward = sorted(
            [_d(_get_day_data(data, day)['total_release']), _d(_get_day_data(base_data, day)['total_release'])])
        temp_unrelease_reward = [temp_reward[0] - temp_release_reward[0], temp_reward[1] - temp_release_reward[1]]
        records[str(day)] = {
            'days': [day],
            'keep_gas': [format_price(temp_keep_gas, 4)],
            'keep_gas_64': [format_price(temp_keep_gas_64, 4)],
            'create_gas': format_price(temp_create_gas, 4),
            'create_gas_64': format_price(temp_create_gas_64, 4),
            'reward': [format_price(x, 4) for x in temp_reward],
            'release_reward': [format_price(x, 4) for x in temp_release_reward],
            'unrelease_reward': [format_price(x, 4) for x in temp_unrelease_reward],
            'pledge': format_price(_get_day_data(data, day)['total_pledge'], 4)
        }

    if full_day:
        records['full_day'] = records[str(full_day)]
        records.pop(str(full_day))
    return format_return(0, data={
        'records': records, 'win_day': win_day, 'full_day': full_day
    })


@common_ajax_response
def get_usd_rate(request):
    result = CalculatorBase().get_usd_rate()
    return format_return(0, data=result)


@common_ajax_response
def sync_total_power_per_hour(request):
    '''
    每小时同步总算力
    '''
    overview = CalculatorBase().get_fil_overview(must_update_cache=True)
    total_power = overview.get('total_power')
    if not total_power:
        return format_return(0)

    increase_power = CalculatorBase().get_increase_power_per_day()  # CalculatorBase().sync_increase_power_per_day()

    gas_stat = CalculatorBase().get_gas_stat()

    base_fee = CalculatorBase().get_base_fee()

    # 添加记录
    now = datetime.datetime.now().replace(second=0, minute=0, microsecond=0)
    CalculatorBase().add_total_power(
        record_time=now, power=total_power, increase_power=increase_power,
        block_reward=overview.get('block_reward'), avg_reward=overview.get('avg_reward'),
        avg_pledge=overview.get('avg_pledge'), total_supply=overview.get('total_supply'),
        circulating_supply=overview.get('circulating_supply'),
        burnt_supply=overview.get('burnt_supply'),
        total_pledge_collateral=overview.get('total_pledge_collateral'),
        total_multisig_locked_balance=overview.get('total_multisig_locked_balance'),
        total_market_pledge=overview.get('total_market_pledge'),
        price=overview.get('price'),
        avg_tipset_blocks=overview.get('avg_tipset_blocks'),
        pre_commit_sector_total_gas=gas_stat.get('pre_commit_sector'),
        prove_commit_sector_total_gas=gas_stat.get('prove_commit_sector'),
        submit_windowed_po_st_total_gas=gas_stat.get('submit_windowed_po_st'),
        base_fee=base_fee
    )
    return format_return(0)


@common_ajax_response
def sync_tipset(request):
    '''
    每天上午8点同步tipset
    '''
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    return TipsetBase().sync_tipset_2(date=date)


@common_ajax_response
def sync_temp_tipset(request):
    '''
    每半小时同步最新区块
    '''
    return TipsetBase().sync_temp_tipset()


@common_ajax_response
def sync_gas_fee(request):
    '''
    同步汽油费
    '''
    return CalculatorBase().sync_gas_fee()


@common_ajax_response
def sync_total_power_day_record(request):
    '''同步每日数据'''
    date = request.POST.get('date')
    return CalculatorBase().sync_total_power_day_record(date=date)
