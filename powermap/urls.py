from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^cars/popup/(?P<car_id>\d+)/$', views.car_popup, name='car_popup'),
    url(
        r'^note_popup/(?P<note_id>\d+)/$',
        views.note_popup,
        name='note_popup'
    ),
    url(
        r'^next_location_popup/$',
        views.next_location_popup,
        name='next_location_popup'
    ),
    url(
        r'^cars/(?P<car_id>[0-9]+)/set_active/$',
        views.set_active,
        name='set_active'
    ),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^login_user/$', views.login_user, name='login_user'),
    url(r'^cars/register_car/$', views.register_car, name='register_car'),
    url(
        r'^cars/register_success/$',
        views.register_success,
        name='register_success'
    )

]
