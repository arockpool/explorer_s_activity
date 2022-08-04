from django.db import models


class PoolMiner(models.Model):
    '''
    矿池矿工
    '''
    miner_address = models.CharField('矿工id', max_length=128)
    power = models.DecimalField('有效算力', max_digits=34, decimal_places=0, default=0)
    increase_power = models.DecimalField('封装量', max_digits=34, decimal_places=0, default=0)
    increase_power_offset = models.DecimalField('新增算力', max_digits=34, decimal_places=0, default=0)
    total_reward = models.DecimalField('总产出', max_digits=20, decimal_places=4, default=0)
    avg_reward = models.DecimalField('24h平均挖矿收益 FIL/TiB', max_digits=10, decimal_places=4, default=0)
    luck = models.DecimalField('幸运值', max_digits=8, decimal_places=4, default=0)
    total_block_count = models.IntegerField('总出块数', default=0)
    total_win_count = models.IntegerField('总赢票数', default=0)
    sector_size = models.DecimalField('扇区大小', max_digits=16, decimal_places=0, default=0)
    reward = models.DecimalField('24小时产出', max_digits=20, decimal_places=4, default=0)
    block_count = models.IntegerField('24小时出块数', default=0)
    ip = models.CharField('ip地址', max_length=32, null=True)
    area = models.CharField('区域', max_length=32, null=True)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        ordering = ["-create_time", ]


class PoolMinerDay(models.Model):
    '''
    矿池矿工
    '''
    date = models.DateTimeField('日期')
    miner_address = models.CharField('矿工id', max_length=128, null=True)
    power = models.DecimalField('有效算力', max_digits=34, decimal_places=0, default=0)
    increase_power = models.DecimalField('封装量', max_digits=34, decimal_places=0, default=0)
    increase_power_offset = models.DecimalField('新增算力', max_digits=34, decimal_places=0, default=0)
    total_reward = models.DecimalField('总产出', max_digits=20, decimal_places=4, default=0)
    avg_reward = models.DecimalField('24h平均挖矿收益 FIL/TiB', max_digits=10, decimal_places=4, default=0)
    luck = models.DecimalField('幸运值', max_digits=8, decimal_places=4, default=0)
    total_block_count = models.IntegerField('总出块数', default=0)
    total_win_count = models.IntegerField('总赢票数', default=0)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-create_time", ]
