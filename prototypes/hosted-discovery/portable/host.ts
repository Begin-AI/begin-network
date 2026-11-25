import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { betterAuth, type BetterAuthOptions } from "better-auth";
import { APIError } from "better-auth/api";
import { jwt } from "better-auth/plugins";
import { getMigrations } from "better-auth/db/migration";
import { mcp, requireMcpAuth } from "@better-auth/mcp";
import { cimd } from "@better-auth/cimd";
import { fetchClientMetadataResource } from "@better-auth/cimd/node";
import { oauthProviderAuthServerMetadata, verifyOAuthQueryParams } from "@better-auth/oauth-provider";
import { createMcpHandler, McpServer, fromJsonSchema, type JsonSchemaType } from "@modelcontextprotocol/server";
import { tools, callTool } from "../lib/mcp.ts";
import { DiscoveryError } from "../lib/discovery.ts";
import { discoveryDatabase } from "./sqlite.ts";
import { loginPage, consentPage } from "./pages.ts";

export type HostConfig = {origin:string; database:string; secret:string; allowedEmails:string[]; localTest?:boolean;googleClientId?:string;googleClientSecret?:string};
export async function createHost(config:HostConfig) {
  const originUrl=new URL(config.origin);
  if(originUrl.origin!==config.origin || originUrl.username || originUrl.password) throw new Error("BEGIN_ORIGIN must be a canonical origin without path or credentials");
  const loopback=["127.0.0.1","localhost"].includes(originUrl.hostname);
  if(originUrl.protocol!=="https:" && !(loopback && config.localTest)) throw new Error("HTTPS required outside explicitly enabled loopback tests");
  if(config.localTest && !loopback) throw new Error("Local test mode requires loopback origin");
  if(!config.localTest && (!config.googleClientId || !config.googleClientSecret)) throw new Error("Configure verified Google sign-in before starting a remotely accessible host");
  if(config.secret.length<32) throw new Error("BETTER_AUTH_SECRET must be at least 32 characters");
  const sqlite=new DatabaseSync(config.database);
  sqlite.exec("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;");
  // Apply the initial discovery migration only to an empty discovery database.
  // Later schema versions must append explicit migrations rather than replay this file.
  if(!sqlite.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='addresses'").get()) sqlite.exec(readFileSync(new URL("../drizzle/0000_old_texas_twister.sql",import.meta.url),"utf8"));
  const db=discoveryDatabase(sqlite), resource=config.origin+"/mcp";
  const allowed=new Set(config.allowedEmails.map(x=>x.toLowerCase()));
  const options={
    appName:"Begin Discovery",baseURL:config.origin,basePath:"/api/auth",secret:config.secret,database:sqlite,
    socialProviders:config.googleClientId&&config.googleClientSecret?{google:{clientId:config.googleClientId,clientSecret:config.googleClientSecret}}:undefined,
    emailAndPassword:{enabled:!!config.localTest,minPasswordLength:12,maxPasswordLength:128},
    // Remote accounts require an invited, provider-verified email; passwords exist only in loopback tests.
    databaseHooks:{user:{create:{before:async(user)=>{if(!allowed.has(user.email.toLowerCase()) || (!config.localTest && !user.emailVerified)) throw new APIError("FORBIDDEN",{message:"This discovery host is invitation-only"});}}}},
    trustedOrigins:[config.origin],
    advanced:{ipAddress:{ipAddressHeaders:["x-begin-client-ip"]}},
    rateLimit:{enabled:true,storage:"database",window:60,max:100},
    plugins:[jwt(),mcp({loginPage:"/sign-in",consentPage:"/consent",resource,
      scopes:["openid","profile","offline_access","begin:discovery"],
      accessTokenExpiresIn:300,refreshTokenExpiresIn:604800,
      resources:[{identifier:resource,allowedScopes:["begin:discovery"]}],
      allowDynamicClientRegistration:true,allowUnauthenticatedClientRegistration:true,
      clientRegistrationDefaultApplicationType:"infer",
    }),cimd({fetchClientMetadataResource,metadataProfile:"mcp-2026-07-28"})],
  } satisfies BetterAuthOptions;
  const migration=await getMigrations(options);await migration.runMigrations();
  const auth=betterAuth(options);
  const metadata=oauthProviderAuthServerMetadata(auth);
  const protectedMcp=requireMcpAuth(auth,async(request,claims)=>{
    if(typeof claims.sub!=="string" || !claims.sub) return new Response("Missing account subject",{status:401});
    const owner=claims.sub;
    const handler=createMcpHandler(()=>{
      const server=new McpServer({name:"begin-discovery",version:"0.1.0"});
      for(const tool of tools) server.registerTool(tool.name,{
        description:tool.description,inputSchema:fromJsonSchema(tool.inputSchema as JsonSchemaType),annotations:tool.annotations,
      },async(args)=>{
        try {const output=await callTool(db,owner,config.origin,tool.name,args);return {content:[{type:"text" as const,text:JSON.stringify(output)}],structuredContent:output as Record<string,unknown>,isError:false};}
        catch(e){return {content:[{type:"text" as const,text:e instanceof DiscoveryError?e.message:"Service unavailable; retry with the same idempotency key"}],isError:true};}
      });
      return server;
    },{legacy:"stateless"});
    return handler.fetch(request);
  },{resource,requiredScopes:["begin:discovery"]});
  async function fetch(request:Request):Promise<Response> {
    const url=new URL(request.url);
    if(url.origin!==config.origin) return new Response("Unexpected host",{status:421});
    if(request.headers.has("origin") && request.headers.get("origin")!==config.origin) return new Response("Unexpected origin",{status:403});
    const path=url.pathname;
    if(path==="/health") return Response.json({status:"ok",service:"begin-discovery",mode:"invitation pilot"});
    if(path==="/.well-known/oauth-authorization-server" || path==="/.well-known/oauth-authorization-server/api/auth") return metadata(request);
    if(path.startsWith("/api/auth/") || path.startsWith("/.well-known/oauth-protected-resource")) {
      const response=await auth.handler(request);
      // The library may return its navigation target as JSON. A browser visiting
      // the authorization endpoint must actually reach the login/consent screen.
      if(request.method==="GET" && path==="/api/auth/oauth2/authorize" && response.status===200 && request.headers.get("accept")?.includes("text/html")) {
        const result=await response.clone().json() as {url?:string;redirect_uri?:string};
        const next=result.url??result.redirect_uri;
        if(next) {const headers=new Headers(response.headers);headers.delete("content-type");headers.set("location",next);return new Response(null,{status:302,headers});}
      }
      return response;
    }
    if(path==="/mcp") {
      if(request.method!=="POST") return new Response(null,{status:405,headers:{Allow:"POST"}});
      return protectedMcp(request);
    }
    if(path==="/sign-in") return loginPage(!!config.localTest);
    if(path==="/consent") {
      const query=url.search.slice(1),context=await auth.$context;
      if(!await verifyOAuthQueryParams(query,context.secret)) return new Response("Invalid or expired consent request",{status:400});
      const session=await auth.api.getSession({headers:request.headers});
      if(!session) return new Response("Sign in before granting consent",{status:401});
      const clientId=url.searchParams.get("client_id")??"";
      try {await auth.api.getOAuthClientPublic({query:{client_id:clientId},headers:request.headers});}
      catch {return new Response("Client unavailable",{status:400});}
      return consentPage(clientId,url.searchParams.get("scope")??"");
    }
    if(path==="/") return new Response("Begin Discovery invitation pilot. Connect this host's /mcp URL in your existing AI client. Originating vision: Rima Al Shikh · Begin AI.",{headers:{"content-type":"text/plain; charset=utf-8"}});
    return new Response("Not found",{status:404});
  }
  return {auth,fetch,close:()=>sqlite.close()};
}
