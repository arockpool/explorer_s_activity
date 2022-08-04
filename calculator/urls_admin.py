from django.conf.urls import url

from calculator import views_admin

urlpatterns = [
    url(r'^search_logs$', views_admin.search_logs),

]
