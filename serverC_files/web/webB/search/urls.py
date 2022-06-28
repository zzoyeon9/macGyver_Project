from django.urls import path
from . import views

app_name='search'

urlpatterns = [

    path('memberlist', views.read_Member, name='memberlist'),
    path('memberlist/creating', views.goToCreate, name='creating'),
    path('memberlist/created', views.createMemberInfo, name='created'),
    path('memberlist/updated', views.updateMemberInfo, name='updated'),
    path('memberlist/updating', views.goToUpdate, name='updating'),
    path('memberlist/deleting', views.deleteMemberInfo, name='deleting'),
]
