"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession, signIn } from "next-auth/react";
import { Loader2, PencilLine, Save, UserCircle2, X } from "lucide-react";
import { fetchUserGoal, fetchUserProfile, updateUserGoal, updateUserProfile } from "@/lib/api";
import { toUserId } from "@/lib/user-id";
import type { StudyGoal, UserProfile } from "@/lib/types";

type FormState = {
  name: string;
  institution: string;
  bio: string;
  goal: StudyGoal;
};

export default function ProfilePage() {
  const { data: session, status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [form, setForm] = useState<FormState>({ name: "", institution: "", bio: "", goal: "general" });
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ready = useMemo(() => status === "authenticated" && !!session, [session, status]);
  const userEmail = session?.user?.email ?? "";
  const userId = useMemo(() => toUserId(userEmail), [userEmail]);
  const sessionName = session?.user?.name ?? "";
  const sessionImage = session?.user?.image ?? "";

  useEffect(() => {
    if (!ready || !userEmail) return;

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    fetchUserProfile(userEmail, sessionName, sessionImage)
      .then((payload) => {
        if (cancelled) return;
        setProfile(payload);
        const defaultGoal: StudyGoal = (payload.goal as StudyGoal) ?? "general";
        setForm({
          name: payload.name ?? "",
          institution: payload.institution ?? "",
          bio: payload.bio ?? "",
          goal: defaultGoal,
        });
        return fetchUserGoal(userId);
      })
      .then((goalPayload) => {
        if (!cancelled && goalPayload?.goal) {
          setForm((prev) => ({ ...prev, goal: goalPayload.goal }));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load profile.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ready, userEmail, userId, sessionName, sessionImage]);

  if (status === "loading") {
    return (
      <main className="app-shell">
        <section className="glass-card p-10 text-center">
          <p className="text-sm text-slate-200">Loading profile...</p>
        </section>
      </main>
    );
  }

  if (!ready) {
    return (
      <main className="app-shell">
        <section className="glass-card mx-auto max-w-xl p-10 text-center">
          <h2 className="text-3xl font-semibold text-white">Sign in required</h2>
          <p className="mt-3 text-sm text-slate-300">Please sign in to view and edit your profile.</p>
          <button className="btn-primary mt-6" onClick={() => signIn("google", { callbackUrl: "/profile" })}>
            Sign in with Google
          </button>
        </section>
      </main>
    );
  }

  const image = profile?.profile_image || sessionImage;

  return (
    <main className="app-shell">
      <section className="glass-card mx-auto max-w-3xl rounded-xl p-6 shadow sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-white">User Profile</h1>
            <p className="mt-1 text-sm text-slate-300">Manage your PaperCast account details.</p>
          </div>
          {!isEditing ? (
            <button type="button" className="btn-secondary" onClick={() => setIsEditing(true)}>
              <PencilLine className="h-4 w-4" />
              Edit Profile
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setIsEditing(false);
                  setMessage(null);
                  setError(null);
                  if (profile) {
                    setForm({
                      name: profile.name ?? "",
                      institution: profile.institution ?? "",
                      bio: profile.bio ?? "",
                      goal: (profile.goal as StudyGoal) ?? "general",
                    });
                  }
                }}
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={async () => {
                  if (!userEmail) return;
                  setIsSaving(true);
                  setMessage(null);
                  setError(null);
                  try {
                    const updated = await updateUserProfile({
                      user_email: userEmail,
                      name: form.name,
                      institution: form.institution,
                      bio: form.bio,
                      profile_image: profile?.profile_image ?? sessionImage ?? "",
                    });
                    await updateUserGoal(userId, form.goal);
                    setProfile(updated);
                    setForm({
                      name: updated.name,
                      institution: updated.institution,
                      bio: updated.bio,
                      goal: form.goal,
                    });
                    setIsEditing(false);
                    setMessage("Profile updated successfully.");
                  } catch (err: unknown) {
                    setError(err instanceof Error ? err.message : "Failed to update profile.");
                  } finally {
                    setIsSaving(false);
                  }
                }}
                disabled={isSaving}
              >
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Changes
              </button>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="mt-8 inline-flex items-center gap-2 text-sm text-slate-300">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading profile...
          </div>
        ) : (
          <div className="mt-8 grid gap-6 md:grid-cols-[160px_1fr]">
            <div className="rounded-xl border border-white/15 bg-white/5 p-4">
              {image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={image} alt="Profile" className="h-28 w-28 rounded-full border border-white/20 object-cover" />
              ) : (
                <div className="inline-flex h-28 w-28 items-center justify-center rounded-full border border-white/20 bg-slate-900/40 text-slate-300">
                  <UserCircle2 className="h-16 w-16" />
                </div>
              )}
              <p className="mt-3 text-xs text-slate-400">{profile?.email || userEmail}</p>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
                <label className="text-xs font-medium uppercase tracking-[0.12em] text-slate-300">Name</label>
                {isEditing ? (
                  <input
                    className="mt-2 w-full rounded-xl border border-white/15 bg-black/25 px-3 py-2 text-sm text-white outline-none focus:border-sky-300/70"
                    value={form.name}
                    onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                  />
                ) : (
                  <p className="mt-2 text-sm text-gray-100">{profile?.name || "Not set"}</p>
                )}
              </div>

              <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
                <label className="text-xs font-medium uppercase tracking-[0.12em] text-slate-300">Email</label>
                <p className="mt-2 text-sm text-gray-100">{profile?.email || userEmail}</p>
              </div>

              <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
                <label className="text-xs font-medium uppercase tracking-[0.12em] text-slate-300">Institution</label>
                {isEditing ? (
                  <input
                    className="mt-2 w-full rounded-xl border border-white/15 bg-black/25 px-3 py-2 text-sm text-white outline-none focus:border-sky-300/70"
                    value={form.institution}
                    onChange={(event) => setForm((prev) => ({ ...prev, institution: event.target.value }))}
                  />
                ) : (
                  <p className="mt-2 text-sm text-gray-100">{profile?.institution || "Not set"}</p>
                )}
              </div>

              <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
                <label className="text-xs font-medium uppercase tracking-[0.12em] text-slate-300">Learning Goal</label>
                {isEditing ? (
                  <select
                    className="mt-2 w-full rounded-xl border border-white/15 bg-black/25 px-3 py-2 text-sm text-white outline-none focus:border-sky-300/70"
                    value={form.goal}
                    onChange={(event) => setForm((prev) => ({ ...prev, goal: event.target.value as StudyGoal }))}
                  >
                    <option value="general">General</option>
                    <option value="upsc">UPSC</option>
                    <option value="jee">JEE</option>
                    <option value="neet">NEET</option>
                    <option value="cat">CAT</option>
                  </select>
                ) : (
                  <p className="mt-2 text-sm text-gray-100">{form.goal.toUpperCase()}</p>
                )}
              </div>

              <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
                <label className="text-xs font-medium uppercase tracking-[0.12em] text-slate-300">Bio</label>
                {isEditing ? (
                  <textarea
                    className="mt-2 min-h-[120px] w-full rounded-xl border border-white/15 bg-black/25 px-3 py-2 text-sm text-white outline-none focus:border-sky-300/70"
                    value={form.bio}
                    onChange={(event) => setForm((prev) => ({ ...prev, bio: event.target.value }))}
                  />
                ) : (
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-gray-100">{profile?.bio || "Not set"}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {message && <p className="mt-5 text-sm text-emerald-300">{message}</p>}
        {error && <p className="mt-5 text-sm text-rose-300">{error}</p>}
      </section>
    </main>
  );
}
