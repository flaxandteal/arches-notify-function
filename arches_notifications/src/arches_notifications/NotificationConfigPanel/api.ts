import arches from "arches";

import type {
    GroupOption,
    NodegroupOption,
    NotificationTypeOption,
} from "./types";

export async function fetchNotificationTypes(): Promise<NotificationTypeOption[]> {
    const res = await fetch(arches.urls.get_notification_types);
    if (!res.ok) throw new Error(`Failed to fetch notification types (${res.status})`);
    const data = await res.json();
    return data.types ?? [];
}

export async function fetchGroups(): Promise<GroupOption[]> {
    const res = await fetch(arches.urls.notification_groups);
    if (!res.ok) throw new Error(`Failed to fetch groups (${res.status})`);
    const data = await res.json();
    return data.groups ?? [];
}

export async function fetchNodegroups(graphId: string): Promise<NodegroupOption[]> {
    const res = await fetch(arches.urls.notification_nodegroups(graphId));
    if (!res.ok) throw new Error(`Failed to fetch nodegroups (${res.status})`);
    const data = await res.json();
    return data.nodegroups ?? [];
}
