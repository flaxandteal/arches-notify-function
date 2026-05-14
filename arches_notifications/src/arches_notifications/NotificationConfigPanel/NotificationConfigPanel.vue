<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Message from "primevue/message";

import NotificationRuleEntry from "./NotificationRuleEntry.vue";
import {
    deleteNotificationType,
    fetchEmailTemplates,
    fetchGroups,
    fetchNodegroups,
} from "./api.ts";
import {
    emptyRule,
    type EmailTemplateOption,
    type GroupOption,
    type NodegroupOption,
    type NotificationPanelConfig,
    type NotificationRule,
} from "./types.ts";

const props = defineProps<{
    graphId: string;
    modelValue: NotificationPanelConfig;
    // Pull-model bridge: KO shim hands us a function, Vue calls it once on
    // Save Edits to flush the latest snapshot. No per-keystroke emits → no
    // koMapping.fromJS churn while typing.
    registerFlush?: (fn: () => NotificationPanelConfig) => void;
    // Called once on the first user edit so the KO shim can flip `dirty` and
    // make the function manager's Save Edits button appear (it's gated on
    // dirty). Subsequent edits do nothing here — full state is pulled at save.
    markDirty?: () => void;
}>();

// Local reactive copy — Vue owns it. The KO shim pulls a snapshot via
// registerFlush() when the function manager's Save Edits button is clicked.
// Defensive: fold any incoming rule onto a fresh emptyRule() so missing
// fields (from older saved configs) get sensible defaults.
const config = reactive<NotificationPanelConfig>({
    nodegroups: (props.modelValue?.nodegroups ?? []).map((r) => ({
        ...emptyRule(),
        ...r,
        resource_name: { ...emptyRule().resource_name, ...(r.resource_name ?? {}) },
    })),
});

// Hand the KO shim a snapshot fn it can call on Save Edits.
props.registerFlush?.(() => JSON.parse(JSON.stringify(config)));

// Fire markDirty once on the first user edit, then stop watching. Cheap.
const stopDirtyWatch = watch(
    config,
    () => {
        props.markDirty?.();
        stopDirtyWatch();
    },
    { deep: true, flush: "post" },
);

const nodegroups = ref<NodegroupOption[]>([]);
const emailTemplates = ref<EmailTemplateOption[]>([]);
const groups = ref<GroupOption[]>([]);
const loadError = ref<string | null>(null);
const loading = ref(true);

onMounted(async () => {
    try {
        const [ng, templates, grps] = await Promise.all([
            fetchNodegroups(props.graphId),
            fetchEmailTemplates(),
            fetchGroups(),
        ]);
        nodegroups.value = ng;
        emailTemplates.value = templates;
        groups.value = grps;
    } catch (e) {
        loadError.value =
            "Failed to load configuration options. Check the console for details.";
        console.error(e);
    } finally {
        loading.value = false;
    }
});

function addRule() {
    config.nodegroups.push(emptyRule());
}

function removeRule(index: number) {
    const removed = config.nodegroups[index];
    config.nodegroups.splice(index, 1);
    props.markDirty?.();
    if (removed?.notiftype_id) {
        // Fire-and-forget: a stale type left behind on a network failure is
        // harmless (just an orphan opt-out entry), so don't block the UI.
        deleteNotificationType(removed.notiftype_id).catch((e) =>
            console.warn("Failed to delete notification type:", e),
        );
    }
}

function updateRule(index: number, rule: NotificationRule) {
    Object.assign(config.nodegroups[index], rule);
}
</script>

<template>
    <div
        class="notification-config-panel"
        @click.stop
        @change.stop
        @input.stop
    >
        <div class="panel-header">
            <h3 class="panel-title">Notification Rules</h3>
            <Button
                icon="pi pi-plus"
                label="Add rule"
                size="small"
                outlined
                :disabled="loading"
                @click="addRule"
            />
        </div>

        <Message
            v-if="loadError"
            severity="error"
        >
            {{ loadError }}
        </Message>

        <div
            v-if="loading"
            class="loading-placeholder"
        >
            <i class="pi pi-spin pi-spinner" />
            Loading options…
        </div>

        <template v-else>
            <p
                v-if="config.nodegroups.length === 0"
                class="empty-state"
            >
                No rules configured. Add one to send notifications when a tile is saved.
            </p>

            <div class="rule-list">
                <NotificationRuleEntry
                    v-for="(rule, i) in config.nodegroups"
                    :key="i"
                    :rule="rule"
                    :index="i"
                    :nodegroups="nodegroups"
                    :email-templates="emailTemplates"
                    :groups="groups"
                    @update:rule="updateRule(i, $event)"
                    @remove="removeRule(i)"
                />
            </div>
        </template>
    </div>
</template>

<style scoped>
.notification-config-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0;
    /* Reset the Arches function-manager container font scaling.
       The KO host container uses small typography; Vue/PrimeVue
       defaults to ~14px and the cascade scales it down further. */
    font-size: 14px;
    line-height: 1.5;
    color: var(--p-text-color, #111827);
}

.notification-config-panel :deep(input),
.notification-config-panel :deep(textarea),
.notification-config-panel :deep(.p-select-label),
.notification-config-panel :deep(.p-multiselect-label),
.notification-config-panel :deep(button) {
    font-size: 14px;
}

.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.panel-title {
    margin: 0;
    font-weight: 600;
}

.rule-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 70vh;
    overflow-y: auto;
    /* Keep scrollbar off the right edge of rule cards */
    padding-right: 0.25rem;
}

.empty-state {
    color: var(--p-text-muted-color, #6b7280);
    font-size: 0.875rem;
    text-align: center;
    padding: 1.5rem 0;
    margin: 0;
}

.loading-placeholder {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--p-text-muted-color, #6b7280);
    font-size: 0.875rem;
    padding: 1rem 0;
}
</style>
