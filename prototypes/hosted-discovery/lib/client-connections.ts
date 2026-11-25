import { DiscoveryError, type Database } from "./discovery.ts";
export type ConnectionIdentity = {owner:string;address:string;label:string};
const hash=async(value:string)=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value)))).map(x=>x.toString(16).padStart(2,"0")).join("");
export async function createClientConnection(db:Database,owner:string,address:string,days:number,now=Math.floor(Date.now()/1000)) {
  if(!owner || !Number.isInteger(days)||days<1||days>7)throw new DiscoveryError("Invalid connection request");
  const owned=await db.prepare("SELECT label FROM addresses WHERE owner=? AND address=?").bind(owner,address).first<{label:string}>();
  if(!owned)throw new DiscoveryError("Address unavailable or not owned by this account");
  const bytes=crypto.getRandomValues(new Uint8Array(32));
  const token="begin_"+Array.from(bytes).map(x=>x.toString(16).padStart(2,"0")).join("");
  const id=crypto.randomUUID(),expires=now+days*86400;
  await db.batch([db.prepare(`INSERT INTO client_connections(id,token_hash,owner,address,label,created_at,expires_at)
    SELECT ?,?,?,?,?,?,? WHERE (SELECT count(*) FROM client_connections WHERE owner=? AND revoked_at IS NULL AND expires_at>?) < 8`).bind(id,await hash(token),owner,address,owned.label,now,expires,owner,now)]);
  if(!await db.prepare("SELECT id FROM client_connections WHERE id=?").bind(id).first())throw new DiscoveryError("Active connection limit reached (8)");
  return {id,token,address,label:owned.label,expires_at:expires};
}
export async function resolveClientConnection(db:Database,token:string,now=Math.floor(Date.now()/1000)):Promise<ConnectionIdentity|null> {
  if(!/^begin_[a-f0-9]{64}$/.test(token))return null;
  return db.prepare(`SELECT c.owner,c.address,c.label FROM client_connections c JOIN addresses a ON a.address=c.address AND a.owner=c.owner
    WHERE c.token_hash=? AND c.revoked_at IS NULL AND c.expires_at>?`).bind(await hash(token),now).first<ConnectionIdentity>();
}
export async function revokeClientConnection(db:Database,owner:string,id:string,now=Math.floor(Date.now()/1000)) {
  if(!owner)throw new DiscoveryError("Authentication required");
  await db.batch([db.prepare("UPDATE client_connections SET revoked_at=COALESCE(revoked_at,?) WHERE id=? AND owner=?").bind(now,id,owner)]);
}
