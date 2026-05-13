export interface ResourceNameConfig {
    require_prefix: string | null;
    strip_prefix: string | null;
    strip_suffix: string | null;
}

// Matches the well-known UUID set by migration 0001_notification_type and
// notification_config.DEFAULT_NOTIFICATION_TYPE_ID. Used as the dropdown's
// default selection; users can change it per rule.
export const DEFAULT_NOTIFICATION_TYPE_ID =
    "a85b3f1c-7d4e-4d5a-9b5e-2a3b4c5d6e7f";

export interface NotificationRule {
    nodegroup_alias: string;
    // Optional: when set, fire only if THIS node's value changed.
    node_alias: string | null;
    notiftype_id: string;
    groups_to_notify: string[];
    message: string;
    email: boolean;
    button_text: string;
    link_path: string;
    resource_name: ResourceNameConfig;
}

export interface NotificationPanelConfig {
    nodegroups: NotificationRule[];
}

export interface NodeOption {
    node_id: string;
    alias: string;
    name: string;
    datatype: string;
}

export interface NodegroupOption {
    nodegroup_id: string;
    alias: string;
    name: string;
    nodes: NodeOption[];
}

export interface NotificationTypeOption {
    typeid: string;
    name: string;
    emailnotify: boolean;
    webnotify: boolean;
}

export interface GroupOption {
    id: number;
    name: string;
}

export function emptyRule(): NotificationRule {
    return {
        nodegroup_alias: "",
        node_alias: null,
        notiftype_id: DEFAULT_NOTIFICATION_TYPE_ID,
        groups_to_notify: [],
        message: "",
        email: false,
        button_text: "Open Arches",
        link_path: "/index.htm",
        resource_name: {
            require_prefix: null,
            strip_prefix: null,
            strip_suffix: null,
        },
    };
}
