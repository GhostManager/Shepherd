"""This contains all of the URL mappings for the catalog application. The `urlpatterns` list
routes URLs to views. For more information please see:

    https://docs.djangoproject.com/en/2.1/topics/http/urls/
"""

from . import views
from django.conf.urls import include
from django.urls import path, re_path


# URLs for the basic domain views
urlpatterns = [
    path('', views.index, name='index'),
    path('domains/', views.DomainListView.as_view(), name='domains'),
    path('avail_domains/', views.AvailDomainListView.as_view(), name='available-domains'),
    path('active_domains/', views.ActiveDomainListView.as_view(), name='active-domains'),
    path('res_domains/', views.ResDomainListView.as_view(), name='reserved-domains'),
    path('graveyard/', views.GraveyardListView.as_view(), name='graveyard'),
    path('domain/<int:pk>', views.DomainDetailView.as_view(), name='domain-detail'),
    path('mydomains/', views.ActiveDomainsByUserListView.as_view(), name='my-domains'),
    path('error/', views.error, name='error'),
    path('profile/', views.profile, name='profile'),
]

# URLs for creating, updating, and deleting project histories
urlpatterns += [
    path('history/<int:pk>/create/', views.HistoryCreate.as_view(), name='history_create'),
    path('history/<int:pk>/update/', views.HistoryUpdate.as_view(), name='history_update'),
    path('history/<int:pk>/delete/', views.HistoryDelete.as_view(), name='history_delete'),
]

# URLs for creating, updating, and deleting domains
urlpatterns += [
    path('domain/create/', views.DomainCreate.as_view(), name='domain_create'),
    path('domain/<int:pk>/update/', views.DomainUpdate.as_view(), name='domain_update'),
    path('domain/<int:pk>/delete/', views.DomainDelete.as_view(), name='domain_delete'),
]

# URLs for domain status change functions
urlpatterns += [
    path('checkout/<int:pk>', views.checkout, name='checkout'),
    path('release/<int:pk>', views.release, name='release'),
]

# URLs for management functions
urlpatterns += [
    path('management/', views.management, name='management'),
    path('update/', views.update, name='update'),
    path('update_dns/', views.update_dns, name='update_dns'),
    path('upload/csv/', views.upload_csv, name='upload_csv'),
]