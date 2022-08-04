import time
import logging
import decimal
import requests
import datetime

from django.db import transaction
from django.db.models import Avg, Q, F, Sum, Count

from explorer_s_common import debug, consts, cache, raw_sql
from explorer_s_common.utils import format_return, Validator, format_power, format_price
from explorer_s_common.decorator import validate_params, cache_required
from explorer_s_common.third.filscout_sdk import FilscoutBase
from explorer_s_common.third.filfox_sdk import FilfoxBase
from explorer_s_common.third.filecoin_sdk import FilecoinBase

from explorer_s_activity.consts import ERROR_DICT
from testnet_ranking.models import Miner, Peer, HelpRecord, RrmMiner, ActivityConfig


class IpfsunionBase(object):

    def fetch(self, url, data={}, headers={}):
        try:
            logging.warning('url--> %s' % url)
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36'}
            result = requests.get(url, headers=headers, timeout=10).json()
            # logging.warning('response--> %s' % result)
            return result
        except Exception as e:
            debug.get_debug_detail(e)
            return {}

    def get_miners(self, page_index=1, page_size=100):
        url = 'https://filscoutv3api.ipfsunion.cn/miner/list?page=%s&page_size=%s' % (page_index, page_size)
        return self.fetch(url=url)

    def get_peer(self, peer_id):
        url = 'https://filscoutv3api.ipfsunion.cn/peer/by_peerId/%s' % peer_id
        return self.fetch(url=url)


