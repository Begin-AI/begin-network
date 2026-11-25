import { sqliteTable, text, integer, uniqueIndex, primaryKey, index } from "drizzle-orm/sqlite-core";

export const addresses = sqliteTable("addresses", {
  address: text("address").primaryKey(), owner: text("owner").notNull(),
  label: text("label").notNull(), createdAt: integer("created_at").notNull(),
}, t => [uniqueIndex("owner_label").on(t.owner, t.label)]);
export const subscriptions = sqliteTable("subscriptions", {
  address: text("address").notNull().references(() => addresses.address),
  topic: text("topic").notNull(), expiresAt: integer("expires_at").notNull(),
}, t => [primaryKey({columns: [t.address, t.topic]}), index("topic_expiry").on(t.topic, t.expiresAt)]);
export const messages = sqliteTable("messages", {
  id: text("id").primaryKey(), sender: text("sender").notNull().references(() => addresses.address),
  owner: text("owner").notNull(), idempotencyKey: text("idempotency_key").notNull(),
  digest: text("digest").notNull(), kind: text("kind").notNull(),
  thread: text("thread").notNull(), topic: text("topic").notNull(),
  text: text("text").notNull(), createdAt: integer("created_at").notNull(),
  expiresAt: integer("expires_at").notNull(),
}, t => [uniqueIndex("sender_idempotency").on(t.sender, t.idempotencyKey), index("owner_created").on(t.owner, t.createdAt)]);
export const deliveries = sqliteTable("deliveries", {
  seq: integer("seq").primaryKey({autoIncrement: true}),
  message: text("message").notNull().references(() => messages.id),
  recipient: text("recipient").notNull().references(() => addresses.address),
  acknowledgedAt: integer("acknowledged_at"),
}, t => [uniqueIndex("message_recipient").on(t.message, t.recipient), index("recipient_seq").on(t.recipient, t.seq)]);
export const clientConnections = sqliteTable("client_connections", {
  id: text("id").primaryKey(), tokenHash: text("token_hash").notNull().unique(),
  owner: text("owner").notNull(), address: text("address").notNull().references(() => addresses.address),
  label: text("label").notNull(), createdAt: integer("created_at").notNull(),
  expiresAt: integer("expires_at").notNull(), revokedAt: integer("revoked_at"),
}, t => [index("connection_owner").on(t.owner)]);
