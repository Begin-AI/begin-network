import { env } from "cloudflare:workers";
import { createClientConnection, revokeClientConnection } from "@/lib/client-connections";
import { DiscoveryError, type Database } from "@/lib/discovery";
export const dynamic="force-dynamic";
export async function POST(request:Request){
 const headers={"cache-control":"no-store","x-content-type-options":"nosniff"};
 const owner=request.headers.get("oai-authenticated-user-id");
 if(!owner)return Response.json({error:"Browser sign-in required"},{status:401,headers});
 if(request.headers.get("origin")!==new URL(request.url).origin)return Response.json({error:"Same-origin browser request required"},{status:403,headers});
 if(!request.headers.get("content-type")?.startsWith("application/json"))return Response.json({error:"JSON required"},{status:415,headers});
 if(!env.DB)return Response.json({error:"Database unavailable"},{status:503,headers});
 const reader=request.body?.getReader();if(!reader)return Response.json({error:"Empty body"},{status:400,headers});
 const chunks:Uint8Array[]=[];let size=0;for(;;){const next=await reader.read();if(next.done)break;size+=next.value.length;if(size>4096){await reader.cancel();return Response.json({error:"Body limit exceeded"},{status:413,headers});}chunks.push(next.value);}
 try{const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}const body=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes));
  if(!body||typeof body!=="object"||Array.isArray(body))throw new DiscoveryError("Invalid connection request");
  const db=env.DB as unknown as Database;
  if(body.action==="create"&&typeof body.address==="string"&&Object.keys(body).every(k=>["action","address","days"].includes(k)))return Response.json(await createClientConnection(db,owner,body.address,body.days),{headers});
  if(body.action==="revoke"&&typeof body.id==="string"&&Object.keys(body).every(k=>["action","id"].includes(k))){await revokeClientConnection(db,owner,body.id);return Response.json({revoked:true},{headers});}
  throw new DiscoveryError("Invalid connection request");
 }catch(e){return Response.json({error:e instanceof DiscoveryError?e.message:"Connection request failed"},{status:400,headers});}
}
