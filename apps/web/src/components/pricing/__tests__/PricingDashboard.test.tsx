import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PricingDashboard } from '../PricingDashboard';

const mockStats = {
  buyBoxWinRate: 87, buyBoxTrend: 4.2,
  avgMargin: 24.8, marginTrend: -1.1,
  priceChangesToday: 12, changesTrend: 3,
  revenueImpact: 2340
};
const mockProducts = [
  { asin: 'B08ABC', title: 'Wireless Earbuds', ourPrice: 24.99, buyBoxPrice: 24.99, competitorCount: 7, weOwnBuyBox: true, lastChange: '2h ago', lastChangeDir: 'down' as const },
  { asin: 'B08DEF', title: 'Phone Case', ourPrice: 16.99, buyBoxPrice: 14.99, competitorCount: 12, weOwnBuyBox: false, lastChange: '5h ago', lastChangeDir: 'up' as const },
];

vi.mock('@/lib/api', () => ({
  pricingApi: {
    getStats: vi.fn(() => Promise.resolve(mockStats)),
    getProducts: vi.fn(() => Promise.resolve({ items: mockProducts, total: 89 })),
    getBuyBoxHistory: vi.fn(() => Promise.resolve([])),
    getCompetitorMap: vi.fn(() => Promise.resolve([])),
    reprice: vi.fn(() => Promise.resolve({ success: true })),
  }
}));

describe('PricingDashboard', () => {
  const user = userEvent.setup();

  it('renders 4 stat cards', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      expect(screen.getByText('87%')).toBeInTheDocument();
      expect(screen.getByText('24.8%')).toBeInTheDocument();
      expect(screen.getByText('12')).toBeInTheDocument();
      expect(screen.getByText(/\$2,340/)).toBeInTheDocument();
    });
  });

  it('stat card values use Fredoka font', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      expect(screen.getByText('87%').className).toMatch(/display|fredoka/i);
    });
  });

  it('shows green trend for positive values', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      const buyBoxTrend = screen.getByTestId('trend-buy-box');
      expect(buyBoxTrend.className).toMatch(/emerald|green/);
    });
  });

  it('shows amber/red trend for negative values', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      const marginTrend = screen.getByTestId('trend-margin');
      expect(marginTrend.className).toMatch(/amber|rose|yellow|red/);
    });
  });

  it('renders pricing agent badge with violet dot', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/pricing agent/i)).toBeInTheDocument();
    });
  });

  it('renders Buy Box chart container', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      expect(screen.getByTestId('buybox-chart')).toBeInTheDocument();
    });
  });

  it('renders competitor map chart container', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      expect(screen.getByTestId('competitor-chart')).toBeInTheDocument();
    });
  });

  it('renders price table with products', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      expect(screen.getByText('B08ABC')).toBeInTheDocument();
      expect(screen.getByText('B08DEF')).toBeInTheDocument();
    });
  });

  it('shows ASIN in data badge format', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      expect(screen.getByText('B08ABC').className).toMatch(/border-dashed|primary-pop/);
    });
  });

  it('shows green checkmark when we own Buy Box', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      const row = screen.getByText('B08ABC').closest('tr')!;
      const status = within(row).getByTestId('buybox-status');
      expect(status.className).toMatch(/emerald|green/);
    });
  });

  it('shows red X when we do not own Buy Box', async () => {
    render(<PricingDashboard />);
    await waitFor(() => {
      const row = screen.getByText('B08DEF').closest('tr')!;
      const status = within(row).getByTestId('buybox-status');
      expect(status.className).toMatch(/rose|red/);
    });
  });

  it('shows total count', async () => {
    render(<PricingDashboard />);
    await waitFor(() => expect(screen.getByText(/89/)).toBeInTheDocument());
  });

  it('Reprice button triggers API call', async () => {
    const { pricingApi } = await import('@/lib/api');
    render(<PricingDashboard />);
    await waitFor(() => screen.getByText('B08DEF'));
    const row = screen.getByText('B08DEF').closest('tr')!;
    await user.click(within(row).getByRole('button', { name: /reprice/i }));
    expect(pricingApi.reprice).toHaveBeenCalledWith('B08DEF');
  });
});
