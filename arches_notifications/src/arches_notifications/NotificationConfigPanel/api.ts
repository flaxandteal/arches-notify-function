import arches from "arches";

import type {
    EmailTemplateOption,
    GroupOption,
    NodegroupOption,
} from "./types.ts";

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

export async function fetchEmailTemplates(): Promise<EmailTemplateOption[]> {
    const res = await fetch(arches.urls.notification_email_templates);
    if (!res.ok) throw new Error(`Failed to fetch email templates (${res.status})`);
    const data = await res.json();
    return data.templates ?? [];
}

function getCsrfToken(): string {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
}

export async function deleteNotificationType(typeId: string): Promise<void> {
    const res = await fetch(arches.urls.notification_type_delete(typeId), {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrfToken() },
        credentials: "same-origin",
    });
    if (!res.ok && res.status !== 404) {
        throw new Error(`Failed to delete notification type (${res.status})`);
    }
}
