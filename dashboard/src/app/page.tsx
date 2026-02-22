import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-2">QC Dashboard</h1>
      <p className="text-gray-400 mb-8">Multi-lab calcium imaging quality control</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
        <Link
          href="/live"
          className="block rounded-xl bg-gray-800 hover:bg-gray-700 p-6 transition"
        >
          <h2 className="text-xl font-semibold mb-1">Live Session</h2>
          <p className="text-gray-400 text-sm">Real-time QC status and live plots</p>
        </Link>
        <Link
          href="/sessions"
          className="block rounded-xl bg-gray-800 hover:bg-gray-700 p-6 transition"
        >
          <h2 className="text-xl font-semibold mb-1">Sessions</h2>
          <p className="text-gray-400 text-sm">Browse past sessions and replay</p>
        </Link>
      </div>
    </main>
  );
}
