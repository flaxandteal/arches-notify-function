from django.urls import path

from .views import GraphNodegroupsView, GroupsView

urlpatterns = [
    path(
        "api/notifications/groups",
        GroupsView.as_view(),
        name="notification_groups",
    ),
    path(
        "api/notifications/nodegroups/<str:graph_id>",
        GraphNodegroupsView.as_view(),
        name="notification_nodegroups",
    ),
]
