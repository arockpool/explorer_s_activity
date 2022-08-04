import json

from django.test import TestCase
from django.test.client import Client

from testnet_ranking.interface import RankingBase
from testnet_ranking.models import Peer, Miner


class RankingTestCase(TestCase):

    def setUp(self):
        self.user_id = '1'
        self.client = Client(HTTP_USERID=self.user_id)
        self.init_data()

    def init_data(self):
        RankingBase().add_help_record(rmd_user_id='rmd_001', rmd_user_nick='stranger', power=4, record_time='2020-06-06 12:12:12', order_id='001')
        RankingBase().add_help_record(rmd_user_id='rmd_002', rmd_user_nick='半夜没事瞎溜达', power=5, record_time='2020-06-06 12:12:13', order_id='002')
        RankingBase().add_help_record(rmd_user_id='rmd_002', rmd_user_nick='半夜没事瞎溜达', power=6, record_time='2020-06-06 12:12:14', order_id='003')

        RankingBase().add_rmd_miner(miner_address='t002')

        RankingBase().add_config(rule="这是规则1111", bhp=1000, fil=9999)

        peer = Peer.objects.create(peer_id='1', ip='127.0.0.1', area='0')
        Miner.objects.create(miner_address='t001', peer=peer, increased_power=1000, increased_power_str='1M', raw_byte_power=1000, raw_byte_power_str='1M')
        peer = Peer.objects.create(peer_id='2', ip='127.0.0.2', area='0')
        Miner.objects.create(miner_address='t002', peer=peer, increased_power=1100, increased_power_str='1.1M', raw_byte_power=1100, raw_byte_power_str='1.1M')
        peer = Peer.objects.create(peer_id='3', ip='127.0.0.3', area='0')
        Miner.objects.create(miner_address='t003', peer=peer, increased_power=1200, increased_power_str='1.2M', raw_byte_power=1200, raw_byte_power_str='1.2M')
        peer = Peer.objects.create(peer_id='4', ip='127.0.0.4', area='0')
        Miner.objects.create(miner_address='t004', peer=peer, increased_power=1300, increased_power_str='1.3M', raw_byte_power=1300, raw_byte_power_str='1.3M')
        peer = Peer.objects.create(peer_id='5', ip='127.0.0.5', area='0')
        Miner.objects.create(miner_address='t005', peer=peer, increased_power=1400, increased_power_str='1.4M', raw_byte_power=1400, raw_byte_power_str='1.4M')

    def test_sync_data(self):
        RankingBase().sync_data()

    def test_get_ranking(self):
        result = self.client.post(
            '/activity/api/testnet_ranking/get_ranking', {}
        ).json()
        print(result)

        result = self.client.post(
            '/activity/api/testnet_ranking/get_activity_config', {}
        ).json()
        print(result)

        result = self.client.post(
            '/activity/api/testnet_ranking/get_help_powers', {'rmd_user_id': 'rmd_002'}
        ).json()
        print(result)

        result = self.client.post(
            '/activity/api/testnet_ranking/get_help_records', {}
        ).json()
        print(result)

    def test_reward_stat(self):
        result = self.client.post(
            '/activity/api/testnet_ranking/sync_reward_stat', {}
        ).json()
        print(result)

        result = self.client.post(
            '/activity/api/testnet_ranking/get_reward_stat', {}
        ).json()
        print(result)

    def test_sp2_reward_stat(self):
        result = self.client.post(
            '/activity/api/testnet_ranking/sync_sp2_reward_stat', {}
        ).json()
        print(result)

        result = self.client.post(
            '/activity/api/testnet_ranking/get_sp2_reward_stat', {}
        ).json()
        print(result)
