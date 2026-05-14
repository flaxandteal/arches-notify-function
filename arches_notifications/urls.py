from django.urls import path

from .views import (
    DeleteNotificationTypeView,
    EmailTemplatesView,
    GraphNodegroupsView,
    GroupsView,
)

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
    path(
        "api/notifications/email-templates",
        EmailTemplatesView.as_view(),
        name="notification_email_templates",
    ),
    path(
        "api/notifications/type/<uuid:type_id>",
        DeleteNotificationTypeView.as_view(),
        name="notification_type_delete",
    ),
]
