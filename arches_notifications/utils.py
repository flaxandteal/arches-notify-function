from functools import lru_cache


@lru_cache
def node_id(alias, graph_slug):
    """Resolve a node alias to its UUID string for use as a tile.data key.

    Result is cached per alias+graph_slug pair, so the DB is only hit once
    per process lifetime.

    Example:
        decision = self.tile.data[node_id('grade_d_decision', 'excavation-licence')]
    """
    from arches.app.models.models import Node
    return str(Node.objects.values_list('nodeid', flat=True).get(alias=alias, graph__slug=graph_slug))
