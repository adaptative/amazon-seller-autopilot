import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CatalogView } from '../CatalogView';

const mockListings = [
  { asin: 'B08ABC', title: 'Wireless Earbuds Pro', price: 29.99, bsr: 1250, healthScore: 82, status: 'active' as const, imageUrl: '/img/earbuds.jpg' },
  { asin: 'B08DEF', title: 'Phone Case Ultra', price: 14.99, bsr: 3400, healthScore: 45, status: 'active' as const, imageUrl: '/img/case.jpg' },
  { asin: 'B08GHI', title: 'USB-C Cable 6ft', price: 9.99, bsr: 890, healthScore: 91, status: 'inactive' as const, imageUrl: '/img/cable.jpg' },
];

vi.mock('@/lib/api', () => ({
  listingsApi: {
    list: vi.fn(() => Promise.resolve({ items: mockListings, total: 247 })),
    optimize: vi.fn(() => Promise.resolve({ success: true })),
  }
}));

describe('CatalogView', () => {
  const user = userEvent.setup();

  it('renders data table with all listings', async () => {
    render(<CatalogView />);
    await waitFor(() => expect(screen.getAllByRole('row')).toHaveLength(4)); // header + 3
  });

  it('shows ASINs in data badge style', async () => {
    render(<CatalogView />);
    await waitFor(() => {
      const badge = screen.getByText('B08ABC');
      expect(badge.className).toMatch(/border-dashed|primary-pop|font-bold/);
    });
  });

  it('shows health score with colored progress bar', async () => {
    render(<CatalogView />);
    await waitFor(() => {
      expect(screen.getByTestId('health-bar-B08ABC')).toBeInTheDocument();
      expect(screen.getByText('82')).toBeInTheDocument();
    });
  });

  it('health bar is green for score >= 70', async () => {
    render(<CatalogView />);
    await waitFor(() => {
      expect(screen.getByTestId('health-bar-B08ABC').className).toMatch(/emerald|green/);
    });
  });

  it('health bar is amber for score 40-69', async () => {
    render(<CatalogView />);
    await waitFor(() => {
      expect(screen.getByTestId('health-bar-B08DEF').className).toMatch(/amber|yellow/);
    });
  });

  it('filters by search query', async () => {
    render(<CatalogView />);
    await waitFor(() => screen.getByPlaceholderText(/search/i));
    await user.type(screen.getByPlaceholderText(/search/i), 'Earbuds');
    await waitFor(() => {
      expect(screen.getByText('Wireless Earbuds Pro')).toBeInTheDocument();
      expect(screen.queryByText('Phone Case Ultra')).not.toBeInTheDocument();
    });
  });

  it('shows total count in footer', async () => {
    render(<CatalogView />);
    await waitFor(() => expect(screen.getByText(/247/)).toBeInTheDocument());
  });

  it('navigates to editor when Optimize clicked', async () => {
    const onNavigate = vi.fn();
    render(<CatalogView onOptimize={onNavigate} />);
    await waitFor(() => screen.getByText('Wireless Earbuds Pro'));
    const row = screen.getByText('B08ABC').closest('tr')!;
    await user.click(within(row).getByRole('button', { name: /optimize/i }));
    expect(onNavigate).toHaveBeenCalledWith('B08ABC');
  });

  it('shows agent status badge', async () => {
    render(<CatalogView />);
    await waitFor(() => {
      expect(screen.getByText(/listing agent/i)).toBeInTheDocument();
    });
  });
});
