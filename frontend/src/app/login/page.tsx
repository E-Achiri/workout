"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signIn, signUp, confirmSignUp } from "@/lib/auth";

type AuthMode = "signin" | "signup" | "confirm";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmCode, setConfirmCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await signIn({ email, password });
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await signUp({ email, password });
      setMode("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await confirmSignUp({ email, code: confirmCode });
      // After confirmation, sign in automatically
      await signIn({ email, password });
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirmation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
      <main className="flex flex-col items-center gap-8 p-8 w-full max-w-md">
        <h1 className="text-2xl font-semibold text-black dark:text-white">
          {mode === "signin" && "Sign In"}
          {mode === "signup" && "Sign Up"}
          {mode === "confirm" && "Confirm Email"}
        </h1>

        {error && (
          <div className="w-full p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {mode === "signin" && (
          <form onSubmit={handleSignIn} className="flex flex-col gap-4 w-full">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              className="px-4 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-600 dark:text-white"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              className="px-4 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-600 dark:text-white"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-colors"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        )}

        {mode === "signup" && (
          <form onSubmit={handleSignUp} className="flex flex-col gap-4 w-full">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              className="px-4 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-600 dark:text-white"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password (8+ chars, upper, lower, number)"
              required
              minLength={8}
              className="px-4 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-600 dark:text-white"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-green-400 transition-colors"
            >
              {loading ? "Signing up..." : "Sign Up"}
            </button>
          </form>
        )}

        {mode === "confirm" && (
          <form onSubmit={handleConfirm} className="flex flex-col gap-4 w-full">
            <p className="text-zinc-600 dark:text-zinc-400 text-center">
              We sent a confirmation code to {email}
            </p>
            <input
              type="text"
              value={confirmCode}
              onChange={(e) => setConfirmCode(e.target.value)}
              placeholder="Confirmation code"
              required
              className="px-4 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-600 dark:text-white"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-colors"
            >
              {loading ? "Confirming..." : "Confirm"}
            </button>
          </form>
        )}

        <div className="text-zinc-600 dark:text-zinc-400">
          {mode === "signin" && (
            <button
              onClick={() => setMode("signup")}
              className="text-blue-600 hover:underline"
            >
              Don&apos;t have an account? Sign up
            </button>
          )}
          {(mode === "signup" || mode === "confirm") && (
            <button
              onClick={() => setMode("signin")}
              className="text-blue-600 hover:underline"
            >
              Already have an account? Sign in
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
