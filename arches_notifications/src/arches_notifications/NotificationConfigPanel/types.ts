export interface ResourceNameConfig {
    require_prefix: string | null;
    strip_prefix: string | null;
    strip_suffix: string | null;
}

export const DEFAULT_EMAIL_TEMPLATE = "email/general_notification.htm";

export type FireOn = "any" | "created" | "updated" | "copied";

export type SavedBy = "anyone" | "user" | "system";

export type EmailRecipients = "members" | "members_and_extra" | "extra_only";

export interface NotificationRule {
    nodegroup_alias: string;
    // Optional: when set, fire only if THIS node's value changed.
    node_alias: string | null;
    // Missing on rules saved before these fields existed.
    fire_on?: FireOn;
    saved_by?: SavedBy;
    // UUID auto-generated when the rule is created. The function's
    // after_function_save hook upserts a NotificationType keyed by this id,
    // so each rule maps 1:1 to an opt-out entry in the user prefs UI.
    notiftype_id: string;
    // Becomes NotificationType.name — what the user sees in their email
    // preferences. Empty => derived from graph + nodegroup at save time.
    notification_name: string;
    // Django template path used to render the email body.
    emailtemplate: string;
    groups_to_notify: string[];
    // Missing on rules saved before this field existed.
    users_to_notify?: number[];
    message: string;
    email: boolean;
    // Missing on rules saved before these fields existed.
    email_recipients?: EmailRecipients;
    email_addresses?: string[];
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

export interface EmailTemplateOption {
    path: string;
    label: string;
}

export interface UserOption {
    id: number;
    username: string;
    email: string;
}

export interface GroupOption {
    id: number;
    name: string;
}

export function emptyRule(): NotificationRule {
    return {
        nodegroup_alias: "",
        node_alias: null,
        fire_on: "any",
        saved_by: "anyone",
        notiftype_id: crypto.randomUUID(),
        notification_name: "",
        emailtemplate: DEFAULT_EMAIL_TEMPLATE,
        groups_to_notify: [],
        users_to_notify: [],
        message: "",
        email: false,
        email_recipients: "members",
        email_addresses: [],
        button_text: "View resource",
        // Empty => backend links to the resource report page. Override with
        // a fixed path if every email should land on the same destination.
        link_path: "",
        resource_name: {
            require_prefix: null,
            strip_prefix: null,
            strip_suffix: null,
        },
    };
}
