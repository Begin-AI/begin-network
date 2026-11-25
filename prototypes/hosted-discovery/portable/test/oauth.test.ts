import { test } from "node:test";
import assert from "node:assert/strict";
import { createHost } from "../host.ts";
import { createHttpServer } from "../http.ts";
import { createServer } from "node:http";
import { once } from "node:events";

async function setup(){
  const placeholder=createServer();placeholder.listen(0,"127.0.0.1");await once(placeholder,"listening");const port=(placeholder.address() as {port:number}).port;await new Promise<void>(resolve=>placeholder.close(()=>resolve()));
  const origin=`http://127.0.0.1:${port}`;
  const host=await createHost({origin,database:":memory:",secret:crypto.randomUUID()+crypto.randomUUID(),allowedEmails:["alice@example.test","bob@example.test"],localTest:true});
  const server=createHttpServer(host,origin);server.listen(port,"127.0.0.1");await once(server,"listening");
  return {host,origin,close:async()=>{server.closeAllConnections();await new Promise<void>(resolve=>server.close(()=>resolve()));host.close();}};
}
async function json(response:Response){const text=await response.text();try{return JSON.parse(text);}catch{throw new Error(`Expected JSON (${response.status}): ${text.slice(0,100)}`);}}
function cookie(response:Response){return response.headers.getSetCookie().map(x=>x.split(";")[0]).join("; ");}
async function authorize(origin:string,email:string,existingPassword?:string){
  const password=existingPassword??crypto.randomUUID()+crypto.randomUUID();
  const resource=origin+"/mcp",redirect="https://client.example.test/callback";
  const registration=await fetch(origin+"/api/auth/oauth2/register",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({client_name:"Synthetic MCP client",redirect_uris:[redirect],token_endpoint_auth_method:"none",grant_types:["authorization_code","refresh_token"],response_types:["code"],scope:"begin:discovery offline_access"})});
  const client=await json(registration);assert.equal(registration.status,201,JSON.stringify(client));assert.ok(client.client_id);
  const verifier=crypto.randomUUID()+crypto.randomUUID();const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(verifier));const challenge=Buffer.from(digest).toString("base64url");
  const url=new URL(origin+"/api/auth/oauth2/authorize");url.search=new URLSearchParams({client_id:client.client_id,redirect_uri:redirect,response_type:"code",scope:"begin:discovery offline_access",state:"synthetic-state",code_challenge:challenge,code_challenge_method:"S256",resource}).toString();
  const auth=await fetch(url,{redirect:"manual",headers:{accept:"text/html"}});const authBody=auth.status===200?await json(auth):null;assert.ok(auth.status===302||auth.status===200);const login=new URL(auth.headers.get("location")??authBody?.url??authBody?.redirect_uri,origin);assert.equal(login.pathname,"/sign-in");
  const signup=await fetch(origin+(existingPassword?"/api/auth/sign-in/email":"/api/auth/sign-up/email"),{method:"POST",headers:{"content-type":"application/json",origin},body:JSON.stringify({email,name:"Synthetic participant",password,oauth_query:login.search.slice(1)})});
  const signed=await json(signup);assert.equal(signup.status,200,JSON.stringify(signed));const session=cookie(signup);assert.ok(session);assert.ok(signed.url,"OAuth continuation after sign-up required");
  const consent=new URL(signed.url,origin);assert.equal(consent.pathname,"/consent");
  const rendered=await fetch(consent,{headers:{cookie:session}});assert.equal(rendered.status,200);assert.match(await rendered.text(),/Allow discovery access/);
  const allowed=await fetch(origin+"/api/auth/oauth2/consent",{method:"POST",headers:{"content-type":"application/json",origin,cookie:session},body:JSON.stringify({accept:true,oauth_query:consent.search.slice(1)})});
  const result=await json(allowed);assert.equal(allowed.status,200,JSON.stringify(result));const callback=new URL(result.url??result.redirect_uri);assert.equal(callback.origin,"https://client.example.test");assert.equal(callback.searchParams.get("state"),"synthetic-state");assert.ok(callback.searchParams.get("code"));
  const form=new URLSearchParams({grant_type:"authorization_code",client_id:client.client_id,code:callback.searchParams.get("code")!,redirect_uri:redirect,code_verifier:verifier,resource});
  const tokenResponse=await fetch(origin+"/api/auth/oauth2/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body:form});
  const tokens=await json(tokenResponse);assert.equal(tokenResponse.status,200,JSON.stringify(tokens));assert.ok(tokens.access_token);return {tokens,client,form,password};
}
async function call(origin:string,token:string,name:string,args:unknown){const response=await fetch(origin+"/mcp",{method:"POST",headers:{"content-type":"application/json",accept:"application/json, text/event-stream","mcp-protocol-version":"2026-07-28","mcp-method":"tools/call","mcp-name":name,authorization:`Bearer ${token}`},body:JSON.stringify({jsonrpc:"2.0",id:crypto.randomUUID(),method:"tools/call",params:{name,arguments:args,_meta:{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{name:"synthetic-test",version:"1"},"io.modelcontextprotocol/clientCapabilities":{}}}})});const body=await json(response);assert.equal(response.status,200,JSON.stringify(body));assert.equal(body.result?.isError,false,JSON.stringify(body));return body.result.structuredContent??JSON.parse(body.result.content[0].text);}

