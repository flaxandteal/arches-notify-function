<script setup lang="ts">
import { onMounted, ref } from "vue";

import Button from "primevue/button";
import Message from "primevue/message";

import NotificationRuleEntry from "./NotificationRuleEntry.vue";
import { fetchGroups, fetchNodegroups, fetchNotificationTypes } from "./api";
import {
    emptyRule,
    type GroupOption,
    type NodegroupOption,
    type NotificationPanelConfig,
    type NotificationRule,
    type NotificationTypeOption,
} from "./types";

const props = defineProps<{
    graphId: string;
    modelValue: NotificationPanelConfig;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: NotificationPanelConfig): void;
}>();

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
        loadError.value = "Failed to load configuration options. Check the console for details.";
        console.error(e);
    } finally {
        loading.value = false;
    }
});

function addRule() {
    emit("update:modelValue", {
        nodegroups: [...props.modelValue.nodegroups, emptyRule()],
    });
}

function removeRule(index: number) {
    const updated = props.modelValue.nodegroups.filter((_, i) => i !== index);
    emit("update:modelValue", { nodegroups: updated });
}

function updateRule(index: number, rule: NotificationRule) {
    const updated = props.modelValue.nodegroups.map((r, i) =>
        i === index ? rule : r,
    );
    emit("update:modelValue", { nodegroups: updated });
}
</script>

<template>
    <div class="notification-config-panel">
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
                v-if="modelValue.nodegroups.length === 0"
                class="empty-state"
            >
                No rules configured. Add one to send notifications when a tile is saved.
            </p>

            <div class="rule-list">
                <NotificationRuleEntry
                    v-for="(rule, i) in modelValue.nodegroups"
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