class RankingBase(object):

    def __init__(self):
        self.cache_key_reward_stat = 'test_net_reward_stat'
        self.cache_key_sp2_reward_stat = 'test_net_sp2_reward_stat'
        self.cache_timeout = 7 * 24 * 60 * 3600

    def sync_data(self):
        '''
        同步数据
        '''
        start_time = datetime.datetime.now()

        miners = self.sync_miners()

        count = 0
        for p in miners:
            with transaction.atomic():

                peer_id = p.get('peer_id')
                if not peer_id:
                    continue
                # 创建节点
                peer = self.sync_peer(peer_id=peer_id)

                miner_address = p.get('miner_address')
                if not miner_address:
                    continue
                count += 1
                print('[ %s ]矿工--> %s' % (count, miner_address))
                # 创建矿工
                miner, created = Miner.objects.get_or_create(miner_address=miner_address)
                miner.nick_name = p.get('nick_name')
                miner.peer = peer
                miner.increased_power = p.get('increased_power')
                miner.increased_power_str = p.get('increased_power_str')
                miner.raw_byte_power = p.get('raw_byte_power')
                miner.raw_byte_power_str = p.get('raw_byte_power_str')
                miner.save()

                time.sleep(0.2)

        if miners:
            # 清除无效矿工记录
            Miner.objects.filter(update_time__lt=start_time).delete()

        # 计算MINING POOL账号的排名
        self.set_rmd_miner_ranking()

        end_time = datetime.datetime.now()
        print('同步完成，耗时 %s s' % (end_time - start_time).total_seconds())
        return format_return(0)

    def sync_peer(self, peer_id):
        '''
        同步节点
        '''
        # print('peer_id-->', peer_id, 'info-->', info)
        peer, created = Peer.objects.get_or_create(peer_id=peer_id)
        # 如果已经有了区域了则不请求
        if peer.location_en:
            return peer

        result = IpfsunionBase().get_peer(peer_id=peer_id)
        if not result or result['code'] != 200:
            return peer
        info = result['data']['peer']
        peer.ip = info.get('ip')
        peer.longitude = decimal.Decimal(info.get('longitude', '0') or '0')
        peer.latitude = decimal.Decimal(info.get('latitude', '0') or '0')
        peer.location = info.get('location')
        location_en = info.get('location_en')
        peer.location_en = location_en
        # 是否亚洲
        if location_en and location_en.find('Asia') >= 0:
            peer.area = 0
        peer.save()
        return peer

    def sync_miners(self):
        '''
        同步矿工
        '''
        page_index = 1
        page_size = 100
        miners = []
        temp = []

        result = IpfsunionBase().get_miners(page_index=page_index, page_size=page_size)
        if result and result['code'] == 200 and len(result['data']['data']) > 0:
            temp = result['data']['data']

        while temp and page_index <= 1000:
            miners += temp
            # print('miners--->%s, page_index-->%s' % (len(miners), page_index))
            page_index += 1

            time.sleep(1)
            # 再次查询
            result = IpfsunionBase().get_miners(page_index=page_index, page_size=page_size)
            if result and result['code'] == 200:
                temp = result['data']['data']
            else:
                temp = []

        print('miners总数--->', len(miners))
        miners = [x for x in miners if x['raw_byte_power'] != '0' and x['increased_power'] != '0']
        print('去除无效数据之后的miners总数--->', len(miners))
        return miners

    def get_total_power(self, area=None):
        '''
        获取全网算力

        SELECT SUM(`increased_power`), SUM(`raw_byte_power`)
        FROM `testnet_ranking_miner` m, `testnet_ranking_peer` p
        WHERE m.`peer_id` = p.`peer_id` and area = 0;
        '''
        condition = ""
        if area is not None:
            condition = " AND area = %s " % area

        sql = """
            SELECT SUM(`increased_power`), SUM(`raw_byte_power`)
            FROM `testnet_ranking_miner` m, `testnet_ranking_peer` p
            WHERE m.`peer_id` = p.`peer_id` %s ;
        """ % condition

        return raw_sql.exec_sql(sql, [])[0]

    @validate_params
    def add_help_record(self, rmd_user_id, rmd_user_nick, power=0, record_time=None, order_id=None):
        '''
        添加助力记录
        '''
        if HelpRecord.objects.filter(order_id=order_id).count() > 0:
            return format_return(0)

        obj = HelpRecord.objects.create(
            rmd_user_id=rmd_user_id, rmd_user_nick=rmd_user_nick, power=power,
            record_time=record_time, order_id=order_id
        )
        return format_return(0, data={'obj_id': obj.id})

    def get_help_records(self, rmd_user_id=None):
        '''
        获取助力记录
        '''
        objs = HelpRecord.objects.filter()
        if rmd_user_id is not None:
            objs = objs.filter(rmd_user_id=rmd_user_id)
        return objs

    def get_total_help_power(self):
        '''
        查询助力的总算力
        '''
        return HelpRecord.objects.filter().aggregate(Sum('power'))['power__sum'] or 0

    @validate_params
    def add_config(self, rule, bhp, fil):
        obj = ActivityConfig.objects.create(rule=rule, bhp=bhp, fil=fil)
        return format_return(0, data={'obj_id': obj.id})

    def get_config(self):
        objs = ActivityConfig.objects.filter()
        return objs[0] if objs else None

    def add_rmd_miner(self, miner_address):
        obj, created = RrmMiner.objects.get_or_create(miner_address=miner_address)
        return format_return(0, data={'obj_id': obj.id})

    def get_rmd_miners(self, area=None):
        objs = RrmMiner.objects.filter()
        if area is not None:
            objs = objs.order_by('asia_ranking')
        else:
            objs = objs.order_by('ranking')
        return objs

    def set_rmd_miner_ranking(self):
        '''
        计算MINING POOL账号排名
        '''
        for rmd_miner in RrmMiner.objects.filter():
            rmd_miner.ranking = self.get_miner_ranking(miner_address=rmd_miner.miner_address)
            rmd_miner.asia_ranking = self.get_miner_ranking(miner_address=rmd_miner.miner_address, area=0)
            rmd_miner.save()

    def get_miner_ranking(self, miner_address, area=None):
        '''
        获取矿工排名
        '''

        ranking = 0
        # 获取当前矿工的原值算力
        miner = Miner.objects.filter(miner_address=miner_address)
        if not miner:
            return ranking
        miner = miner[0]

        # 大于此原值算力的个数
        if area is not None:
            ranking += Miner.objects.filter(raw_byte_power__gt=miner.raw_byte_power, peer__area=area).count()
        else:
            ranking += Miner.objects.filter(raw_byte_power__gt=miner.raw_byte_power).count()

        # 等于此原值算力的个数
        if area is not None:
            ranking += Miner.objects.filter(raw_byte_power=miner.raw_byte_power, miner_address__gt=miner_address, peer__area=area).order_by('miner_address').count()
        else:
            ranking += Miner.objects.filter(raw_byte_power=miner.raw_byte_power, miner_address__gt=miner_address).order_by('miner_address').count()

        return ranking + 1

    def get_miners(self, area=None):
        '''
        获取排名
        '''
        objs = Miner.objects.filter()
        if area is not None:
            objs = objs.filter(peer__area=area)
        return objs.order_by('-raw_byte_power')

    def get_miner_by_address(self, address):
        objs = Miner.objects.filter(miner_address=address)
        return objs[0] if objs else None

    def get_last_update_time(self):
        objs = Miner.objects.filter().order_by('-update_time')
        if objs:
            return objs[0].update_time
        else:
            return datetime.datetime.now()

    def sync_block_ranking(self):

        # 同步出块率
        records = FilscoutBase(net='spacerace').get_block_list()
        if records['code'] == 200:
            records = records['data']['list']
            cache_obj = cache.Cache()
            data = {
                'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'records': records
            }
            cache_obj.set('block_rate_ranking', data)

        # 同步出块列表
        records = FilfoxBase(net='spacerace').get_blocks()
        if records:
            records = records['miners']
            for per in records:
                per['power_str'] = format_power(decimal.Decimal(per['rawBytePower']))

            cache_obj = cache.Cache()
            data = {
                'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'records': records
            }
            cache_obj.set('block_list_ranking', data)
        return format_return(0)

    def get_reward_stat(self):
        return cache.Cache().get(key=self.cache_key_reward_stat) or {}

    def sync_reward_stat(self):
        '''
        同步奖励统计
        '''
        data = {
            'total_power': 0,
            'total_power_str': '',
            'global': 0,
            'africa': 0,
            'asia': 0,
            'europe': 0,
            'north_america': 0,
            'oceania': 0,
            'south_america': 0
        }

        region_mapping = {
            'global': '',
            'africa': '002',
            'asia': '142',
            'europe': '150',
            'north_america': '021',
            'oceania': '009',
            'south_america': '419'
        }
        for key in data:
            if region_mapping.get(key) is not None:
                records = FilecoinBase().get_reward_stat(region=region_mapping[key])
                if records['current_tier'] is not None:
                    data[key] = int(records['tiers'][records['current_tier']][1])
            # 全网总算力
            if region_mapping.get(key) == '':
                data['total_power'] = records['power']
                data['total_power_str'] = format_power(records['power'])

        # 保存进缓存
        cache_obj = cache.Cache()
        cache_obj.set(key=self.cache_key_reward_stat, value=data, time_out=self.cache_timeout)
        return format_return(0)

    def get_sp2_reward_stat(self):
        return cache.Cache().get(key=self.cache_key_sp2_reward_stat) or {}

    def sync_sp2_reward_stat(self):
        result = FilecoinBase().get_sp2_reward_stat()
        if not result:
            return format_return(0)

        rewards = {
            10 * 1024 * 1024 * 1024 * 1024: 10000,
            100 * 1024 * 1024 * 1024 * 1024: 20000,
            500 * 1024 * 1024 * 1024 * 1024: 50000,
            1024 * 1024 * 1024 * 1024 * 1024: 100000
        }
        data = {}
        items = []
        total_data_size = 0

        for per in result.get('payload', []):
            items.append({
                'miner': per['client'],
                'data_size': per['data_size'],
                'data_size_str': format_power(per['data_size']),
                'num_cids': per['num_cids'],
                'num_deals': per['num_deals'],
                'num_miners': per['num_miners']
            })
            total_data_size += per['data_size']
        # 排序
        data['items'] = sorted(items, key=lambda x: x['data_size'], reverse=True)
        data['total_data_size'] = total_data_size
        data['total_data_size_str'] = format_power(total_data_size)
        data['reward'] = 0

        for key in rewards:
            if total_data_size > key:
                data['reward'] = rewards[key]

        # 保存进缓存
        cache_obj = cache.Cache()
        cache_obj.set(key=self.cache_key_sp2_reward_stat, value=data, time_out=self.cache_timeout)
        return format_return(0)
