from django.conf.urls import url, include

urlpatterns = [
    url(r'^activity/api/testnet_ranking/', include('testnet_ranking.urls')),
    url(r'^activity/api/dashboard/', include('dashboard.urls')),

    url(r'^activity/api/calculator/', include('calculator.urls')),
    url(r'^activity/admin/calculator/', include('calculator.urls_admin')),
]
