import { test } from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Discovery, type Database } from "../lib/discovery.ts";
import { createClientConnection, resolveClientConnection, revokeClientConnection } from "../lib/client-connections.ts";
import { handleMcp, callTool, tools } from "../lib/mcp.ts";

function adapter(sqlite:DatabaseSync):Database {
  return {prepare(sql:string) {let values:unknown[]=[]; const statement = {
    bind(...args:unknown[]) {values=args; return statement;},
    async first<T>() {return (sqlite.prepare(sql).get(...values as never[])??null) as T|null;},
    async all<T>() {return {results:sqlite.prepare(sql).all(...values as never[]) as T[]};},
    execute() {return sqlite.prepare(sql).run(...values as never[]);},
  };return statement;}, async batch(statements) {sqlite.exec("BEGIN IMMEDIATE");try {const result=statements.map(s=>(s as unknown as {execute():unknown}).execute());sqlite.exec("COMMIT");return result;}catch(e){sqlite.exec("ROLLBACK");throw e;}}};
}
const schema = readFileSync(new URL("../drizzle/0000_old_texas_twister.sql",import.meta.url),"utf8")+"\n"+readFileSync(new URL("../drizzle/0001_secret_vivisector.sql",import.meta.url),"utf8");
function fixture(path=":memory:") {const sql=new DatabaseSync(path);sql.exec(schema);const db=adapter(sql);return {sql,db,a:new Discovery(db,"alice","https://begin.example",1000),b:new Discovery(db,"bob","https://begin.example",1000),c:new Discovery(db,"eve","https://begin.example",1000)};}
function thread(value:unknown):string { assert.ok(value && typeof value === "object" && "thread_id" in value); return (value as {thread_id:string}).thread_id; }
async function body(response:Response):Promise<{result:{protocolVersion?:string;tools:unknown[];isError:boolean};error:{code:number}}> { const text=await response.text();return JSON.parse(response.headers.get("content-type")?.includes("text/event-stream") ? text.split("\n").find(line=>line.startsWith("data: "))!.slice(6) : text) as never; }
async function pair() {const f=fixture();const a=await f.a.register("gpt"),b=await f.b.register("claude");await f.b.subscribe(b.address,"guitar",7,true);return {...f,aa:a.address,bb:b.address};}

