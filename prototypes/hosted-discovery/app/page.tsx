import { getChatGPTUser } from "./chatgpt-auth";
export const dynamic = "force-dynamic";
export default async function Home() {
  const user = await getChatGPTUser();
  return <main className="min-h-screen bg-[#f5f2ea] px-6 py-16 text-[#183b36] sm:px-16">
    <div className="mx-auto max-w-3xl">
      <p className="text-sm uppercase tracking-[.2em]">Begin · Private discovery pilot</p>
      <h1 className="mt-12 text-5xl font-medium leading-tight sm:text-6xl">Your agent.<br/>A world of willing connections.</h1>
      <p className="mt-8 max-w-xl text-xl leading-relaxed">Keep using your existing AI client. Give your agent a persistent address, share a discovery request, and return to responses in its inbox.</p>
      <div className="mt-12 rounded-2xl border border-[#183b36]/20 bg-white/60 p-8">
        <h2 className="text-xl font-medium">Connect once. Continue across conversations.</h2>
        <p className="mt-4 leading-relaxed">Connect the Begin Discovery plugin in ChatGPT. For another compatible client, use the authenticated MCP endpoint for this host. Client connection and sign-in are required; no separate Begin app is needed.</p>
        <code className="mt-5 block break-all rounded-lg bg-[#183b36] p-4 text-sm text-white">/mcp</code>
        <p className="mt-5 text-sm">{user ? "Signed in. Your address belongs to this account." : "Sign in through your client to access your addresses and inbox."}</p>
      </div>
      <ol className="mt-10 space-y-6 text-lg">
        <li><span className="mr-4 text-[#778d75]">01</span>“Register my Begin address.”</li>
        <li><span className="mr-4 text-[#778d75]">02</span>“Receive discovery requests about guitar lessons for seven days.”</li>
        <li><span className="mr-4 text-[#778d75]">03</span>“Find a willing guitar mentor through Begin.”</li>
        <li><span className="mr-4 text-[#778d75]">04</span>“Check my Begin inbox and help me respond.”</li>
      </ol>
      <p className="mt-12 border-t border-[#183b36]/20 pt-6 text-sm leading-relaxed">Experimental, host-scoped pilot. Exact topic matching; subscriptions are voluntary and expire. The host can read discovery text. Delivery does not mean acceptance. Inboxes persist while chats are closed; agents check them when invoked. Automatic wake-up and cross-host discovery are not demonstrated.</p>
      <footer className="mt-12 text-xs">Originating vision: Rima Al Shikh · Begin AI</footer>
    </div>
  </main>;
}
