import ko from "knockout";
import koMapping from "knockout-mapping";

import FunctionViewModel from "viewmodels/function-view-model";
import createVueApplication from "utils/create-vue-application";

import NotificationConfigPanel from "@/arches_notifications/NotificationConfigPanel/NotificationConfigPanel.vue";
import notifyTemplate from "templates/views/components/functions/notify.htm";

/*
 * KO shim for the NotifyFunction config panel.
 *
 * The Arches function manager hands us `params.config` — a ko-mapping
 * observable wrapping the FunctionXGraph.config JSON. We:
 *
 *   1. Snapshot it to plain JS as the Vue panel's initial modelValue.
 *   2. Mount the Vue panel via createVueApplication into a div whose id is
 *      unique per instance (so multiple function panels can coexist).
 *   3. Listen for `update:modelValue` from Vue and write the updated rule
 *      list back into the KO observable so the function manager picks it up
 *      on save.
 *
 * triggering_nodegroups is forced to [] so Arches' Tile dispatcher fires
 * post_save for every nodegroup on the graph; per-nodegroup routing then
 * happens inside NotifyFunction._configs_for_tile against the rules list.
 */
export default ko.components.register("views/components/functions/notify", {
    viewModel: function (params) {
        FunctionViewModel.apply(this, arguments);

        this.mountId = "notify-config-mount-" + crypto.randomUUID();

        const ensureShape = (snapshot) => ({
            ...snapshot,
            triggering_nodegroups: [],
            nodegroups: Array.isArray(snapshot && snapshot.nodegroups)
                ? snapshot.nodegroups
                : [],
        });

        const initial = ensureShape(koMapping.toJS(this.config));

        // Pull model: Vue keeps local state and hands us a snapshot fn at
        // mount. We call it only when the function manager's Save Edits
        // button is clicked (capture phase, before KO's click handler reads
        // this.config). This avoids per-keystroke koMapping.fromJS, which
        // was the source of typing lag in the message textarea.
        let getSnapshot = null;
        const registerFlush = (fn) => { getSnapshot = fn; };

        // Called once on the user's first Vue-side edit. Reconcile a single
        // time so KO's `dirty` computed flips true and the Save Edits button
        // appears. Subsequent calls are no-ops; the real flush happens on
        // save click below.
        let dirtied = false;
        const markDirty = () => {
            if (dirtied || !getSnapshot) return;
            dirtied = true;
            const merged = ensureShape({
                ...koMapping.toJS(this.config),
                ...getSnapshot(),
            });
            koMapping.fromJS(merged, this.config);
        };

        const flush = () => {
            if (!getSnapshot) return;
            const merged = ensureShape({
                ...koMapping.toJS(this.config),
                ...getSnapshot(),
            });
            koMapping.fromJS(merged, this.config);
        };

        const onCaptureClick = (e) => {
            const btn = e.target.closest('button[data-bind*="click: save"]');
            if (btn) flush();
        };
        document.addEventListener("click", onCaptureClick, true);

        const mount = () => {
            const target = document.getElementById(this.mountId);
            if (!target) {
                window.setTimeout(mount, 50);
                return;
            }
            createVueApplication(NotificationConfigPanel, undefined, {
                graphId: this.graphid,
                modelValue: initial,
                registerFlush,
                markDirty,
            }).then((app) => {
                app.mount("#" + this.mountId);
            });
        };

        window.setTimeout(mount, 0);
    },
    template: notifyTemplate,
});
