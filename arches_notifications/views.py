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

        # All nodes that belong to a nodegroup, in one query — bucket them
        # into nodegroups in Python so the panel can offer a per-nodegroup
        # node picker for change-detection rules.
        rows = (
            Node.objects.filter(graph=graph, nodegroup__isnull=False)
            .values("nodegroup_id", "alias", "name", "nodeid", "datatype")
        )

        by_nodegroup: dict[str, dict] = {}
        for r in rows:
            ng_id = str(r["nodegroup_id"])
            bucket = by_nodegroup.setdefault(
                ng_id,
                {"nodegroup_id": ng_id, "alias": None, "name": None, "nodes": []},
            )
            bucket["nodes"].append(
                {
                    "node_id": str(r["nodeid"]),
                    "alias": r["alias"],
                    "name": r["name"],
                    "datatype": r["datatype"],
                }
            )
            # Pick the node whose nodeid matches the nodegroup_id as the
            # nodegroup's representative alias/name (the "top" node of the
            # nodegroup). Fall back to first encountered otherwise.
            if str(r["nodeid"]) == ng_id or bucket["alias"] is None:
                bucket["alias"] = r["alias"]
                bucket["name"] = r["name"]

        results = sorted(by_nodegroup.values(), key=lambda b: b["alias"] or "")
        for b in results:
            b["nodes"].sort(key=lambda n: n["alias"] or "")

        return JsonResponse({"nodegroups": results})
