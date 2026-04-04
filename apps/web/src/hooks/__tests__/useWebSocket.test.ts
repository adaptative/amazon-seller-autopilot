import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useWebSocket } from "../useWebSocket";

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: any) => void) | null = null;
  readyState = 0;
  url: string;
  close = vi.fn();
  send = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  simulateOpen() {
    this.readyState = 1;
    this.onopen?.();
  }
  simulateMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
  simulateClose() {
    this.readyState = 3;
    this.onclose?.();
  }
  simulateError() {
    this.onerror?.({ message: "Connection failed" });
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal("WebSocket", MockWebSocket);
});
afterEach(() => vi.unstubAllGlobals());

describe("useWebSocket", () => {
  it("connects to the provided URL", () => {
    renderHook(() => useWebSocket("ws://localhost:8000/ws"));
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toBe("ws://localhost:8000/ws");
  });

  it("reports connected status after open", () => {
    const { result } = renderHook(() => useWebSocket("ws://localhost:8000/ws"));
    expect(result.current.status).toBe("connecting");
    act(() => MockWebSocket.instances[0].simulateOpen());
    expect(result.current.status).toBe("connected");
  });

  it("receives and parses JSON messages", () => {
    const { result } = renderHook(() => useWebSocket("ws://localhost:8000/ws"));
    act(() => MockWebSocket.instances[0].simulateOpen());
    act(() =>
      MockWebSocket.instances[0].simulateMessage({
        type: "agent_update",
        data: { agent: "pricing", status: "active" },
      })
    );
    expect(result.current.lastMessage).toEqual({
      type: "agent_update",
      data: { agent: "pricing", status: "active" },
    });
  });

  it("maintains message history", () => {
    const { result } = renderHook(() => useWebSocket("ws://localhost:8000/ws"));
    act(() => MockWebSocket.instances[0].simulateOpen());
    act(() => MockWebSocket.instances[0].simulateMessage({ type: "msg1" }));
    act(() => MockWebSocket.instances[0].simulateMessage({ type: "msg2" }));
    act(() => MockWebSocket.instances[0].simulateMessage({ type: "msg3" }));
    expect(result.current.messages).toHaveLength(3);
  });

  it("provides sendMessage function", () => {
    const { result } = renderHook(() => useWebSocket("ws://localhost:8000/ws"));
    act(() => MockWebSocket.instances[0].simulateOpen());
    act(() => result.current.sendMessage({ type: "ping" }));
    expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ type: "ping" })
    );
  });

  it("attempts reconnect on close with exponential backoff", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      useWebSocket("ws://localhost:8000/ws", { reconnect: true })
    );
    act(() => MockWebSocket.instances[0].simulateOpen());
    act(() => MockWebSocket.instances[0].simulateClose());
    expect(result.current.status).toBe("reconnecting");

    act(() => {
      vi.advanceTimersByTime(1100);
    });
    expect(MockWebSocket.instances).toHaveLength(2);
    vi.useRealTimers();
  });

  it("stops reconnecting after max retries", () => {
    vi.useFakeTimers();
    renderHook(() =>
      useWebSocket("ws://localhost:8000/ws", {
        reconnect: true,
        maxRetries: 3,
      })
    );

    for (let i = 0; i < 4; i++) {
      act(() =>
        MockWebSocket.instances[
          MockWebSocket.instances.length - 1
        ].simulateClose()
      );
      act(() => {
        vi.advanceTimersByTime(30000);
      });
    }
    expect(MockWebSocket.instances.length).toBeLessThanOrEqual(5);
    vi.useRealTimers();
  });

  it("closes connection on unmount", () => {
    const { unmount } = renderHook(() =>
      useWebSocket("ws://localhost:8000/ws")
    );
    const ws = MockWebSocket.instances[0];
    unmount();
    expect(ws.close).toHaveBeenCalled();
  });

  it("filters messages by type when subscribed", () => {
    const { result } = renderHook(() =>
      useWebSocket("ws://localhost:8000/ws", {
        filterTypes: ["agent_update"],
      })
    );
    act(() => MockWebSocket.instances[0].simulateOpen());
    act(() =>
      MockWebSocket.instances[0].simulateMessage({
        type: "agent_update",
        data: {},
      })
    );
    act(() =>
      MockWebSocket.instances[0].simulateMessage({
        type: "notification",
        data: {},
      })
    );
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].type).toBe("agent_update");
  });
});
