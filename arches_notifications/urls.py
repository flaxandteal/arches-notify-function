from django.urls import path

from .views import GraphNodegroupsView, GroupsView, NotificationTypesView

urlpatterns = [
    path(
        "api/notifications/types",
        NotificationTypesView.as_view(),
        name="arches_notifications_types",
    ),
    path(
        "api/notifications/groups",
        GroupsView.as_view(),
        name="arches_notifications_groups",
    ),
    path(
        "api/notifications/nodegroups/<str:graph_id>",
        GraphNodegroupsView.as_view(),
        name="arches_notifications_nodegroups",
    ),
]
