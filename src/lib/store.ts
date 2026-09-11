'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useShallow } from 'zustand/react/shallow';

// Tracks auto-dismiss timer IDs so they can be cancelled on manual dismiss
const toastTimers = new Map<string, ReturnType<typeof setTimeout>>();

// ═══════════════════════════════════════════
// CIRUS — Zustand UI State Store
// ═══════════════════════════════════════════

interface ToastItem {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  description?: string;
}

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Active incident tab
  activeArtifactTab: string;
  setActiveArtifactTab: (tab: string) => void;

  // Selected workflow stage
  selectedStageId: string | null;
  setSelectedStageId: (id: string | null) => void;

  // Toasts
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;

  // Approval status per incident (local, not persisted to server yet)
  approvals: Record<string, 'approved' | 'rejected' | 'pending'>;
  setApproval: (incidentId: string, status: 'approved' | 'rejected' | 'pending') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Sidebar
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // Active artifact tab
      activeArtifactTab: 'rca',
      setActiveArtifactTab: (tab) => set({ activeArtifactTab: tab }),

      // Workflow stage
      selectedStageId: null,
      setSelectedStageId: (id) => set({ selectedStageId: id }),

      // Toasts
      toasts: [],
      addToast: (toast) => {
        const id = Math.random().toString(36).slice(2);
        set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));
        // Auto-remove after 5s; store timer ID so manual dismiss can cancel it
        const timer = setTimeout(() => {
          get().removeToast(id);
          toastTimers.delete(id);
        }, 5000);
        toastTimers.set(id, timer);
      },
      removeToast: (id) => {
        // Cancel pending auto-dismiss if user dismissed manually
        const timer = toastTimers.get(id);
        if (timer !== undefined) {
          clearTimeout(timer);
          toastTimers.delete(id);
        }
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
      },

      // Approvals
      approvals: {},
      setApproval: (incidentId, status) =>
        set((s) => ({
          approvals: { ...s.approvals, [incidentId]: status },
        })),
    }),
    {
      name: 'cirus-ui-store',
      // Only persist sidebar + approvals — toasts are ephemeral
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        approvals: state.approvals,
        activeArtifactTab: state.activeArtifactTab,
      }),
    },
  ),
);

// ─── Convenience selectors ────────────────────────────────────────────────────
export const useSidebar = () =>
  useUIStore(useShallow((s) => ({
    collapsed: s.sidebarCollapsed,
    toggle: s.toggleSidebar,
  })));

export const useToasts = () =>
  useUIStore(useShallow((s) => ({
    toasts: s.toasts,
    add: s.addToast,
    remove: s.removeToast,
  })));

export const useApproval = (incidentId: string) => {
  const status = useUIStore((s) => s.approvals[incidentId] ?? 'pending');
  const setApproval = useUIStore((s) => s.setApproval);
  return {
    status,
    set: (status: 'approved' | 'rejected' | 'pending') => setApproval(incidentId, status),
  };
};
