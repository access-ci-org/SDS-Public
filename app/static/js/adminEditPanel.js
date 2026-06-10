/**
 * Lifecycle helpers for the admin edit panel that lives inside the
 * software details modal.
 *
 * The panel is HTMX-driven: Save and Revert re-render the entire
 * #admin-edit-panel element via outerHTML swap. The freshly rendered
 * HTML always marks Core Metadata as the active tab, which would
 * otherwise reset the user's position after every Save or Revert.
 *
 * attachTabPreservation wires up listeners on the persistent container
 * (which wraps #admin-edit-panel and survives the swap) to remember the
 * active tab before the swap and reactivate it after.
 *
 * Note: htmx:afterSwap fires on the original target element, which is
 * detached from the DOM during an outerHTML swap and therefore does
 * not bubble to the container. htmx:afterSettle fires on the NEW
 * element (still attached), so its bubbling reaches the container.
 */

const ACTIVE_TAB_DATASET_KEY = "activeTabTarget";
const TAB_SELECTOR = ".admin-edit-tabs .nav-link";

function findActiveTabTarget(root) {
    const active = root.querySelector(`${TAB_SELECTOR}.active`);
    return active ? active.getAttribute("data-bs-target") : null;
}

function activateTab(root, target) {
    const btn = root.querySelector(`${TAB_SELECTOR}[data-bs-target="${target}"]`);
    if (!btn || typeof window.bootstrap === "undefined") return;
    window.bootstrap.Tab.getOrCreateInstance(btn).show();
}

export function attachTabPreservation(container) {
    container.addEventListener("htmx:beforeSwap", () => {
        const target = findActiveTabTarget(container);
        if (target) {
            container.dataset[ACTIVE_TAB_DATASET_KEY] = target;
        }
    });

    container.addEventListener("htmx:afterSettle", () => {
        const target = container.dataset[ACTIVE_TAB_DATASET_KEY];
        if (target) {
            activateTab(container, target);
        }
    });
}
