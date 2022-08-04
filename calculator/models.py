from django.db import models


class TotalPower(models.Model):
    '''
    全网算力
    '''
    power = models.DecimalField('有效算力', max_digits=34, decimal_places=0, default=0)
    increase_power = models.DecimalField('全网算力增量', max_digits=34, decimal_places=0, default=0)
    block_reward = models.DecimalField('区块奖励', max_digits=34, decimal_places=0, default=0)
    avg_reward = models.DecimalField('24h平均挖矿收益 FIL/TiB', max_digits=10, decimal_places=4, default=0)
    avg_pledge = models.DecimalField('当前扇区质押量 FIL/32GiB', max_digits=10, decimal_places=4, default=0)
    total_supply = models.DecimalField('当前总供给', max_digits=34, decimal_places=0, default=0)
    circulating_supply = models.DecimalField('FIL流通量', max_digits=34, decimal_places=0, default=0)
    burnt_supply = models.DecimalField('燃烧量', max_digits=34, decimal_places=0, default=0)
    total_pledge_collateral = models.DecimalField('总前置质押', max_digits=34, decimal_places=0, default=0)
    total_multisig_locked_balance = models.DecimalField('总官方锁定量', max_digits=34, decimal_places=0, default=0)
    total_market_pledge = models.DecimalField('总市场质押', max_digits=34, decimal_places=0, default=0)
    price = models.DecimalField('fil价格', max_digits=10, decimal_places=4, default=0)
    avg_tipset_blocks = models.DecimalField('平均区块高度', max_digits=10, decimal_places=4, default=0)
    pre_commit_sector_total_gas = models.DecimalField('24小时复制证明p1总汽油费', max_digits=16, decimal_places=6, default=0)
    prove_commit_sector_total_gas = models.DecimalField('24小时复制证明p2总汽油费', max_digits=16, decimal_places=6, default=0)
    submit_windowed_po_st_total_gas = models.DecimalField('24小时时空证明总汽油费', max_digits=16, decimal_places=6, default=0)
    base_fee = models.DecimalField('基础费', max_digits=34, decimal_places=0, default=0)
    record_time = models.DateTimeField('记录时间')

    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-record_time", "-create_time", ]


class Tipset(models.Model):
    '''
    区块高度
    '''
    height = models.IntegerField('高度', default=0, db_index=True)
    total_win_count = models.IntegerField('总消息数量', default=0)
    total_reward = models.DecimalField('总区块奖励', max_digits=30, decimal_places=0, default=0)

    record_time = models.DateTimeField('产生时间', db_index=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-record_time", "-create_time", ]


class TipsetBlock(models.Model):
    '''
    区块
    '''
    tipset = models.ForeignKey('Tipset', related_name='blocks', on_delete=models.DO_NOTHING, null=True)
    height = models.IntegerField('高度', default=0, db_index=True)
    record_time = models.DateTimeField('产生时间', db_index=True)
    block_hash = models.CharField('消息hash', max_length=128, null=True)
    miner_address = models.CharField('矿工id', max_length=128, null=True)
    msg_count = models.IntegerField('消息数量', default=0)
    win_count = models.IntegerField('消息数量', default=0)
    reward = models.DecimalField('区块奖励', max_digits=30, decimal_places=0, default=0)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-create_time", ]


class TempTipsetBlock(models.Model):
    '''
    临时区块信息
    '''
    height = models.IntegerField('高度', default=0, db_index=True)
    record_time = models.DateTimeField('产生时间', db_index=True)
    block_hash = models.CharField('消息hash', max_length=128, null=True)
    miner_address = models.CharField('矿工id', max_length=128, null=True)
    msg_count = models.IntegerField('消息数量', default=0)
    win_count = models.IntegerField('消息数量', default=0)
    reward = models.DecimalField('区块奖励', max_digits=30, decimal_places=0, default=0)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)


class SearchLog(models.Model):
    '''
    '''
    search_type_choices = ((0, '有效算力产出计算'), (1, '矿机产出计算'), (2, '有效算力成本计算'),)

    user_id = models.CharField('user_id', max_length=32)
    start_date = models.DateTimeField('开挖时间', null=True)
    speed = models.FloatField('封装速度', default=0)
    power = models.FloatField('有效算力', default=0)
    store_power = models.FloatField('存储空间', default=0)
    cost = models.FloatField('投入成本', default=0)
    price = models.FloatField('币价', default=0)
    increase = models.FloatField('增速', default=0)
    store_cost = models.FloatField('单T存储空间成本', default=0)
    hardware_cost = models.FloatField('机柜与电力成本', default=0)
    depreciation_days = models.FloatField('折旧天数', default=0)
    search_type = models.IntegerField('查询类型', default=0, choices=search_type_choices)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-create_time", ]


class TotalPowerDay(models.Model):

    date = models.DateField('时间')
    power = models.DecimalField('有效算力', max_digits=34, decimal_places=0, default=0)
    increase_power = models.DecimalField('全网算力增量', max_digits=34, decimal_places=0, default=0)
    avg_reward = models.DecimalField('24h平均挖矿收益 FIL/TiB', max_digits=10, decimal_places=4, default=0)
    avg_pledge = models.DecimalField('当前扇区质押量 FIL/32GiB', max_digits=10, decimal_places=4, default=0)
    luck = models.DecimalField('幸运值', max_digits=10, decimal_places=8, default=0)
    burnt_supply = models.DecimalField('燃烧量', max_digits=34, decimal_places=0, default=0)
    base_fee = models.DecimalField('基础费', max_digits=34, decimal_places=0, default=0)
    circulating_supply = models.DecimalField('FIL流通量', max_digits=34, decimal_places=0, default=0)
    pre_commit_sector_total_gas = models.DecimalField('24小时复制证明p1总汽油费', max_digits=16, decimal_places=6, default=0)
    prove_commit_sector_total_gas = models.DecimalField('24小时复制证明p2总汽油费', max_digits=16, decimal_places=6, default=0)
    submit_windowed_po_st_total_gas = models.DecimalField('24小时时空证明总汽油费', max_digits=16, decimal_places=6, default=0)
    create_gas = models.DecimalField('生产gas', max_digits=16, decimal_places=6, default=0)
    keep_gas = models.DecimalField('维护gas', max_digits=16, decimal_places=6, default=0)
    packing_power = models.DecimalField('全网封装量', max_digits=34, decimal_places=0, default=0)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        ordering = ["-date", "-create_time", ]


class GasFeeDay(models.Model):
    '''每天的gas费'''
    date = models.DateField('时间')
    method = models.CharField('类别', max_length=64)
    count = models.IntegerField('数量', default=0)
    gas_limit = models.DecimalField('平均Gas限额', max_digits=34, decimal_places=2, default=0)
    gas_fee_cap = models.DecimalField('gas_fee_cap', max_digits=34, decimal_places=2, default=0)
    gas_premium = models.DecimalField('gas_premium', max_digits=34, decimal_places=2, default=0)
    gas_used = models.DecimalField('平均Gas消耗', max_digits=34, decimal_places=2, default=0)
    fee = models.DecimalField('平均手续费', max_digits=34, decimal_places=2, default=0)
    total_fee = models.DecimalField('总手续费', max_digits=34, decimal_places=2, default=0)

    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ["-date", "-create_time", ]
