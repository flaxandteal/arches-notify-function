<script setup lang="ts">
import { ref, computed } from "vue";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import MultiSelect from "primevue/multiselect";
import Panel from "primevue/panel";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";

import type {
    GroupOption,
    NodegroupOption,
    NotificationTrigger,
    NotificationTypeOption,
} from "./types";

const props = defineProps<{
    trigger: NotificationTrigger;
    index: number;
    nodegroups: NodegroupOption[];
    notificationTypes: NotificationTypeOption[];
    groups: GroupOption[];
}>();

const emit = defineEmits<{
    (e: "update:trigger", value: NotificationTrigger): void;
    (e: "remove"): void;
}>();

const resourceNameExpanded = ref(false);

const selectedNodegroup = computed({
    get: () =>
        props.nodegroups.find((n) => n.alias === props.trigger.nodegroup_alias) ?? null,
    set: (val: NodegroupOption | null) =>
        update("nodegroup_alias", val?.alias ?? ""),
});

const selectedType = computed({
    get: () =>
        props.notificationTypes.find((t) => t.typeid === props.trigger.notiftype_id) ?? null,
    set: (val: NotificationTypeOption | null) =>
        update("notiftype_id", val?.typeid ?? ""),
});

const selectedGroups = computed({
    get: () =>
        props.groups.filter((g) => props.trigger.groups_to_notify.includes(g.name)),
    set: (val: GroupOption[]) =>
        update("groups_to_notify", val.map((g) => g.name)),
});

function update<K extends keyof NotificationTrigger>(
    key: K,
    value: NotificationTrigger[K],
) {
    emit("update:trigger", { ...props.trigger, [key]: value });
}

function updateResourceName(
    key: keyof NotificationTrigger["resource_name"],
    value: string,
) {
    emit("update:trigger", {
        ...props.trigger,
        resource_name: {
            ...props.trigger.resource_name,
            [key]: value || null,
        },
    });
}

const triggerLabel = computed(() => {
    if (props.trigger.nodegroup_alias) {
        return props.trigger.nodegroup_alias;
    }
    return `Trigger ${props.index + 1}`;
});
</script>

<template>
    <Panel
        class="trigger-entry"
        toggleable
    >
        <template #header>
            <span class="trigger-label">{{ triggerLabel }}</span>
        </template>
        <template #icons>
            <Button
                icon="pi pi-trash"
                text
                severity="danger"
                size="small"
                aria-label="Remove trigger"
                @click.stop="emit('remove')"
            />
        </template>

        <div class="trigger-fields">
            <div class="field">
                <label>Nodegroup</label>
                <Select
                    v-model="selectedNodegroup"
                    :options="nodegroups"
                    option-label="alias"
                    placeholder="Select nodegroup…"
                    class="w-full"
                    filter
                />
            </div>

            <div class="field">
                <label>Notification type</label>
                <Select
                    v-model="selectedType"
                    :options="notificationTypes"
                    option-label="name"
                    placeholder="Select type…"
                    class="w-full"
                />
            </div>

            <div class="field">
                <label>Groups to notify</label>
                <MultiSelect
                    v-model="selectedGroups"
                    :options="groups"
                    option-label="name"
                    placeholder="Select groups…"
                    class="w-full"
                    display="chip"
                    filter
                />
            </div>

            <div class="field">
                <label>Message</label>
                <Textarea
                    :model-value="trigger.message"
                    rows="2"
                    class="w-full"
                    placeholder="Use {name} for the resource display name"
                    @update:model-value="update('message', $event)"
                />
            </div>

            <div class="field field--inline">
                <label>Send email</label>
                <ToggleSwitch
                    :model-value="trigger.email"
                    @update:model-value="update('email', $event)"
                />
            </div>

            <template v-if="trigger.email">
                <div class="field email-field">
                    <label>Button text</label>
                    <InputText
                        :model-value="trigger.button_text"
                        class="w-full"
                        @update:model-value="update('button_text', $event)"
                    />
                </div>
                <div class="field email-field">
                    <label>Link path</label>
                    <InputText
                        :model-value="trigger.link_path"
                        class="w-full"
                        placeholder="/index.htm"
                        @update:model-value="update('link_path', $event)"
                    />
                </div>
            </template>

            <!-- Resource name filtering — advanced, hidden by default -->
            <div class="field field--accordion">
                <button
                    class="accordion-toggle"
                    type="button"
                    @click="resourceNameExpanded = !resourceNameExpanded"
                >
                    <i
                        :class="resourceNameExpanded ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
                    />
                    Resource name
                </button>

                <template v-if="resourceNameExpanded">
                    <div class="accordion-body">
                        <div class="field">
                            <label>Require prefix (skip if name doesn't start with this)</label>
                            <InputText
                                :model-value="trigger.resource_name.require_prefix ?? ''"
                                class="w-full"
                                placeholder="e.g. HM-"
                                @update:model-value="updateResourceName('require_prefix', $event)"
                            />
                        </div>
                        <div class="field-row">
                            <div class="field">
                                <label>Strip prefix</label>
                                <InputText
                                    :model-value="trigger.resource_name.strip_prefix ?? ''"
                                    class="w-full"
                                    @update:model-value="
                                        updateResourceName('strip_prefix', $event)
                                    "
                                />
                            </div>
                            <div class="field">
                                <label>Strip suffix</label>
                                <InputText
                                    :model-value="trigger.resource_name.strip_suffix ?? ''"
                                    class="w-full"
                                    @update:model-value="
                                        updateResourceName('strip_suffix', $event)
                                    "
                                />
                            </div>
                        </div>
                    </div>
                </template>
            </div>
        </div>
    </Panel>
</template>

<style scoped>
.trigger-label {
    font-weight: 600;
    font-size: 0.9rem;
}

.trigger-fields {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.field label {
    font-size: 0.8rem;
    color: var(--p-text-muted-color, #6b7280);
    font-weight: 500;
}

.field--inline {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
}

.email-field {
    padding-left: 1rem;
    border-left: 2px solid var(--p-content-border-color, #e5e7eb);
}

.field--accordion {
    border-top: 1px solid var(--p-content-border-color, #e5e7eb);
    padding-top: 0.5rem;
}

.accordion-toggle {
    background: none;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--p-text-muted-color, #6b7280);
    padding: 0;
}

.accordion-toggle:hover {
    color: var(--p-text-color, #111827);
}

.accordion-body {
    margin-top: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.field-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
}

.w-full {
    width: 100%;
}
</style>
