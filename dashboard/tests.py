import json

from django.test import TestCase
from django.test.client import Client

from explorer_s_common.utils import format_return, format_price, format_power


class DashboardTestCase(TestCase):

    def setUp(self):
        self.user_id = '1'
        self.client = Client(HTTP_USERID=self.user_id)

    def test_get_overview(self):
        result = self.client.post(
            '/activity/api/dashboard/get_overview', {}
        ).json()
        print(result)

    def test_get_pool_miners(self):
        result = self.client.post(
            '/activity/api/dashboard/get_pool_miners', {}
        ).json()
        print(result)

    def test_get_miner_distribution(self):
        result = self.client.post(
            '/activity/api/dashboard/get_miner_distribution', {}
        ).json()
        print(result)

    def test_get_block_list(self):
        result = self.client.post(
            '/activity/api/dashboard/get_block_list', {}
        ).json()
        print(result)

    def test_get_ranking(self):
        result = self.client.post(
            '/activity/api/dashboard/get_ranking', {}
        ).json()
        print(result)
