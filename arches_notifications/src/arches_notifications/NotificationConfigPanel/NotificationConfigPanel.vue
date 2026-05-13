<script setup lang="ts">
import { onMounted, ref } from "vue";

import Button from "primevue/button";
import Message from "primevue/message";

import NotificationTriggerEntry from "./NotificationTriggerEntry.vue";
import {
    emptyTrigger,
    type GroupOption,
    type NodegroupOption,
    type NotificationPanelConfig,
    type NotificationTrigger,
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
        await Promise.all([fetchNodegroups(), fetchNotificationTypes(), fetchGroups()]);
    } catch (e) {
        loadError.value = "Failed to load configuration options. Check the console for details.";
        console.error(e);
    } finally {
        loading.value = false;
    }
});

async function fetchNodegroups() {
    const res = await fetch(`/api/notifications/nodegroups/${props.graphId}`);
    const data = await res.json();
    nodegroups.value = data.nodegroups ?? [];
}

async function fetchNotificationTypes() {
    const res = await fetch("/api/notifications/types");
    const data = await res.json();
    notificationTypes.value = data.notification_types ?? [];
}

async function fetchGroups() {
    const res = await fetch("/api/notifications/groups");
    const data = await res.json();
    groups.value = data.groups ?? [];
}

function addTrigger() {
    emit("update:modelValue", {
        nodegroups: [...props.modelValue.nodegroups, emptyTrigger()],
    });
}

function removeTrigger(index: number) {
    const updated = props.modelValue.nodegroups.filter((_, i) => i !== index);
    emit("update:modelValue", { nodegroups: updated });
}

function updateTrigger(index: number, trigger: NotificationTrigger) {
    const updated = props.modelValue.nodegroups.map((t, i) =>
        i === index ? trigger : t,
    );
    emit("update:modelValue", { nodegroups: updated });
}
</script>

<template>
    <div class="notification-config-panel">
        <div class="panel-header">
            <h3 class="panel-title">Notification Triggers</h3>
            <Button
                icon="pi pi-plus"
                label="Add trigger"
                size="small"
                outlined
                :disabled="loading"
                @click="addTrigger"
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
                No triggers configured. Add one to send notifications when a tile is saved.
            </p>

            <div class="trigger-list">
                <NotificationTriggerEntry
                    v-for="(trigger, i) in modelValue.nodegroups"
                    :key="i"
                    :trigger="trigger"
                    :index="i"
                    :nodegroups="nodegroups"
                    :notification-types="notificationTypes"
                    :groups="groups"
                    @update:trigger="updateTrigger(i, $event)"
                    @remove="removeTrigger(i)"
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

.trigger-list {
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