test("portable host advertises CIMD, DCR and resource-bound PKCE",async()=>{const f=await setup();try{const response=await fetch(f.origin+"/.well-known/oauth-authorization-server");const metadata=await json(response);assert.equal(metadata.client_id_metadata_document_supported,true);assert.equal(metadata.registration_endpoint,f.origin+"/api/auth/oauth2/register");assert.deepEqual(metadata.code_challenge_methods_supported,["S256"]);const denied=await fetch(f.origin+"/mcp",{method:"POST"});assert.equal(denied.status,401);assert.match(denied.headers.get("www-authenticate")!,/resource_metadata/);}finally{await f.close();}});
test("two complete OAuth flows then discovery request, response and ownership isolation",async()=>{const f=await setup();try{
 const alice=await authorize(f.origin,"alice@example.test"),bob=await authorize(f.origin,"bob@example.test");
 const secondAlice=await authorize(f.origin,"alice@example.test",alice.password);
 const a=await call(f.origin,alice.tokens.access_token,"begin_register_address",{label:"gpt-context"}),b=await call(f.origin,bob.tokens.access_token,"begin_register_address",{label:"claude-context"});
 assert.deepEqual(await call(f.origin,secondAlice.tokens.access_token,"begin_register_address",{label:"gpt-context"}),a);
 await call(f.origin,bob.tokens.access_token,"begin_set_discovery_subscription",{address:b.address,topic:"pilot.guitar",days:1,enabled:true});
 const request=await call(f.origin,alice.tokens.access_token,"begin_submit_discovery",{address:a.address,idempotency_key:"oauth-pilot-request",topic:"pilot.guitar",text:"Synthetic request: guitar mentor",ttl_seconds:3600});assert.equal(request.delivery_count,1);
 const inbox=await call(f.origin,bob.tokens.access_token,"begin_check_inbox",{address:b.address,after:0,limit:10});assert.equal(inbox.messages.length,1);
 await call(f.origin,bob.tokens.access_token,"begin_reply_discovery",{address:b.address,idempotency_key:"oauth-pilot-response",request_id:request.thread_id,text:"Synthetic response: willing to discuss",kind:"discovery_response"});
 const answer=await call(f.origin,alice.tokens.access_token,"begin_check_inbox",{address:a.address,after:0,limit:10});assert.equal(answer.messages[0].kind,"discovery_response");
 const other=await fetch(f.origin+"/mcp",{method:"POST",headers:{"content-type":"application/json",accept:"application/json, text/event-stream","mcp-protocol-version":"2026-07-28","mcp-method":"tools/call","mcp-name":"begin_check_inbox",authorization:`Bearer ${alice.tokens.access_token}`},body:JSON.stringify({jsonrpc:"2.0",id:1,method:"tools/call",params:{name:"begin_check_inbox",arguments:{address:b.address,after:0,limit:10},_meta:{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}})});
 const denied=await json(other);assert.equal(denied.result.isError,true);assert.match(denied.result.content[0].text,/not owned/);
 const forged=await fetch(f.origin+"/mcp",{method:"POST",headers:{authorization:"Bearer bogus","oai-authenticated-user-id":"alice"}});assert.equal(forged.status,401);
 const replay=await fetch(f.origin+"/api/auth/oauth2/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body:alice.form});assert.equal(replay.status,400);
 }finally{await f.close();}});

test("remote startup fails closed without verified sign-in configuration",async()=>{
 await assert.rejects(()=>createHost({origin:"https://discovery.example.test",database:":memory:",secret:crypto.randomUUID()+crypto.randomUUID(),allowedEmails:[]}),/verified Google sign-in/);
 await assert.rejects(()=>createHost({origin:"https://discovery.example.test",database:":memory:",secret:crypto.randomUUID()+crypto.randomUUID(),allowedEmails:[],localTest:true}),/loopback/);
});
test("closed registration and forged consent are rejected",async()=>{
 const f=await setup();try{
  const signup=await fetch(f.origin+"/api/auth/sign-up/email",{method:"POST",headers:{"content-type":"application/json",origin:f.origin},body:JSON.stringify({email:"uninvited@example.test",name:"Synthetic uninvited",password:crypto.randomUUID()+crypto.randomUUID()})});assert.equal(signup.status,403);
  const consent=await fetch(f.origin+"/consent?client_id=forged&scope=begin%3Adiscovery&sig=invalid&exp=9999999999");assert.equal(consent.status,400);
  const cross=await fetch(f.origin+"/api/auth/oauth2/register",{method:"POST",headers:{origin:"https://evil.example.test","content-type":"application/json"},body:"{}"});assert.equal(cross.status,403);
 }finally{await f.close();}
});
