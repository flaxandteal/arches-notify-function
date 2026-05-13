<script setup lang="ts">
import { onMounted, reactive, watch, ref } from "vue";

import Button from "primevue/button";
import Message from "primevue/message";

import NotificationRuleEntry from "./NotificationRuleEntry.vue";
import { fetchGroups, fetchNodegroups, fetchNotificationTypes } from "./api.ts";
import {
    emptyRule,
    type GroupOption,
    type NodegroupOption,
    type NotificationPanelConfig,
    type NotificationRule,
    type NotificationTypeOption,
} from "./types.ts";

const props = defineProps<{
    graphId: string;
    modelValue: NotificationPanelConfig;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: NotificationPanelConfig): void;
}>();

// Local reactive copy — Vue owns it. We propagate to the parent (KO shim)
// debounced, so typing in a textarea doesn't trigger a koMapping.fromJS
// rebuild on every keystroke.
// Defensive: fold any incoming rule onto a fresh emptyRule() so missing
// fields (from older saved configs) get sensible defaults. Otherwise an
// undefined `email` would propagate into the Checkbox v-model and the
// toggle silently emits undefined back.
const config = reactive<NotificationPanelConfig>({
    nodegroups: (props.modelValue?.nodegroups ?? []).map((r) => ({
        ...emptyRule(),
        ...r,
        resource_name: { ...emptyRule().resource_name, ...(r.resource_name ?? {}) },
    })),
});

let emitTimer: ReturnType<typeof setTimeout> | null = null;
watch(
    config,
    (val) => {
        if (emitTimer) clearTimeout(emitTimer);
        emitTimer = setTimeout(() => {
            emit("update:modelValue", JSON.parse(JSON.stringify(val)));
        }, 200);
    },
    { deep: true },
);

const nodegroups = ref<NodegroupOption[]>([]);
const notificationTypes = ref<NotificationTypeOption[]>([]);
const groups = ref<GroupOption[]>([]);
const loadError = ref<string | null>(null);
const loading = ref(true);

onMounted(async () => {
    try {
        const [ng, types, grps] = await Promise.all([
            fetchNodegroups(props.graphId),
            fetchNotificationTypes(),
            fetchGroups(),
        ]);
        nodegroups.value = ng;
        notificationTypes.value = types;
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
    config.nodegroups.splice(index, 1);
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
                    :notification-types="notificationTypes"
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
    font-size: 1rem;
    font-weight: 600;
}

.rule-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
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
