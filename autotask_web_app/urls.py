from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^account/profile/(?P<id>[0-9]+)/input_validation/$', views.input_validation, name='input_validation'),
    url(r'^account/profile/(?P<id>[0-9]+)/input_validation/(?P<validation_group_id>[0-9]+)$', views.edit_validation_group, name='edit_validation_group'),
    url(r'^delete_validation_group/(?P<id>[0-9]+)', views.delete_validation_group, name='delete_validation_group'),
    url(r'^delete_validation/(?P<id>[0-9]+)', views.delete_validation, name='delete_validation'),
    url(r'^account/profile/(?P<id>[0-9]+)/$', views.profile, name='profile'),
    url(r'^create_picklist', views.create_picklist_database, name='create_picklist_database'),
    url(r'^ajax_create_picklist', views.ajax_create_picklist, name='ajax_create_picklist'),
    url(r'^generate_entities/(?P<id>[0-9]+)/$', views.generate_entities, name='generate_entities'),
    url(r'^$', views.home, name='home'),
    url(r'^autotask_validation$', views.index, name='index'),
    url(r'^create_ticket/(?P<id>[0-9]+)/$', views.create_ticket, name='create_ticket'),
    url(r'^ajax_create_ticket', views.ajax_create_ticket, name='ajax_create_ticket'),
    url(r"^account/signup/$", views.SignupView.as_view(), name="account_signup"),
    url(r'^account/', include('account.urls')),
]
