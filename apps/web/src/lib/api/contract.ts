import type {
  AlertItem,
  DemoState,
  GapsResponse,
  KioskMessageResponse,
  LiveSignal,
  ManagerChatResponse,
  Metrics,
  Overview,
  Product,
  Recommendation,
  RiskType,
  SkuDetail,
  Store,
} from "./types";

export type Unsubscribe = () => void;

export interface ApiClient {
  getStores(): Promise<Store[]>;
  getProducts(q: string): Promise<Product[]>;
  createKioskSession(storeId: string): Promise<{ sessionId: string }>;
  sendKioskMessage(input: {
    sessionId: string;
    storeId: string;
    text: string;
  }): Promise<KioskMessageResponse>;
  getOverview(storeId: string): Promise<Overview>;
  getRecommendations(
    storeId: string,
    risk?: RiskType,
  ): Promise<Recommendation[]>;
  getSkuDetail(storeId: string, sku: string): Promise<SkuDetail>;
  managerChat(input: {
    storeId: string;
    sessionId?: string;
    message: string;
    /** The product on screen, if any, so "why 60?" works without naming it. */
    sku?: string;
  }): Promise<ManagerChatResponse>;
  getGaps(storeId: string): Promise<GapsResponse>;
  /** Deletes this visitor's sandbox content (204). State arrives via realtime. */
  resetDemo(): Promise<void>;
  /** Recomputes the hero scenario into the sandbox. State arrives via realtime. */
  nextMorning(storeId: string): Promise<void>;
}

export interface RealtimeClient {
  subscribeAlerts(
    storeId: string,
    cb: (alerts: AlertItem[]) => void,
  ): Unsubscribe;
  subscribeLiveSignals(
    storeId: string,
    cb: (signals: LiveSignal[]) => void,
  ): Unsubscribe;
  subscribeMetrics(
    storeId: string,
    cb: (metrics: Metrics) => void,
  ): Unsubscribe;
  subscribeDemoState(cb: (state: DemoState) => void): Unsubscribe;
}
