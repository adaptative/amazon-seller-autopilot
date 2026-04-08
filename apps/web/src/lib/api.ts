import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

// Attach auth token from localStorage on each request
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export interface Listing {
  asin: string;
  title: string;
  price: number;
  bsr: number;
  healthScore: number;
  status: 'active' | 'inactive' | 'suppressed';
  imageUrl: string;
}

export interface ListingDetail {
  asin: string;
  title: string;
  bullets: string[];
  description: string;
  searchTerms: string;
  price: number;
  bsr: number;
  healthScore: number;
  status: string;
  imageUrl: string;
  lastSyncedAt: string;
}

export interface ListingSuggestion {
  title: string;
  bullets: string[];
  description: string;
  searchTerms: string;
  confidence: number;
  reasoning: string;
  diff: {
    title?: { added: string[]; removed: string[] };
    bullets?: { index: number; old: string; new: string }[];
    description?: { old: string; new: string };
    searchTerms?: { old: string; new: string };
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export const listingsApi = {
  list: (params?: { search?: string; status?: string; page?: number; pageSize?: number }) =>
    apiClient.get<PaginatedResponse<Listing>>('/listings', { params }).then((r) => r.data),

  get: (asin: string) =>
    apiClient.get<ListingDetail>(`/listings/${asin}`).then((r) => r.data),

  getSuggestion: (asin: string) =>
    apiClient.post<ListingSuggestion>(`/listings/${asin}/optimize`).then((r) => r.data),

  applySuggestion: (asin: string, suggestion: Partial<ListingSuggestion>) =>
    apiClient.post<{ success: boolean }>(`/listings/${asin}/apply`, suggestion).then((r) => r.data),

  getHistory: (asin: string) =>
    apiClient.get<{ actions: any[] }>(`/listings/${asin}/history`).then((r) => r.data),
};

// ── Pricing types ────────────────────────────────────────────────

export interface PricingStats {
  buyBoxWinRate: number;
  buyBoxTrend: number;
  avgMargin: number;
  marginTrend: number;
  priceChangesToday: number;
  changesTrend: number;
  revenueImpact: number;
}

export interface PricedProduct {
  asin: string;
  title: string;
  ourPrice: number;
  buyBoxPrice: number;
  competitorCount: number;
  weOwnBuyBox: boolean;
  lastChange: string;
  lastChangeDir: 'up' | 'down' | 'none';
  imageUrl?: string;
}

export interface BuyBoxHistoryPoint {
  date: string;
  winRate: number;
}

export interface CompetitorPoint {
  sellerId: string;
  sellerName: string;
  price: number;
  rating: number;
  isOurs: boolean;
  isBuyBoxWinner: boolean;
}

export const pricingApi = {
  getStats: () =>
    apiClient.get<PricingStats>('/pricing/stats').then((r) => r.data),

  getProducts: (params?: { page?: number; pageSize?: number }) =>
    apiClient.get<PaginatedResponse<PricedProduct>>('/pricing/products', { params }).then((r) => r.data),

  getBuyBoxHistory: (days?: number) =>
    apiClient.get<BuyBoxHistoryPoint[]>('/pricing/buybox-history', { params: { days } }).then((r) => r.data),

  getCompetitorMap: (asin?: string) =>
    apiClient.get<CompetitorPoint[]>('/pricing/competitor-map', { params: { asin } }).then((r) => r.data),

  reprice: (asin: string) =>
    apiClient.post<{ success: boolean }>(`/pricing/reprice/${asin}`).then((r) => r.data),
};
