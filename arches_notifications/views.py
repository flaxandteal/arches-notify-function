import json

from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.views import View


class NotificationTypesView(View):
    """Return all NotificationType records for use in the function config UI."""

    def get(self, request):
        from arches.app.models.models import NotificationType
        types = list(
            NotificationType.objects.values("typeid", "name", "emailnotify", "webnotify")
        )
        # typeid is a UUID — serialise to string
        for t in types:
            t["typeid"] = str(t["typeid"])
        return JsonResponse({"notification_types": types})


class GroupsView(View):
    """Return all Django auth groups for use in the function config UI."""

    def get(self, request):
        groups = list(Group.objects.values("id", "name").order_by("name"))
        return JsonResponse({"groups": groups})


class GraphNodegroupsView(View):
    """Return nodegroups (with aliases) for a given graph slug or UUID."""

    def get(self, request, graph_id):
        from arches.app.models.models import NodeGroup, Node
        # Resolve graph_id — accept slug or UUID
        from arches.app.models.models import GraphModel
        try:
            graph = GraphModel.objects.get(graphid=graph_id)
        except (GraphModel.DoesNotExist, Exception):
            graph = GraphModel.objects.filter(slug=str(graph_id)).first()
            if not graph:
                return JsonResponse({"error": "Graph not found"}, status=404)

        # Get one representative node per nodegroup to surface the alias
        nodegroups = (
            Node.objects.filter(graph=graph, nodegroup__isnull=False)
            .values("nodegroup_id", "alias", "name")
            .order_by("alias")
            .distinct("nodegroup_id")
        )
        results = [
            {
                "nodegroup_id": str(ng["nodegroup_id"]),
                "alias": ng["alias"],
                "name": ng["name"],
            }
            for ng in nodegroups
        ]
        return JsonResponse({"nodegroups": results})
