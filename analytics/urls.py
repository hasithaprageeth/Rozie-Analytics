from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
	path('analytics/recent', views.recentAnalytics, name='recentAnalytics'),
	path('analytics/full', views.fullAnalytics, name='fullAnalytics'),
	path('analytics/detail/recent/<int:cluster>', views.recentAnalyticsDetail, name='recentAnalyticsDetail'),
	path('analytics/detail/full/<int:cluster>', views.fullAnalyticsDetail, name='fullAnalyticsDetail'),
	path('analytics/recent/update', views.recentAnalyticsUpdate, name='recentAnalyticsUpdate'),
	path('analytics/full/update', views.fullAnalyticsUpdate, name='fullAnalyticsUpdate'),
	path('analytics/detail/recent/<int:cluster>/update', views.recentAnalyticsDetailUpdate, name='recentAnalyticsDetailUpdate'),
	path('analytics/detail/full/<int:cluster>/update', views.fullAnalyticsDetailUpdate, name='fullAnalyticsDetailUpdate')		
]