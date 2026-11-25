import { createServer } from "node:http";
import type { createHost } from "./host.ts";
export function createHttpServer(host:Awaited<ReturnType<typeof createHost>>,origin:string){
const server=createServer(async(req,res)=>{try{
  const chunks:Buffer[]=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>16384){res.writeHead(413);res.end("Request body limit exceeded");return;}chunks.push(chunk);}
  const headers=new Headers();for(const[key,value]of Object.entries(req.headers))if(value!==undefined)headers.set(key,Array.isArray(value)?value.join(","):value);
  for(const key of [...headers.keys()])if(key.startsWith("oai-")||key.startsWith("x-forwarded-")||key==="forwarded")headers.delete(key);
  headers.set("x-begin-client-ip",req.socket.remoteAddress??"unknown");
  const url=new URL(req.url??"/",origin);if(!(req.url??"/").startsWith("/")||url.origin!==origin){res.writeHead(400);res.end("Invalid request target");return;}
  const request=new Request(url,{method:req.method,headers,...(chunks.length?{body:Buffer.concat(chunks)}:{})});const response=await host.fetch(request);
  res.statusCode=response.status;response.headers.forEach((value,key)=>{if(key!=="set-cookie")res.setHeader(key,value);});const cookies=response.headers.getSetCookie();if(cookies.length)res.setHeader("set-cookie",cookies);
  if(response.body)for await(const chunk of response.body as unknown as AsyncIterable<Uint8Array>)res.write(chunk);res.end();
}catch{res.writeHead(500);res.end("Service unavailable");}});
server.requestTimeout=15000;server.headersTimeout=10000;return server;
}
