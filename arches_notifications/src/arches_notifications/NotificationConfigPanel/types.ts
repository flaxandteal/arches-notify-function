export interface ResourceNameConfig {
    require_prefix: string | null;
    strip_prefix: string | null;
    strip_suffix: string | null;
}

export interface NotificationRule {
    nodegroup_alias: string;
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

export interface NodegroupOption {
    nodegroup_id: string;
    alias: string;
    name: string;
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
        notiftype_id: "",
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
