from django.conf.urls import url

from calculator import views

urlpatterns = [
    url(r'^get_calculate_info$', views.get_calculate_info),
    url(r'^get_calculate_sum$', views.get_calculate_sum),
    url(r'^get_calculate_detail$', views.get_calculate_detail),
    url(r'^get_quick_calculate_sum$', views.get_quick_calculate_sum),
    url(r'^get_cost_calculate_sum$', views.get_cost_calculate_sum),
    url(r'^get_calculate_sum_v2$', views.get_calculate_sum_v2),
    url(r'^get_usd_rate$', views.get_usd_rate),

    url(r'^get_power_overview$', views.get_power_overview),

    url(r'^sync_total_power_per_hour$', views.sync_total_power_per_hour),
    url(r'^sync_tipset$', views.sync_tipset),
    url(r'^sync_temp_tipset$', views.sync_temp_tipset),
    url(r'^sync_gas_fee$', views.sync_gas_fee),
    url(r'^sync_total_power_day_record$', views.sync_total_power_day_record),

    # 查看器相关
    url(r'^viewer/get_lookups$', views.get_lookups),
]
