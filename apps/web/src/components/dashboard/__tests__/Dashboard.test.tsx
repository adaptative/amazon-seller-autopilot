import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Dashboard } from '../Dashboard';

const mockDashboardData = {
  stats: {
    totalRevenue: 124560, revenueTrend: 12.5,
    ordersToday: 47, ordersTrend: 8.3,
    buyBoxWinRate: 87, buyBoxTrend: 4.2,
    acos: 24.8, acosTrend: -3.2,
  },
  agents: [
    { type: 'listing', status: 'active', lastAction: 'Optimized 3 titles', lastActionAt: '2m ago' },
    { type: 'pricing', status: 'active', lastAction: 'Repriced 5 products', lastActionAt: '5m ago' },
    { type: 'advertising', status: 'active', lastAction: 'Adjusted 12 bids', lastActionAt: '8m ago' },
    { type: 'inventory', status: 'idle', lastAction: 'All stock levels healthy', lastActionAt: '1h ago' },
    { type: 'analytics', status: 'idle', lastAction: 'Reports generated', lastActionAt: '3h ago' },
    { type: 'compliance', status: 'idle', lastAction: 'No issues found', lastActionAt: '6h ago' },
    { type: 'orchestrator', status: 'active', lastAction: 'Coordinating pricing+listing', lastActionAt: '1m ago' },
  ],
  pendingApprovals: [
    { id: 'act-1', agentType: 'pricing', description: 'Reduce B08XYZ price to $24.99', confidence: 0.87, createdAt: '2m ago' },
    { id: 'act-2', agentType: 'listing', description: 'Optimize B08ABC title', confidence: 0.92, createdAt: '15m ago' },
  ],
  recentActivity: [
    { id: 'ev-1', agentType: 'listing', action: 'Optimized title for', asin: 'B08XYZ', time: '10:42 AM' },
    { id: 'ev-2', agentType: 'pricing', action: 'Won Buy Box on', asin: 'B08ABC', time: '10:38 AM' },
  ],
  notificationCount: 3,
};

vi.mock('@/lib/api', () => ({
  dashboardApi: {
    getData: vi.fn(() => Promise.resolve(mockDashboardData)),
  },
}));

describe('Dashboard', () => {
  it('renders personalized greeting', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getByText(/good morning|good afternoon|good evening/i)).toBeInTheDocument();
      expect(screen.getByText(/Sarah/)).toBeInTheDocument();
    });
  });

  it('renders 4 stat cards with values', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getByText('$124,560')).toBeInTheDocument();
      expect(screen.getAllByText('47').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('87%').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('24.8%').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('stat values use Fredoka font', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      const matches = screen.getAllByText('$124,560');
      const hasFredoka = matches.some(el => el.className.match(/display|fredoka/i));
      expect(hasFredoka).toBe(true);
    });
  });

  it('renders all 7 agent statuses', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getAllByText(/Listing Agent/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Pricing Agent/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Advertising Agent/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Inventory Agent/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Analytics Agent/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Compliance Agent/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Orchestrator/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('active agents have pulsing dots', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      const listingDot = screen.getByTestId('agent-dot-listing');
      expect(listingDot.className).toMatch(/pulse|animate/);
    });
  });

  it('idle agents do NOT pulse', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      const inventoryDot = screen.getByTestId('agent-dot-inventory');
      expect(inventoryDot.className).not.toMatch(/pulse/);
    });
  });

  it('shows pending approvals count', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getByTestId('pending-count')).toHaveTextContent('2');
    });
  });

  it('renders approval cards with agent-colored borders', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getByText(/Reduce B08XYZ/)).toBeInTheDocument();
      expect(screen.getByText(/Optimize B08ABC/)).toBeInTheDocument();
    });
  });

  it('renders activity feed with ASINs in data badge format', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      const badge = screen.getByText('B08XYZ');
      expect(badge.className).toMatch(/border-dashed|primary-pop|font-bold/);
    });
  });

  it('shows live indicator on activity feed', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getByTestId('live-indicator')).toBeInTheDocument();
    });
  });

  it('has Cmd+K search bar', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search|⌘K/i)).toBeInTheDocument();
    });
  });

  it('notification bell shows unread count', async () => {
    render(<Dashboard userName="Sarah" />);
    await waitFor(() => {
      expect(screen.getByTestId('notification-badge')).toBeInTheDocument();
    });
  });
});
