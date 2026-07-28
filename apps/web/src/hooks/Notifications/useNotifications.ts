"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

export interface AppNotification {
  id: string;
  title: string;
  body: string;
  unread: boolean;
  // In-app destination for the notification (e.g. `/intake/applications/:id`).
  href: string | null;
  created_at: string;
}

const fetchNotifications = (key: string) => getApiClient().get<AppNotification[]>(key);

// Top-bar notification feed. Backend contract (to be built):
//   GET  /notifications                 -> AppNotification[] (newest first)
//   POST /notifications/{id}/read       -> mark one read
//   POST /notifications/read-all        -> mark all read
// Until that ships the feed simply resolves empty (SWR shows the caught-up
// state); nothing is fabricated client-side.
export function useNotifications() {
  const { data, error, isLoading, mutate } = useSWR<AppNotification[]>(
    "/notifications",
    fetchNotifications,
    { revalidateOnFocus: true, shouldRetryOnError: false },
  );

  const notifications = data ?? [];
  const unreadCount = notifications.filter((n) => n.unread).length;

  async function markRead(id: string) {
    // Optimistic: flip locally, then persist.
    await mutate(
      async () => {
        await getApiClient().post(`/notifications/${id}/read`);
        return notifications.map((n) => (n.id === id ? { ...n, unread: false } : n));
      },
      {
        optimisticData: notifications.map((n) => (n.id === id ? { ...n, unread: false } : n)),
        rollbackOnError: true,
        revalidate: false,
      },
    );
  }

  async function markAllRead() {
    await mutate(
      async () => {
        await getApiClient().post("/notifications/read-all");
        return notifications.map((n) => ({ ...n, unread: false }));
      },
      {
        optimisticData: notifications.map((n) => ({ ...n, unread: false })),
        rollbackOnError: true,
        revalidate: false,
      },
    );
  }

  return { notifications, unreadCount, error, isLoading, markRead, markAllRead, refresh: mutate };
}
