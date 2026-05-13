from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.views import View


class GroupsView(View):
    """Return all Django auth groups for the function config UI.

    Why: Arches core exposes no auth-group listing endpoint.
    """

    def get(self, request):
        groups = list(Group.objects.values("id", "name").order_by("name"))
        return JsonResponse({"groups": groups})


class GraphNodegroupsView(View):
    """Return nodegroups (with aliases) for a graph slug or UUID.

    Why: `api_get_nodegroup_tree` returns opaque DB-function tuples; the config
    panel needs (alias, name, nodegroup_id) triples for the nodegroup dropdown.
    """

    def get(self, request, graph_id):
        from arches.app.models.models import GraphModel, Node

        try:
            graph = GraphModel.objects.get(graphid=graph_id)
        except (GraphModel.DoesNotExist, ValueError):
            graph = GraphModel.objects.filter(slug=str(graph_id)).first()
            if not graph:
                return JsonResponse({"error": "Graph not found"}, status=404)

        nodegroups = (
            Node.objects.filter(graph=graph, nodegroup__isnull=False)
            .order_by("nodegroup_id", "alias")
            .distinct("nodegroup_id")
            .values("nodegroup_id", "alias", "name")
        )
        results = sorted(
            (
                {
                    "nodegroup_id": str(ng["nodegroup_id"]),
                    "alias": ng["alias"],
                    "name": ng["name"],
                }
                for ng in nodegroups
            ),
            key=lambda r: r["alias"] or "",
        )
        return JsonResponse({"nodegroups": results})
