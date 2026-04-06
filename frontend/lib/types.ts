export type RelatedPaper = {
  title: string;
  authors: string;
  summary: string;
  link: string;
};

export type PodcastLength = "quick" | "standard" | "deep";
export type PodcastStyle = "casual" | "lecture" | "debate" | "news";
export type StudyGoal = "general" | "upsc" | "jee" | "neet" | "cat";
export type LearningMode = "beginner" | "exam_mode" | "deep_learning" | "quick_revision";
export type OutputLanguage = "english" | "hindi";

export type PodcastChapter = {
  time: string;
  title: string;
};

export type TranscriptSentence = {
  time: string;
  start_seconds: number;
  text: string;
};

export type StudyNotes = {
  core_idea: string;
  key_concepts: string;
  key_points: string;
  important_results: string;
  limitations: string;
  applications: string;
  quick_revision: string;
};

export type ImportanceExtraction = {
  must_know: string[];
  important: string[];
  optional: string[];
};

export type UploadResult = {
  paper_id: string;
  summary: string;
  transcript_path: string;
  audio_path: string;
  audio_ready: boolean;
  transcript_download_url: string;
  podcast_script_download_url: string;
  notes_download_url: string;
  podcast_length: PodcastLength;
  podcast_style: PodcastStyle;
  study_goal: StudyGoal;
  learning_mode: LearningMode;
  quiz_difficulty: string;
  output_language: OutputLanguage;
  chapters: PodcastChapter[];
  transcript_sentences: TranscriptSentence[];
  methodology_steps: string[];
  mermaid_diagram: string;
  related_papers: RelatedPaper[];
  top_citations: string[];
  study_notes: StudyNotes;
  importance_extraction: ImportanceExtraction;
  knowledge_graph?: KnowledgeGraph;
  knowledge_navigation?: KnowledgeNavigationItem[];
  learning_path?: LearningPathItem[];
  task_status: Record<string, string>;
  processing_status: string[];
};

export type PaperHistoryItem = {
  paper_id: string;
  user_email: string;
  paper_title: string;
  upload_timestamp: string;
  summary: string;
  audio_url: string;
};

export type ChatRequest = {
  paper_id: string;
  question: string;
  history: ChatMessage[];
};

export type ChatResponse = {
  answer: string;
};

export type PodcastRequest = {
  paper_id?: string;
  paper_content?: string;
};

export type PodcastResponse = {
  script: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type StoredChatHistory = {
  paper_id: string;
  user_message: string;
  assistant_response: string;
  timestamp: string;
};

export type UserProfile = {
  user_email: string;
  name: string;
  email: string;
  institution: string;
  bio: string;
  profile_image: string;
  goal?: StudyGoal;
};

export type UserProfileUpdatePayload = {
  user_email: string;
  name: string;
  institution: string;
  bio: string;
  profile_image?: string;
  goal?: StudyGoal | "";
};

export type SimplifiedExplanationResult = {
  paper_id: string;
  explanation: string;
};

export type ActiveRecallItem = {
  id: string;
  topic: string;
  prompt: string;
  answer: string;
  paper_id: string;
};

export type KnowledgeDependency = {
  source: string;
  target: string;
  relation: string;
};

export type KnowledgeTopic = {
  name: string;
  subtopics: string[];
  concepts: string[];
  dependencies: KnowledgeDependency[];
};

export type KnowledgeGraph = {
  topics: KnowledgeTopic[];
};

export type KnowledgeNavigationItem = {
  topic: string;
  subtopics: string[];
  concept_count: number;
};

export type LearningPathItem = {
  topic: string;
  sequence: string[];
  prerequisites: Record<string, string[]>;
};

export type KnowledgeGraphResponse = {
  content_id: string;
  knowledge_graph: KnowledgeGraph;
  knowledge_navigation: KnowledgeNavigationItem[];
  learning_path: LearningPathItem[];
};

export type UserGoalResponse = {
  user_id: string;
  goal: StudyGoal;
};

export type LearningInteractionRequest = {
  user_email: string;
  accuracy: number;
  time_spent: number;
  engagement: number;
};

export type NextModeResponse = {
  content_id: string;
  user_email: string;
  previous_mode: string;
  current_mode: string;
  reason: string;
  repeated_mistakes: boolean;
  recommendations: string[];
};

export type ConfusionSignals = {
  repeated_wrong_answers: boolean;
  repeated_similar_questions: boolean;
  long_response_time: boolean;
};

export type ConfusionActions = {
  simpler_explanation: string;
  real_life_example: string;
  step_by_step_breakdown: string[];
};

export type ConfusionTopic = {
  topic: string;
  topic_status: "clear" | "confused";
  signals: ConfusionSignals;
  wrong_answer_count: number;
  similar_question_count: number;
  long_response_count: number;
  actions: ConfusionActions;
  updated_at: string;
};

export type ConfusionStatusResponse = {
  content_id: string;
  user_email: string;
  topics: ConfusionTopic[];
};

export type ConfusionStatusUpdatePayload = {
  user_email: string;
  topic: string;
  question: string;
  is_correct: boolean;
  response_time_seconds: number;
};

export type LearningEfficiencyTopicItem = {
  topic: string;
  time_spent: number;
  quiz_accuracy: number;
  attempts: number;
  completion_rate: number;
  learning_efficiency_score: number;
  difficulty_adjustment: string;
  priority: string;
  updated_at: string;
};

export type LearningEfficiencyResponse = {
  user_id: string;
  average_learning_efficiency_score: number;
  prioritized_topics: LearningEfficiencyTopicItem[];
  updated_at: string;
};

export type LearningEfficiencyUpdatePayload = {
  topic: string;
  accuracy: number;
  time_spent: number;
  attempts: number;
};

export type TopicGoalAdaptation = {
  goal: StudyGoal;
  style: string;
  level: string;
};

export type TopicLearningState = {
  topic: string;
  mastery_level: number;
  confusion_level: number;
  retention_score: number;
  priority: string;
  attempts: number;
  accuracy: number;
  next_mode_hint: string;
  goal_adaptation: TopicGoalAdaptation;
};

export type LearningStateResponse = {
  user_id: string;
  goal: StudyGoal;
  topics: TopicLearningState[];
  updated_at: string;
};

export type LearningInsightsResponse = {
  user_email: string;
  progress_summary: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
};

export type LearningNextActionRequest = {
  user_id: string;
  recent_activity?: {
    last_mode?: string;
    avg_response_time_seconds?: number;
    recent_correct_rate?: number;
    sessions_last_7_days?: number;
  };
};

export type LearningNextActionResponse = {
  user_id: string;
  goal: StudyGoal;
  next_topic: string;
  next_mode: string;
  difficulty_level: string;
  rationale: string[];
  topic_state: {
    mastery_level: number;
    confusion_level: number;
    retention_score: number;
    priority: string;
  };
  recent_activity: {
    last_mode: string;
    avg_response_time_seconds: number;
    recent_correct_rate: number;
    sessions_last_7_days: number;
  };
};
