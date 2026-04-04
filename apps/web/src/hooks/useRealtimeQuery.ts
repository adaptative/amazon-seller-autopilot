"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "./useWebSocket";

interface UseRealtimeQueryOptions {
  wsEventTypes?: string[];
  wsUrl?: string;
}

export function useRealtimeQuery<T>(
  queryKey: string | string[],
  fetcher: () => Promise<T>,
  options: UseRealtimeQueryOptions = {}
) {
  const { wsEventTypes = [], wsUrl = "ws://localhost:8000/ws" } = options;
  const queryClient = useQueryClient();

  const queryResult = useQuery({
    queryKey: Array.isArray(queryKey) ? queryKey : [queryKey],
    queryFn: fetcher,
  });

  const { lastMessage } = useWebSocket(wsUrl, {
    filterTypes: wsEventTypes.length > 0 ? wsEventTypes : undefined,
  });

  useEffect(() => {
    if (lastMessage && wsEventTypes.includes(lastMessage.type)) {
      queryClient.invalidateQueries({
        queryKey: Array.isArray(queryKey) ? queryKey : [queryKey],
      });
    }
  }, [lastMessage, queryKey, queryClient, wsEventTypes]);

  return queryResult;
}
