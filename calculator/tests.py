import json
import math
import decimal
import datetime

from django.test import TestCase
from django.test.client import Client

from explorer_s_common.utils import format_return, Validator, format_power, format_price, format_fil, str_2_power
from calculator.interface import CalculatorBase, TipsetBase, LookupBase

from calculator.models import TotalPowerDay


class CalculatorTestCase(TestCase):

    def setUp(self):
        self.user_id = '1'
        self.client = Client(HTTP_USERID=self.user_id)

    def init_day_total_power(self):
        start_date = datetime.datetime(2020, 8, 25)

        data = [1, 10.152279629413, 22.8426291661792, 30.4568388882389, 40.8380235611176, 51.2192082339964, 61.6003929068752, 71.9815775797539, 80.6535488073502, 89.3255200349465, 97.9974912625428, 106.669462490139, 115.822341221413, 124.975219952686, 134.12809868396, 151.746931904335, 169.36576512471, 186.984598345085, 204.60343156546, 217.908876642997, 231.214321720533, 244.51976679807, 247.038047320404, 249.556327842738, 252.074608365072, 261.500979616951, 270.92735086883, 280.353722120709, 289.780093372588, 300.250891090005, 310.721688807421, 321.192486524838, 331.663284242254, 341.556885312759, 351.450486383264, 361.344087453769, 371.237688524274, 378.21588482743, 385.194081130585, 392.172277433741, 385.92987762343, 379.687477813119, 373.445078002808, 367.202678192498,
                399.535569215046, 431.868460237594, 464.201351260143, 487.956945583588, 511.712539907032, 535.468134230477, 559.223728553922, 583.951257115955, 608.678785677988, 633.406314240022, 658.133842802055, 650.072302887641, 642.010762973227, 633.949223058813, 614.912361961006, 567.118932685017, 519.325503409028, 631.357521366615, 714.703434453807, 695.143846394508, 686.839027402447, 678.534208410385, 720.842277756184, 727.309813153248, 718.786675651719, 745.731117437805, 772.675559223891, 758.305995952882, 781.404240362902, 785.54872847, 801.42631404, 813.27319717, 825.77275976, 845.86731084, 861.16343053, 875.89757411, 895.15929413, 912.37763214, 920.83764521, 941.39732107, 959.34955978, 976.56955978, 993.78955978, 1011.00955978, 1028.22955978, 1045.44955978, 1066.4844970703, 1082.0190734863]

        for i in range(len(data)):
            d = start_date + datetime.timedelta(days=i)
            TotalPowerDay.objects.get_or_create(date=d, power=data[i] * math.pow(1024, 5), increase_power=10 * math.pow(1024, 5), luck=0.93)

    def test_get_day_reward_per_t(self):
        result = CalculatorBase().get_day_reward_per_t(
            27, decimal.Decimal(14.83), decimal.Decimal(855), decimal.Decimal(5)
        )
        print(result)

    def test_calculator(self):
        # result = self.client.post('/activity/api/calculator/sync_total_power_per_hour').json()
        # print(result)

        now = datetime.datetime.now().replace(second=0, minute=0, microsecond=0)
        yesterday = now - datetime.timedelta(hours=25)
        CalculatorBase().add_total_power(record_time=yesterday, power=972632693214806016, pre_commit_sector_total_gas='12050.535902',
                                         prove_commit_sector_total_gas='30127.670277', submit_windowed_po_st_total_gas='9205.475723')
        yesterday = now - datetime.timedelta(hours=24)
        CalculatorBase().add_total_power(record_time=yesterday, power=725 * 1024 * 1024 * 1024 * 1024 * 1024, pre_commit_sector_total_gas='10000.535902',
                                         prove_commit_sector_total_gas='30000.670277', submit_windowed_po_st_total_gas='9000.475723')
        yesterday = now - datetime.timedelta(hours=23)
        CalculatorBase().add_total_power(record_time=yesterday, power=750 * 1024 * 1024 * 1024 * 1024 * 1024, pre_commit_sector_total_gas='9000.535902',
                                         prove_commit_sector_total_gas='29000.670277', submit_windowed_po_st_total_gas='8000.475723')
        result = self.client.post('/activity/api/calculator/get_calculate_info').json()
        print(result)
        # increase_power_per_day = result['data']['increase_power_per_day_str']

        # print('详细计算器')
        # result = self.client.post('/activity/api/calculator/get_calculate_detail', data={
        #     'cost': 350000, 'current_date': '2020-11-23', 'init_power': 0,
        #     'increase_power_per_day': 14.83, 'price': 29, 'total_power': 200
        # }).json()
        # print(json.dumps(result['data'][:10], indent=2))

        print('汇总计算器')
        result = self.client.post('/activity/api/calculator/get_calculate_sum', data={
            'cost': 350000, 'current_date': '2020-11-23', 'init_power': 120,
            'increase_power_per_day': 14.83, 'price': 29, 'total_power': 120
        }).json()
        print(json.dumps(result['data'], indent=2))

        # print('快速计算器')
        # result = self.client.post('/activity/api/calculator/get_quick_calculate_sum', data={
        #     'cost': 25000, 'total_power': 120, 'price': 35.78, 'increase_power_per_day': 11, 'user_id': '1'
        # }).json()
        # print(json.dumps(result['data'], indent=2))

        # print('显示日志')
        # result = self.client.post('/activity/admin/calculator/search_logs', data={}).json()
        # print(json.dumps(result['data'], indent=2))

    def test_tipset(self):

        blocks = [{
            "block_hash": "bafy2bzacedw4lllhogemgvljwmgze2lip2kabt3h3gqrlkonwz7ude472bcei",
            "miner": "f02398",
            "message_count": 47,
            "reward": "7.25",
            "reward_str_in_list": "14.51 FIL",
            "total_reward": "14.508825125220381"
        }]

        # result = TipsetBase().add_tipset(height=0, blocks=blocks)
        # print('成功：', result)

        print('同步结果:')
        result = TipsetBase().sync_tipset(date='2020-11-13')
        print(result)

    def test_sync_total_power_per_hour(self):
        result = self.client.post('/activity/api/calculator/sync_total_power_per_hour').json()
        print(result)

    def test_emodel(self):
        self.init_day_total_power()

        result = self.client.post('/activity/api/calculator/viewer/get_lookups', data={}).json()
        print(json.dumps(result['data'][:5], indent=2))
