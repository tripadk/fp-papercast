import type {
  ActiveRecallItem,
  ChatMessage,
  ConfusionStatusResponse,
  ConfusionStatusUpdatePayload,
  KnowledgeGraphResponse,
  LearningEfficiencyResponse,
  LearningEfficiencyUpdatePayload,
  LearningInteractionRequest,
  LearningNextActionRequest,
  LearningNextActionResponse,
  LearningStateResponse,
  NextModeResponse,
  PaperHistoryItem,
  LearningMode,
  OutputLanguage,
  PodcastLength,
  PodcastStyle,
  StudyGoal,
  StoredChatHistory,
  SimplifiedExplanationResult,
  UploadResult,
  UserGoalResponse,
  UserProfile,
  UserProfileUpdatePayload,
} from "./types";

const BACKEND_BASE_URL = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "");

function backendUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BACKEND_BASE_URL}${normalizedPath}`;
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

    const response = await fetch(backendUrl("/papers/upload"), {
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
  const response = await fetch(backendUrl("/chat/ask"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ paper_id: paperId, question, history })
  });

  if (!response.ok) {
    throw new Error(`Q&A failed: ${await readErrorMessage(response)}`);
  }

  return response.json();
}

export async function fetchTranscript(transcriptPath: string) {
  const response = await fetch(backendUrl(transcriptPath));

  if (!response.ok) {
    throw new Error(`Transcript failed: ${await readErrorMessage(response)}`);
  }

  return response.text();
}

export async function fetchPaperHistory(userEmail: string) {
  const response = await fetch(backendUrl(`/papers/history?user_email=${encodeURIComponent(userEmail)}`));
  if (!response.ok) {
    throw new Error(`History failed: ${await readErrorMessage(response)}`);
  }
  const payload = (await response.json()) as { papers: PaperHistoryItem[] };
  return payload.papers;
}

export async function fetchPaperDetail(paperId: string, userEmail = "") {
  const query = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : "";
  const response = await fetch(backendUrl(`/papers/${paperId}${query}`));
  if (!response.ok) {
    throw new Error(`Paper load failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UploadResult>;
}

export async function fetchContentStatus(contentId: string) {
  const response = await fetch(backendUrl(`/papers/status/${encodeURIComponent(contentId)}`));
  if (!response.ok) {
    throw new Error(`Status fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UploadResult>;
}

export async function explainPaperLikeIm12(paperId: string) {
  const response = await fetch(backendUrl(`/papers/${paperId}/explain-like-im-12`), {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Simple explanation failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<SimplifiedExplanationResult>;
}

export async function fetchActiveRecall(paperId: string, userEmail: string) {
  const response = await fetch(
    backendUrl(`/revision/active-recall/paper/${encodeURIComponent(paperId)}?user_email=${encodeURIComponent(userEmail)}`)
  );
  if (!response.ok) {
    throw new Error(`Active recall fetch failed: ${await readErrorMessage(response)}`);
  }
  const payload = (await response.json()) as { items: ActiveRecallItem[] };
  return payload.items ?? [];
}

export async function submitActiveRecallAttempt(params: {
  userEmail: string;
  paperId: string;
  topic: string;
  isCorrect: boolean;
}) {
  const response = await fetch(backendUrl("/revision/active-recall/attempt"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_email: params.userEmail,
      paper_id: params.paperId,
      topic: params.topic,
      is_correct: params.isCorrect,
    }),
  });
  if (!response.ok) {
    throw new Error(`Active recall submit failed: ${await readErrorMessage(response)}`);
  }
}

export async function fetchChatHistory(paperId: string) {
  const response = await fetch(backendUrl(`/chat/history/${paperId}`));
  if (!response.ok) {
    throw new Error(`Chat history failed: ${await readErrorMessage(response)}`);
  }
  const payload = (await response.json()) as { messages: StoredChatHistory[] };
  return payload.messages;
}

export async function fetchUserProfile(userEmail: string, name = "", profileImage = "") {
  const response = await fetch(
    backendUrl(`/user/profile?user_email=${encodeURIComponent(userEmail)}&name=${encodeURIComponent(name)}&profile_image=${encodeURIComponent(profileImage)}`)
  );
  if (!response.ok) {
    throw new Error(`Profile load failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UserProfile>;
}

export async function updateUserProfile(payload: UserProfileUpdatePayload) {
  const response = await fetch(backendUrl("/user/profile/update"), {
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

export async function fetchUserGoal(userId: string) {
  const response = await fetch(backendUrl(`/user/${encodeURIComponent(userId)}/goal`));
  if (!response.ok) {
    throw new Error(`Goal load failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UserGoalResponse>;
}

export async function updateUserGoal(userId: string, goal: StudyGoal) {
  const response = await fetch(backendUrl(`/user/${encodeURIComponent(userId)}/goal`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
  if (!response.ok) {
    throw new Error(`Goal update failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<UserGoalResponse>;
}

export async function fetchKnowledgeGraph(contentId: string) {
  const response = await fetch(backendUrl(`/papers/${encodeURIComponent(contentId)}/knowledge-graph`));
  if (!response.ok) {
    throw new Error(`Knowledge graph fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<KnowledgeGraphResponse>;
}

export async function fetchNextMode(contentId: string, payload: LearningInteractionRequest) {
  const response = await fetch(backendUrl(`/content/${encodeURIComponent(contentId)}/next-mode`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Next mode fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<NextModeResponse>;
}

export async function fetchConfusionStatus(contentId: string, userEmail: string) {
  const response = await fetch(
    backendUrl(`/content/${encodeURIComponent(contentId)}/confusion-status?user_email=${encodeURIComponent(userEmail)}`)
  );
  if (!response.ok) {
    throw new Error(`Confusion status fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<ConfusionStatusResponse>;
}

export async function updateConfusionStatus(contentId: string, payload: ConfusionStatusUpdatePayload) {
  const response = await fetch(backendUrl(`/content/${encodeURIComponent(contentId)}/confusion-status`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Confusion status update failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<ConfusionStatusResponse>;
}

export async function fetchLearningEfficiency(userId: string) {
  const response = await fetch(backendUrl(`/user/${encodeURIComponent(userId)}/learning-efficiency`));
  if (!response.ok) {
    throw new Error(`Learning efficiency fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<LearningEfficiencyResponse>;
}

export async function updateLearningEfficiency(userId: string, payload: LearningEfficiencyUpdatePayload) {
  const response = await fetch(backendUrl(`/user/${encodeURIComponent(userId)}/learning-efficiency`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Learning efficiency update failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<LearningEfficiencyResponse>;
}

export async function fetchLearningState(userId: string) {
  const response = await fetch(backendUrl(`/learning-state/${encodeURIComponent(userId)}`));
  if (!response.ok) {
    throw new Error(`Learning state fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<LearningStateResponse>;
}

export async function fetchLearningNextAction(payload: LearningNextActionRequest) {
  const response = await fetch(backendUrl("/learning/next-action"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Learning next-action fetch failed: ${await readErrorMessage(response)}`);
  }
  return response.json() as Promise<LearningNextActionResponse>;
}

async function readErrorMessage(response: Response) {
  const rawText = await response.text();
  if (!rawText) {
    return `${response.status} ${response.statusText}`.trim();
  }

  try {
    const parsed = JSON.parse(rawText) as { detail?: string };
    return parsed.detail ?? rawText;
  } catch {
    return rawText;
  }
}
