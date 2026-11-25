import { createHttpServer } from "./http.ts";
import { createHost } from "./host.ts";
const origin=process.env.BEGIN_ORIGIN??"";
const host=await createHost({origin,database:process.env.BEGIN_DATABASE??"begin.sqlite",secret:process.env.BETTER_AUTH_SECRET??"",allowedEmails:(process.env.BEGIN_ALLOWED_EMAILS??"").split(",").filter(Boolean),localTest:process.env.BEGIN_LOCAL_TEST==="1",googleClientId:process.env.GOOGLE_CLIENT_ID,googleClientSecret:process.env.GOOGLE_CLIENT_SECRET});
const server=createHttpServer(host,origin);
server.requestTimeout=15000;server.headersTimeout=10000;
server.listen(Number(process.env.PORT??8080),process.env.BEGIN_BIND??"127.0.0.1",()=>console.log("Begin Discovery host listening; external TLS must be provided by the operator."));
for(const signal of["SIGINT","SIGTERM"]as const)process.on(signal,()=>server.close(()=>{host.close();process.exit(0);}));
