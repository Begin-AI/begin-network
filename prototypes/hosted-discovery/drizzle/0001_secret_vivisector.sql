CREATE TABLE `client_connections` (
	`id` text PRIMARY KEY NOT NULL,
	`token_hash` text NOT NULL,
	`owner` text NOT NULL,
	`address` text NOT NULL,
	`label` text NOT NULL,
	`created_at` integer NOT NULL,
	`expires_at` integer NOT NULL,
	`revoked_at` integer,
	FOREIGN KEY (`address`) REFERENCES `addresses`(`address`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `client_connections_token_hash_unique` ON `client_connections` (`token_hash`);--> statement-breakpoint
CREATE INDEX `connection_owner` ON `client_connections` (`owner`);