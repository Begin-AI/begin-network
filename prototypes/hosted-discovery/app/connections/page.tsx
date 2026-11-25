import { env } from "cloudflare:workers";
import { requireChatGPTUser } from "../chatgpt-auth";
import ConnectionForm from "./connection-form";
export const dynamic="force-dynamic";
export default async function Connections(){
 const user=await requireChatGPTUser("/connections");
 if(!env.DB)return <main>Database unavailable.</main>;
 const addresses=await env.DB.prepare("SELECT address,label FROM addresses WHERE owner=? ORDER BY label").bind(user.userId).all<{address:string;label:string}>();
 const existing=await env.DB.prepare("SELECT id,address,label,expires_at,revoked_at FROM client_connections WHERE owner=? ORDER BY created_at DESC LIMIT 20").bind(user.userId).all<{id:string;address:string;label:string;expires_at:number;revoked_at:number|null}>();
 return <main className="min-h-screen bg-[#f5f2ea] px-6 py-14 text-[#183b36]"><div className="mx-auto max-w-2xl"><p>Begin · Private client connection</p><h1 className="mt-8 text-4xl">Connect an existing client</h1><p className="mt-6 leading-relaxed">Create a short-lived credential for one of your addresses. It permits discovery tools for that address only. It does not grant access to other addresses, your chats, calendars, email, or arbitrary task execution.</p><p className="mt-4 leading-relaxed">This private Sites host also requires its operator-controlled service-access header. A Begin credential alone cannot pass that platform gate. Use the <code>/client-mcp</code> endpoint and stored connector headers in Claude; keep both credentials out of conversation messages.</p><ConnectionForm addresses={addresses.results} existing={existing.results}/><p className="mt-8 text-sm leading-relaxed">The host can read discovery messages. Credentials expire within seven days and can be revoked here. This is a private interoperability pilot, not public network registration or a self-custodied identity.</p></div></main>;
}
