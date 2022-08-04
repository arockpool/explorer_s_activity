import json
import math
import time
import decimal
import datetime
from collections import Iterable

from django.http import HttpResponse

from explorer_s_common.decorator import common_ajax_response
from explorer_s_common.utils import format_return, format_price, format_power, str_2_power
from explorer_s_common.page import Page
from explorer_s_common import inner_server, cache
from explorer_s_common.third.filscout_sdk import FilscoutBase
from explorer_s_common.third.filfox_sdk import FilfoxBase

from explorer_s_activity import consts
from calculator.interface import CalculatorBase


@common_ajax_response
def search_logs(request):
    '''
    获取计算信息
    '''

    search_type = request.POST.get('search_type')
    page_index = int(request.POST.get('page_index', 1))
    page_count = min(int(request.POST.get('page_count', 10)), 50)

    objs = CalculatorBase().search_logs_for_admin(search_type=search_type)
    data = Page(objs, page_count).page(page_index)

    result = []
    for per in data['objects']:
        result.append({
            'create_time': per.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'start_date': per.start_date.strftime('%Y-%m-%d') if per.start_date else '',
            'speed': per.speed, 'power': per.power, 'store_power': per.store_power,
            'cost': per.cost, 'price': per.price, 'increase': per.increase,
            'store_cost': per.store_cost, 'hardware_cost': per.hardware_cost,
            'depreciation_days': per.depreciation_days
        })

    return format_return(0, data={
        'objs': result, 'total_page': data['total_page'], 'total_count': data['total_count']
    })

    return format_return(0, data=info)
