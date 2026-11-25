// A private service-access endpoint for clients using stored header credentials.
// Sites enforces its platform gate; POST independently verifies the per-address
// credential and never accepts an identity supplied in tool arguments.
export { POST, GET, dynamic } from "../mcp/route";