test("two independently authenticated participants exchange request, response and follow-up", async()=>{
  const f=await pair();
  const request=await f.a.submit(f.aa,"ask-1","guitar","Seeking a willing guitar mentor",3600);
  assert.equal(request.delivery_count,1);
  const incoming=await f.b.inbox(f.bb,0,10);
  assert.equal(incoming.messages[0].text,"Seeking a willing guitar mentor");
  assert.equal(incoming.messages[0].kind,"discovery_request");
  const response=await f.b.reply(f.bb,"answer-1",thread(request),"I can help on Saturday","discovery_response");
  assert.equal((await f.a.inbox(f.aa,0,10)).messages[0].id,response.message_id);
  await f.a.reply(f.aa,"clarify-1",thread(request),"What time?","discovery_followup",f.bb);
  assert.equal((await f.b.inbox(f.bb,0,10)).messages[1].kind,"discovery_followup");
  f.sql.close();
});
test("durable address and unread inbox survive database close and reopen",async()=>{
  const dir=mkdtempSync(join(tmpdir(),"begin-discovery-")),path=join(dir,"test.sqlite");
  try {const f=fixture(path);const a=await f.a.register("phone"),b=await f.b.register("tablet");await f.b.subscribe(b.address,"guitar",1,true);await f.a.submit(a.address,"durable","guitar","Hello",3600);f.sql.close();
    const sql=new DatabaseSync(path),service=new Discovery(adapter(sql),"bob","https://begin.example",1001);
    assert.equal((await service.register("tablet")).address,b.address);assert.equal((await service.inbox(b.address,0,10)).messages.length,1);sql.close();
  } finally {rmSync(dir,{recursive:true,force:true});}
});
test("isolation: cannot read, acknowledge, subscribe or impersonate another account",async()=>{
 const f=await pair();await assert.rejects(()=>f.c.inbox(f.bb,0,10),/not owned/);await assert.rejects(()=>f.c.subscribe(f.bb,"guitar",1,true),/not owned/);await assert.rejects(()=>f.c.acknowledge(f.bb,[crypto.randomUUID()]),/not owned/);await assert.rejects(()=>f.c.submit(f.aa,"x","guitar","Spoof",100),/not owned/);assert.deepEqual((await f.c.list()).addresses,[]);f.sql.close();
});
test("idempotency returns original receipt and rejects altered reuse",async()=>{
 const f=await pair();const first=await f.a.submit(f.aa,"retry","guitar","Hello",3600);const second=await f.a.submit(f.aa,"retry","guitar","Hello",3600);assert.deepEqual(second,first);assert.equal((await f.b.inbox(f.bb,0,10)).messages.length,1);
 await assert.rejects(()=>f.a.submit(f.aa,"retry","guitar","Changed",3600),/different content/);
 const r=await f.b.reply(f.bb,"retry-reply",thread(first),"Yes","discovery_response");assert.deepEqual(await f.b.reply(f.bb,"retry-reply",thread(first),"Yes","discovery_response"),r);f.sql.close();
});
test("unsubscribed or expired subscriptions cannot receive fresh requests",async()=>{
 const f=await pair();await f.b.subscribe(f.bb,"guitar",1,false);assert.equal((await f.a.submit(f.aa,"empty","guitar","Hello",3600)).delivery_count,0);
 await f.b.subscribe(f.bb,"guitar",1,true);const future=new Discovery(f.db,"alice","https://begin.example",1000+86401);assert.equal((await future.submit(f.aa,"expired","guitar","Hello",3600)).delivery_count,0);f.sql.close();
});
test("thread participation enforced, expired request not replyable",async()=>{
 const f=await pair();const r=await f.a.submit(f.aa,"thread","guitar","Hello",60);const eve=await f.c.register("eve");await assert.rejects(()=>f.c.reply(eve.address,"forged",thread(r),"Intrude","discovery_response"),/not a recipient/);await assert.rejects(()=>f.a.reply(f.aa,"bad-target",thread(r),"Hello","discovery_followup",eve.address),/not part/);
 const future=new Discovery(f.db,"bob","https://begin.example",1060);assert.equal((await future.inbox(f.bb,0,10)).messages.length,0);await assert.rejects(()=>future.reply(f.bb,"expired",thread(r),"Yes","discovery_response"),/expired/);f.sql.close();
});
test("pagination and explicit acknowledgement preserve unprocessed messages",async()=>{
 const f=await pair();for(let i=0;i<3;i++) await f.a.submit(f.aa,`msg-${i}`,"guitar",`${i}`,3600);
 const first=await f.b.inbox(f.bb,0,2);assert.equal(first.has_more,true);const last=await f.b.inbox(f.bb,first.next_cursor,2);assert.equal(last.messages.length,1);
 await f.b.acknowledge(f.bb,[String(first.messages[0].id)]);assert.equal((await f.b.inbox(f.bb,0,10)).messages.length,2);await f.b.acknowledge(f.bb,[String(first.messages[0].id)]);assert.equal((await f.b.inbox(f.bb,0,10)).messages.length,2);f.sql.close();
});
test("fanout above 20 fails without partial writes",async()=>{
 const f=fixture();const sender=await f.a.register("sender");for(let i=0;i<21;i++){const s=new Discovery(f.db,`u-${i}`,"https://begin.example",1000);const a=await s.register("recipient");await s.subscribe(a.address,"guitar",1,true);}await assert.rejects(()=>f.a.submit(sender.address,"fanout","guitar","Hello",3600),/20 recipients/);assert.equal(f.sql.prepare("SELECT count(*) AS n FROM messages").get()!.n,0);f.sql.close();
});
test("daily account quota is shared across addresses and retry does not spend again",async()=>{
 const f=await pair();for(let i=0;i<50;i++) await f.a.submit(f.aa,`quota-${i}`,"guitar","Hello",3600);await f.a.submit(f.aa,"quota-0","guitar","Hello",3600);const another=await f.a.register("other");await assert.rejects(()=>f.a.submit(another.address,"exceeded","guitar","Hello",3600),/Daily/);f.sql.close();
});
test("tool schemas reject unknown arguments, invalid types and oversized content",async()=>{
 const f=fixture();for(const args of [{label:"okay",owner:"bob"},{label:""},{label:123},{label:"x".repeat(65)}]) await assert.rejects(()=>callTool(f.db,"alice","https://begin.example","begin_register_address",args,1000),/Invalid/);
 await assert.rejects(()=>callTool(f.db,"","https://begin.example","begin_register_address",{label:"x"},1000),/Authentication/);assert.equal(tools.length,7);f.sql.close();
});
function rpc(method:string,params:unknown={},extra:Record<string,string>={}) {return new Request("https://begin.example/mcp",{method:"POST",headers:{"content-type":"application/json",accept:"application/json, text/event-stream",...extra},body:JSON.stringify({jsonrpc:"2.0",id:1,method,params})});}
test("MCP initialization, discovery, listing and authenticated calls",async()=>{
 const f=fixture();let r=await handleMcp(rpc("initialize",{protocolVersion:"2025-03-26",capabilities:{},clientInfo:{name:"synthetic-test",version:"1"}}),f.db,null);assert.equal((await body(r)).result.protocolVersion,"2025-03-26");r=await handleMcp(rpc("tools/list"),f.db,null);assert.equal((await body(r)).result.tools.length,7);
 r=await handleMcp(rpc("tools/call",{name:"begin_register_address",arguments:{label:"gpt"}}),f.db,null);assert.equal(r.status,401);
 r=await handleMcp(rpc("tools/call",{name:"begin_register_address",arguments:{label:"gpt"}}),f.db,"alice");assert.equal((await body(r)).result.isError,false);f.sql.close();
});
test("HTTP rejects cross-origin, oversized, malformed and unsupported requests",async()=>{
 const f=fixture();assert.equal((await handleMcp(rpc("tools/list",{}, {origin:"https://evil.example"}),f.db,"alice")).status,403);
 assert.equal((await handleMcp(new Request("https://begin.example/mcp",{method:"POST",headers:{"content-type":"application/json"},body:"x".repeat(20000)}),f.db,"alice")).status,413);
 assert.equal((await handleMcp(new Request("https://begin.example/mcp",{method:"POST",headers:{"content-type":"application/json"},body:"{"}),f.db,"alice")).status,400);
 const r=await handleMcp(rpc("unknown"),f.db,"alice");assert.equal((await body(r)).error.code,-32601);f.sql.close();
});
test("batch failure rolls back message and delivery together",async()=>{
 const f=await pair();f.sql.exec("CREATE TRIGGER reject_delivery BEFORE INSERT ON deliveries BEGIN SELECT RAISE(ABORT, 'synthetic storage failure'); END;");await assert.rejects(()=>f.a.submit(f.aa,"atomic","guitar","Hello",3600),/storage failure/);assert.equal(f.sql.prepare("SELECT count(*) AS n FROM messages").get()!.n,0);f.sql.close();
});


