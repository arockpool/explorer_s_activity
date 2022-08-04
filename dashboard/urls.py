from django.conf.urls import url

from dashboard import views, views_2

urlpatterns = [
    url(r'^get_overview$', views.get_overview),
    url(r'^get_block_list$', views.get_block_list),
    url(r'^get_ranking$', views.get_ranking),
    url(r'^get_pool_miners$', views.get_pool_miners),
    url(r'^get_miner_distribution$', views.get_miner_distribution),
    url(r'^get_power_increase$', views.get_power_increase),
    url(r'^sync_power_increase$', views.sync_power_increase),

    url(r'^v2/get_overview$', views_2.get_overview),
    url(r'^v2/get_power_trend$', views_2.get_power_trend),
    url(r'^v2/get_miner_ranking$', views_2.get_miner_ranking),
    url(r'^v2/get_block_list$', views_2.get_block_list),
    url(r'^v2/get_power_distribution$', views_2.get_power_distribution),
    url(r'^v2/get_pool_overview$', views_2.get_pool_overview),
    url(r'^v2/get_pool_miners$', views_2.get_pool_miners),
    url(r'^v2/get_pool_trend$', views_2.get_pool_trend),
    url(r'^v2/get_pool_mines$', views_2.get_pool_mines),
    url(r'^v2/get_pool_last_block_info$', views_2.get_pool_last_block_info),
    url(r'^v2/sync_day_pool_overview$', views_2.sync_day_pool_overview),

]
