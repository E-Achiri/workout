"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { getCurrentSession, signOut } from "@/lib/auth";
import { getMessages, createMessage, deleteMessage, getMe, Message, UserInfo } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [swipeOffset, setSwipeOffset] = useState<Record<number, number>>({});
  const [swiping, setSwiping] = useState<number | null>(null);
  const startX = useRef<number>(0);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const session = await getCurrentSession();
    if (!session) {
      router.push("/login");
      return;
    }
    setIsAuthenticated(true);

    try {
      const userInfo = await getMe();
      setUser(userInfo);
      await fetchMessages();
    } catch (err) {
      setError("Failed to load user info");
    }
  };

  const fetchMessages = async () => {
    setLoadingMessages(true);
    setError(null);
    try {
      const data = await getMessages();
      setMessages(data.messages || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch messages");
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    setLoading(true);
    setError(null);
    try {
      await createMessage(text);
      setText("");
      await fetchMessages();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    router.push("/login");
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteMessage(id);
      setMessages((prev) => prev.filter((msg) => msg.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete message");
    }
  };

  const handleSwipeStart = (id: number, clientX: number) => {
    startX.current = clientX;
    setSwiping(id);
  };

  const handleSwipeMove = (id: number, clientX: number) => {
    if (swiping !== id) return;
    const diff = clientX - startX.current;
    setSwipeOffset((prev) => ({ ...prev, [id]: Math.min(0, diff) }));
  };

  const handleSwipeEnd = (id: number) => {
    const offset = swipeOffset[id] || 0;
    if (offset < -100) {
      handleDelete(id);
    }
    setSwipeOffset((prev) => ({ ...prev, [id]: 0 }));
    setSwiping(null);
  };

  if (isAuthenticated === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-zinc-600 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
      <main className="flex flex-col items-center gap-8 p-8 w-full max-w-md">
        <div className="w-full flex justify-between items-center">
          <h1 className="text-2xl font-semibold text-black dark:text-white">
            Notes
          </h1>
          <div className="flex items-center gap-4">
            {user && (
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                {user.email}
              </span>
            )}
            <button
              onClick={handleSignOut}
              className="text-sm text-red-600 hover:underline"
            >
              Sign out
            </button>
          </div>
        </div>

        {error && (
          <div className="w-full p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter your message..."
            className="px-4 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-600 dark:text-white"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-colors"
          >
            {loading ? "Posting..." : "Post Note"}
          </button>
        </form>

        <button
          onClick={fetchMessages}
          disabled={loadingMessages}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-green-400 transition-colors w-full"
        >
          {loadingMessages ? "Loading..." : "Refresh Notes"}
        </button>

        {messages?.length > 0 && (
          <div className="w-full mt-4">
            <h2 className="text-lg font-semibold text-black dark:text-white mb-2">
              Your Notes
            </h2>
            <ul className="space-y-2">
              {messages.map((msg) => (
                <li
                  key={msg.id}
                  className="relative overflow-hidden rounded-lg"
                  onTouchStart={(e) => handleSwipeStart(msg.id, e.touches[0].clientX)}
                  onTouchMove={(e) => handleSwipeMove(msg.id, e.touches[0].clientX)}
                  onTouchEnd={() => handleSwipeEnd(msg.id)}
                  onMouseDown={(e) => handleSwipeStart(msg.id, e.clientX)}
                  onMouseMove={(e) => swiping === msg.id && handleSwipeMove(msg.id, e.clientX)}
                  onMouseUp={() => handleSwipeEnd(msg.id)}
                  onMouseLeave={() => swiping === msg.id && handleSwipeEnd(msg.id)}
                >
                  <div className="absolute inset-y-0 right-0 bg-red-500 flex items-center px-4">
                    <span className="text-white font-medium">Delete</span>
                  </div>
                  <div
                    className="relative bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 p-3 rounded-lg flex justify-between items-start transition-transform"
                    style={{ transform: `translateX(${swipeOffset[msg.id] || 0}px)` }}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-black dark:text-white break-words">{msg.message}</p>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                        {msg.created_at}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDelete(msg.id)}
                      className="ml-3 text-red-500 hover:text-red-700 text-lg font-bold flex-shrink-0"
                      aria-label="Delete message"
                    >
                      ✕
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages?.length === 0 && !loadingMessages && (
          <p className="text-zinc-600 dark:text-zinc-400">
            No notes yet. Post your first note!
          </p>
        )}
      </main>
    </div>
  );
}
