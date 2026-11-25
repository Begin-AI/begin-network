import { DatabaseSync } from "node:sqlite";
import type { Database } from "../lib/discovery.ts";
/** The same discovery service runs against SQLite or the hosted D1 binding. */
export function discoveryDatabase(sqlite:DatabaseSync):Database {
  return {prepare(sql:string) {let values:unknown[]=[]; const statement={
    bind(...args:unknown[]) {values=args;return statement;},
    async first<T>() {return (sqlite.prepare(sql).get(...values as never[])??null) as T|null;},
    async all<T>() {return {results:sqlite.prepare(sql).all(...values as never[]) as T[]};},
    execute() {return sqlite.prepare(sql).run(...values as never[]);},
  };return statement;},async batch(statements) {
    sqlite.exec("BEGIN IMMEDIATE");try {const result=statements.map(s=>(s as unknown as {execute():unknown}).execute());sqlite.exec("COMMIT");return result;}catch(e){sqlite.exec("ROLLBACK");throw e;}
  }};
}
