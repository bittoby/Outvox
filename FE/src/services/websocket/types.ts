/**
 * WebSocket Event Types
 */

export enum EventType {
  AGENT_HEALTH_UPDATE = "AGENT_HEALTH_UPDATE",
  CALL_STATS_UPDATE = "CALL_STATS_UPDATE",
  CAMPAIGN_PROGRESS = "CAMPAIGN_PROGRESS",
  CAMPAIGN_CREATED = "CAMPAIGN_CREATED",
  CAMPAIGN_UPDATED = "CAMPAIGN_UPDATED",
  POPUP_ADDED = "POPUP_ADDED",
  POPUP_UPDATED = "POPUP_UPDATED",
  POPUP_DISMISSED = "POPUP_DISMISSED",
  SMS_RECEIVED = "SMS_RECEIVED",
  SMS_SENT = "SMS_SENT",
  PHOTO_SUBMITTED = "PHOTO_SUBMITTED",
  PHOTO_UPDATED = "PHOTO_UPDATED",
  LEAD_UPDATED = "LEAD_UPDATED",
  LEAD_CREATED = "LEAD_CREATED",
  STORE_STATS_UPDATE = "STORE_STATS_UPDATE",
  PHONE_NUMBER_UPDATE = "PHONE_NUMBER_UPDATE",
}

export interface WebSocketEvent {
  type: string;
  timestamp: string;
  data: any;
}

export interface WebSocketMessage {
  action: "subscribe" | "unsubscribe" | "ping";
  event_types?: string[];
}

export type EventHandler = (event: WebSocketEvent) => void;

export interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  connectionId: string | null;
}

