CREATE TABLE `addresses` (
	`address` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`label` text NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `owner_label` ON `addresses` (`owner`,`label`);--> statement-breakpoint
CREATE TABLE `deliveries` (
	`seq` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`message` text NOT NULL,
	`recipient` text NOT NULL,
	`acknowledged_at` integer,
	FOREIGN KEY (`message`) REFERENCES `messages`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`recipient`) REFERENCES `addresses`(`address`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `message_recipient` ON `deliveries` (`message`,`recipient`);--> statement-breakpoint
CREATE INDEX `recipient_seq` ON `deliveries` (`recipient`,`seq`);--> statement-breakpoint
CREATE TABLE `messages` (
	`id` text PRIMARY KEY NOT NULL,
	`sender` text NOT NULL,
	`owner` text NOT NULL,
	`idempotency_key` text NOT NULL,
	`digest` text NOT NULL,
	`kind` text NOT NULL,
	`thread` text NOT NULL,
	`topic` text NOT NULL,
	`text` text NOT NULL,
	`created_at` integer NOT NULL,
	`expires_at` integer NOT NULL,
	FOREIGN KEY (`sender`) REFERENCES `addresses`(`address`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `sender_idempotency` ON `messages` (`sender`,`idempotency_key`);--> statement-breakpoint
CREATE INDEX `owner_created` ON `messages` (`owner`,`created_at`);--> statement-breakpoint
CREATE TABLE `subscriptions` (
	`address` text NOT NULL,
	`topic` text NOT NULL,
	`expires_at` integer NOT NULL,
	PRIMARY KEY(`address`, `topic`),
	FOREIGN KEY (`address`) REFERENCES `addresses`(`address`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `topic_expiry` ON `subscriptions` (`topic`,`expires_at`);