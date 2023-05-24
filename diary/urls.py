from django.urls import path
from . import views

urlpatterns = [
    path('lists', views.diary_lists),
    path('<uuid:diaryId>', views.diary_one),
    path('create', views.diary_create),
    path('del', views.diary_del),
    path('update', views.diary_update),
    path('createImg', views.create_img),
]