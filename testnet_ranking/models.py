from django.db import models


class Peer(models.Model):
    '''
    节点
    '''
    area_choice = ((0, '亚洲'), (1, '欧洲'), (2, '北美洲'), (3, '南美洲'), (4, '大洋洲'), (5, '非洲'), (6, '南极洲'), (10, '其他'))

    peer_id = models.CharField('peer_id', max_length=192)
    ip = models.CharField('ip', max_length=192, null=True)
    longitude = models.DecimalField('经度', max_digits=10, decimal_places=6, default=0)
    latitude = models.DecimalField('纬度', max_digits=10, decimal_places=6, default=0)
    location = models.CharField('区域名称', max_length=192, null=True)
    location_en = models.CharField('区域英文名称', max_length=192, null=True)
    area = models.IntegerField('区域标记', default=10)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        ordering = ["-create_time", ]


class Miner(models.Model):
    '''
    矿工表
    '''
    miner_address = models.CharField('矿工地址', max_length=128)
    nick_name = models.CharField('矿工昵称', max_length=128, null=True)
    peer = models.ForeignKey('Peer', on_delete=models.DO_NOTHING, null=True)
    increased_power = models.BigIntegerField('有效算力', default=0)
    increased_power_str = models.CharField('有效算力展示', max_length=64, null=True)
    raw_byte_power = models.BigIntegerField('原值算力', default=0)
    raw_byte_power_str = models.CharField('原值算力展示', max_length=64, null=True)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        ordering = ["-create_time", ]


class RrmMiner(models.Model):
    '''
    矿工表
    '''
    miner_address = models.CharField('矿工地址', max_length=128)
    ranking = models.IntegerField('排名', default=0)
    asia_ranking = models.IntegerField('亚洲排名', default=0)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-create_time", ]


class HelpRecord(models.Model):
    '''
    助力记录
    '''
    rmd_user_id = models.CharField('MINING POOL的用户id', max_length=32)
    rmd_user_nick = models.CharField('MINING POOL的用户名称', max_length=128, null=True)
    power = models.DecimalField('算力', max_digits=10, decimal_places=2, default=0)
    record_time = models.DateTimeField("记录时间", null=True)
    order_id = models.CharField("订单号", max_length=64, null=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-record_time", ]


class ActivityConfig(models.Model):
    '''
    活动配置
    '''
    rule = models.TextField('规则')
    bhp = models.DecimalField('奖励BHP', max_digits=10, decimal_places=2, default=0)
    fil = models.DecimalField('奖励FIL', max_digits=10, decimal_places=2, default=0)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-create_time", ]
