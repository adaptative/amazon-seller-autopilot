import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ListingEditor } from '../ListingEditor';

const mockCurrent = {
  asin: 'B08N49K23V',
  title: 'Wireless Bluetooth Earbuds with Noise Cancellation',
  bullets: [
    'Active Noise Cancellation — block out background noise',
    '30-Hour Battery Life with charging case',
    'Bluetooth 5.3 — stable, low-latency connection',
    'IPX5 Waterproof — sweat and splash resistant',
    'Touch Controls — tap to play, pause, skip'
  ],
  description: 'Experience premium sound quality...',
  searchTerms: 'wireless earbuds bluetooth noise cancelling',
  price: 49.99,
  bsr: 1250,
  healthScore: 78,
  status: 'active',
  imageUrl: '/img/earbuds.jpg',
  lastSyncedAt: '3 min ago',
};

const mockSuggestion = {
  title: 'Wireless Bluetooth 5.3 Earbuds - Active Noise Cancelling, 30H Battery, IPX5 Waterproof',
  bullets: [
    'Premium Active Noise Cancellation — immersive listening experience',
    '30-Hour Extended Battery Life with quick-charge case (10 min = 2 hours)',
    'Bluetooth 5.3 Technology — ultra-stable, low-latency audio connection',
    'IPX5 Waterproof Rating — perfect for workouts and outdoor activities',
    'Intuitive Touch Controls — effortless tap to play, pause, skip, or answer calls'
  ],
  description: 'Elevate your audio experience with premium wireless earbuds...',
  searchTerms: 'earbuds bluetooth 5.3 noise cancelling waterproof',
  confidence: 0.92,
  reasoning: 'Added Bluetooth version to title for search visibility. Expanded bullet points with specific details. Reorganized search terms by relevance.',
  diff: {
    title: { added: ['5.3', 'IPX5 Waterproof'], removed: ['with Noise Cancellation'] },
    bullets: [
      { index: 0, old: 'Active Noise Cancellation — block out background noise', new: 'Premium Active Noise Cancellation — immersive listening experience' },
    ],
  },
};

vi.mock('@/lib/api', () => ({
  listingsApi: {
    get: vi.fn(() => Promise.resolve(mockCurrent)),
    getSuggestion: vi.fn(() => Promise.resolve(mockSuggestion)),
    applySuggestion: vi.fn(() => Promise.resolve({ success: true })),
  }
}));

describe('ListingEditor', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows current listing on the left panel', async () => {
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => {
      expect(screen.getByText(/current listing/i)).toBeInTheDocument();
      const matches = screen.getAllByText(/Wireless Bluetooth/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows AI suggestion on the right panel', async () => {
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => {
      expect(screen.getByText(/ai suggestion/i)).toBeInTheDocument();
    });
  });

  it('shows ASIN in data badge format', async () => {
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => {
      const badge = screen.getByText('B08N49K23V');
      expect(badge.className).toMatch(/border-dashed|primary-pop/);
    });
  });

  it('displays confidence score', async () => {
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => expect(screen.getByText('92%')).toBeInTheDocument());
  });

  it('shows character counts on bullets', async () => {
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => {
      expect(screen.getByTestId('char-count-bullet-0')).toBeInTheDocument();
    });
  });

  it('highlights diff — added text in green', async () => {
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => {
      const addedElements = screen.getAllByTestId('diff-added');
      expect(addedElements.length).toBeGreaterThan(0);
      expect(addedElements[0].className).toMatch(/emerald|green/);
    });
  });

  it('shows expandable reasoning section', async () => {
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => screen.getByText(/reasoning/i));
    await user.click(screen.getByText(/reasoning/i));
    expect(screen.getByText(/Added Bluetooth version/)).toBeVisible();
  });

  it('Apply All button calls API', async () => {
    const { listingsApi } = await import('@/lib/api');
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => screen.getByRole('button', { name: /apply all/i }));
    await user.click(screen.getByRole('button', { name: /apply all/i }));
    expect(listingsApi.applySuggestion).toHaveBeenCalledWith('B08N49K23V', expect.any(Object));
  });

  it('Regenerate button fetches new suggestion', async () => {
    const { listingsApi } = await import('@/lib/api');
    render(<ListingEditor asin="B08N49K23V" />);
    await waitFor(() => screen.getByRole('button', { name: /regenerate/i }));
    const callsBefore = (listingsApi.getSuggestion as ReturnType<typeof vi.fn>).mock.calls.length;
    await user.click(screen.getByRole('button', { name: /regenerate/i }));
    await waitFor(() => {
      expect((listingsApi.getSuggestion as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });
});
