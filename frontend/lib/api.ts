import type {
  ChatMessage,
  ChatResponse,
  LearningInsightsResponse,
  PaperHistoryItem,
  PodcastLength,
  PodcastResponse,
  PodcastStyle,
  SimplifiedExplanationResult,
  StudyGoal,
  UploadResult,
  UserProfile,
  UserProfileUpdatePayload,
  LearningMode,
  OutputLanguage,
} from "./types";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "https://fp-papercast.onrender.com").replace(/\/+$/, "");
const PAPERS_PREFIX = "/api/v1/papers";
const USER_PREFIX = "/user";

export function api(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_URL}${normalizedPath}`;
}

export async function uploadPaper(
  file: File,
  options: {
    podcastLength: PodcastLength;
    podcastStyle: PodcastStyle;
    studyGoal: StudyGoal;
    learningMode: LearningMode;
    outputLanguage: OutputLanguage;
    userEmail: string;
  }
) {
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("podcast_length", options.podcastLength);
    formData.append("podcast_style", options.podcastStyle);
    formData.append("study_goal", options.studyGoal);
    formData.append("learning_mode", options.learningMode);
    formData.append("output_language", options.outputLanguage);
    formData.append("user_email", options.userEmail || "anonymous@local");

    const response = await fetch(api(`${PAPERS_PREFIX}/upload`), {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${await readErrorMessage(response)}`);
    }

    return (await response.json()) as UploadResult;
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Upload failed due to an unexpected client error.");
  }
}

export async function askPaperQuestion(paperId: string, question: string, history: ChatMessage[]) {
  const response = await fetch(api("/api/v1/chat"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ paper_id: paperId, question, history }),
  });

  if (!response.ok) {
    throw new Error(`Q&A failed: ${await readErrorMessage(response)}`);
  }

  return (await response.json()) as ChatResponse;
}

export async function generatePodcast(payload: { paperId?: string; paperContent?: string }) {
  const response = await fetch(api("/api/v1/podcast"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      paper_id: payload.paperId ?? "",
      paper_content: payload.paperContent ?? "",
    }),
  });

  if (!response.ok) {
    throw new Error(`Podcast generation failed: ${await readErrorMessage(response)}`);
  }

  return (await response.json()) as PodcastResponse;
}

export async function fetchLearningInsights(userEmail: string) {
  const response = await fetch(api(`/api/v1/learning-insights?user_email=${encodeURIComponent(userEmail)}`));
  if (!response.ok) {
    throw new Error(`Learning insights failed: ${await readErrorMessage(response)}`);
  }
  return (await response.json()) as LearningInsightsResponse;
}

export async function fetchTranscript(transcriptPath: string) {
  const response = await fetch(api(transcriptPath));

  if (!response.ok) {
    throw new Error(`Transcript failed: ${await readErrorMessage(response)}`);
  }

  return response.text();
}

export async function fetchPaperHistory(userEmail: string) {
  const response = await fetch(api(`${PAPERS_PREFIX}/history?user_email=${encodeURIComponent(userEmail)}`));
  if (!response.ok) {
    throw new Error(`History failed: ${await readErrorMessage(response)}`);
  }
  const payload = (await response.json()) as { papers: PaperHistoryItem[] };
  return payload.papers;
}

export async function fetchPaperDetail(paperId: string, userEmail = "") {
  const query = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : "";
  const response = await fetch(api(`${PAPERS_PREFIX}/${paperId}${query}`));
  if (!response.ok) {
    throw new Error(`Paper load failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UploadResult>;
}

export async function fetchContentStatus(contentId: string) {
  const response = await fetch(api(`${PAPERS_PREFIX}/status/${encodeURIComponent(contentId)}`));
  if (!response.ok) {
    throw new Error(`Status fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UploadResult>;
}

export async function explainPaperLikeIm12(paperId: string) {
  const response = await fetch(api(`${PAPERS_PREFIX}/${paperId}/explain-like-im-12`), {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Simple explanation failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<SimplifiedExplanationResult>;
}

export async function fetchUserProfile(userEmail: string, name = "", profileImage = "") {
  const response = await fetch(
    api(`${USER_PREFIX}/profile?user_email=${encodeURIComponent(userEmail)}&name=${encodeURIComponent(name)}&profile_image=${encodeURIComponent(profileImage)}`)
  );
  if (!response.ok) {
    throw new Error(`Profile load failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UserProfile>;
}

export async function updateUserProfile(payload: UserProfileUpdatePayload) {
  const response = await fetch(api(`${USER_PREFIX}/profile/update`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Profile update failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UserProfile>;
}

async function readErrorMessage(response: Response) {
  const rawText = await response.text();
  if (!rawText) {
    return `${response.status} ${response.statusText}`.trim();
  }

  try {
    const parsed = JSON.parse(rawText) as { detail?: string; error?: string };
    return parsed.detail ?? parsed.error ?? rawText;
  } catch {
    return rawText;
  }
}
