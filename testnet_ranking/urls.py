from django.conf.urls import url

from testnet_ranking import views

urlpatterns = [
    url(r'^get_ranking$', views.get_ranking),
    url(r'^get_block_rate_ranking$', views.get_block_rate_ranking),
    url(r'^get_block_ranking$', views.get_block_ranking),
    url(r'^get_activity_config$', views.get_activity_config),
    url(r'^get_help_powers$', views.get_help_powers),
    url(r'^get_help_records$', views.get_help_records),
    url(r'^get_reward_stat$', views.get_reward_stat),
    url(r'^get_sp2_reward_stat$', views.get_sp2_reward_stat),

    url(r'^add_help_record$', views.add_help_record),

    url(r'^sync_data$', views.sync_data),
    url(r'^sync_block_ranking$', views.sync_block_ranking),
    url(r'^sync_reward_stat$', views.sync_reward_stat),
    url(r'^sync_sp2_reward_stat$', views.sync_sp2_reward_stat),
]