test("official SDK handles modern discovery and enforces modern envelope and headers",async()=>{
 const f=fixture();const meta={"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{name:"synthetic-test",version:"1"}};
 const headers={"mcp-protocol-version":"2026-07-28","mcp-method":"tools/list"};
 const list=await handleMcp(rpc("tools/list",{_meta:meta},headers),f.db,"alice");assert.equal(list.status,200);assert.equal((await body(list)).result.tools.length,7);
 const invalid=await handleMcp(rpc("tools/list",{},headers),f.db,"alice");assert.equal(invalid.status,400);
 const discovered=await handleMcp(rpc("server/discover",{}),f.db,null);assert.equal(discovered.status,200);const d=await body(discovered) as unknown as {result:{supportedVersions:string[]}};assert.ok(d.result.supportedVersions.includes("2026-07-28"));f.sql.close();
});


test("Sites JSON-only tool discovery works without SSE or protocol envelope",async()=>{
 const f=fixture();const request=new Request("https://begin.example/mcp",{method:"POST",headers:{"content-type":"application/json",accept:"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:1,method:"tools/list",params:{}})});
 const response=await handleMcp(request,f.db,null);assert.equal(response.status,200);assert.match(response.headers.get("content-type")!,/application\/json/);assert.equal((await body(response)).result.tools.length,7);f.sql.close();
});


test("address connection stores only a hash, resolves until expiry and revokes by owner",async()=>{
 const f=await pair();const c=await createClientConnection(f.db,"alice",f.aa,1,1000);const stored=f.sql.prepare("SELECT * FROM client_connections WHERE id=?").get(c.id)!;assert.notEqual(stored.token_hash,c.token);assert.ok(!JSON.stringify(stored).includes(c.token));
 assert.deepEqual({...await resolveClientConnection(f.db,c.token,1001)},{owner:"alice",address:f.aa,label:"gpt"});assert.equal(await resolveClientConnection(f.db,c.token,1000+86400),null);assert.equal(await resolveClientConnection(f.db,"begin_"+"0".repeat(64),1001),null);
 await revokeClientConnection(f.db,"bob",c.id,1002);assert.ok(await resolveClientConnection(f.db,c.token,1003));await revokeClientConnection(f.db,"alice",c.id,1004);assert.equal(await resolveClientConnection(f.db,c.token,1005),null);f.sql.close();
});
test("delegated client cannot access other addresses or register another label",async()=>{
 const f=await pair(),other=await f.a.register("other");const scope={address:f.aa,label:"gpt"};
 const listed=await callTool(f.db,"alice","https://begin.example","begin_list_addresses",{},1000,scope) as {addresses:{address:string}[]};assert.deepEqual(listed.addresses.map(a=>a.address),[f.aa]);
 await assert.rejects(()=>callTool(f.db,"alice","https://begin.example","begin_check_inbox",{address:other.address,after:0,limit:10},1000,scope),/limited/);
 await assert.rejects(()=>callTool(f.db,"alice","https://begin.example","begin_register_address",{label:"other"},1000,scope),/limited/);
 const recovered=await callTool(f.db,"alice","https://begin.example","begin_register_address",{label:"gpt"},1000,scope) as {address:string};assert.equal(recovered.address,f.aa);
 await assert.rejects(()=>createClientConnection(f.db,"bob",f.aa,1,1000),/not owned/);await assert.rejects(()=>createClientConnection(f.db,"alice",f.aa,8,1000),/Invalid/);f.sql.close();
});
