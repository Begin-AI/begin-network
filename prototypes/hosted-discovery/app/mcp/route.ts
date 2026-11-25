import { env } from "cloudflare:workers";
import { handleMcp } from "@/lib/mcp";
import { resolveClientConnection } from "@/lib/client-connections";
import type { Database } from "@/lib/discovery";
export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  if (!env.DB) return Response.json({error:"Database unavailable"},{status:503});
  const db=env.DB as unknown as Database;
  const browserIdentity=request.headers.get("oai-authenticated-user-id");
  const authorization=request.headers.get("authorization");
  const credential=authorization?.startsWith("Bearer begin_")?authorization.slice(7):null;
  if(new URL(request.url).pathname==="/client-mcp" && !credential) return Response.json({error:"Begin client credential required"},{status:401,headers:{"cache-control":"no-store"}});
  if(credential) {
    const connection=await resolveClientConnection(db,credential);
    if(!connection || (browserIdentity && browserIdentity!==connection.owner)) return Response.json({error:"Invalid or expired Begin client connection"},{status:401,headers:{"cache-control":"no-store"}});
    return handleMcp(request,db,connection.owner,{address:connection.address,label:connection.label});
  }
  return handleMcp(request,db,browserIdentity);
}
export function GET() { return new Response(null,{status:405,headers:{Allow:"POST"}}); }
