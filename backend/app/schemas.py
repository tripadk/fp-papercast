from pydantic import BaseModel, Field


class RelatedPaper(BaseModel):
    title: str
    authors: str
    summary: str
    link: str


class PodcastChapter(BaseModel):
    time: str
    title: str


class TranscriptSentence(BaseModel):
    time: str
    start_seconds: float
    text: str


class StudyNotes(BaseModel):
    core_idea: str
    key_concepts: str
    key_points: str
    important_results: str
    limitations: str
    applications: str
    quick_revision: str


class ImportanceExtraction(BaseModel):
    must_know: list[str]
    important: list[str]
    optional: list[str]


class KnowledgeDependency(BaseModel):
    source: str
    target: str
    relation: str


class KnowledgeTopic(BaseModel):
    name: str
    subtopics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    concept_items: list[dict[str, str | list[str]]] = Field(default_factory=list)
    dependencies: list[KnowledgeDependency] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    difficulty_level: str = "medium"


class KnowledgeGraph(BaseModel):
    topics: list[KnowledgeTopic] = Field(default_factory=list)


class UploadResponse(BaseModel):
    paper_id: str
    summary: str
    transcript_path: str
    audio_path: str
    audio_url: str | None = None
    audio_ready: bool = False
    transcript_download_url: str
    podcast_script_download_url: str
    notes_download_url: str
    podcast_length: str
    podcast_style: str
    study_goal: str
    learning_mode: str
    quiz_difficulty: str = "medium"
    output_language: str
    chapters: list[PodcastChapter]
    transcript_sentences: list[TranscriptSentence]
    methodology_steps: list[str]
    mermaid_diagram: str
    related_papers: list[RelatedPaper]
    top_citations: list[str]
    study_notes: StudyNotes
    importance_extraction: ImportanceExtraction
    knowledge_graph: KnowledgeGraph = Field(default_factory=KnowledgeGraph)
    knowledge_navigation: list[dict[str, str | int | list[str]]] = Field(default_factory=list)
    learning_path: list[dict[str, str | list[str] | dict[str, list[str]]]] = Field(default_factory=list)
    task_status: dict[str, str] = Field(default_factory=dict)
    processing_status: list[str] = Field(default_factory=list)


class PaperHistoryItem(BaseModel):
    paper_id: str
    user_email: str
    paper_title: str
    upload_timestamp: str
    summary: str
    audio_url: str


class PaperHistoryResponse(BaseModel):
    papers: list[PaperHistoryItem]


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    paper_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str


class ChatHistoryItem(BaseModel):
    paper_id: str
    user_message: str
    assistant_response: str
    timestamp: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryItem]


class UserProfileResponse(BaseModel):
    user_email: str
    name: str
    email: str
    institution: str
    bio: str
    profile_image: str = ""
    goal: str = "general"


class UserProfileUpdateRequest(BaseModel):
    user_email: str = Field(..., min_length=3)
    name: str = ""
    institution: str = ""
    bio: str = ""
    profile_image: str = ""
    goal: str = ""


class UserGoalUpdateRequest(BaseModel):
    goal: str = Field(..., pattern="^(upsc|jee|neet|cat|general)$")


class UserGoalResponse(BaseModel):
    user_id: str
    goal: str = "general"


class SimplifiedExplanationResponse(BaseModel):
    paper_id: str
    explanation: str


class UnifiedContent(BaseModel):
    id: str
    title: str
    raw_text: str
    source_type: str
    created_at: str


class IngestContentResponse(BaseModel):
    content: UnifiedContent
    analysis: UploadResponse


class KnowledgeGraphResponse(BaseModel):
    content_id: str
    knowledge_graph: KnowledgeGraph = Field(default_factory=KnowledgeGraph)
    knowledge_navigation: list[dict[str, str | int | list[str]]] = Field(default_factory=list)
    learning_path: list[dict[str, str | list[str] | dict[str, list[str]]]] = Field(default_factory=list)


class LearningInteractionRequest(BaseModel):
    user_email: str = Field(..., min_length=3)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    time_spent: int = Field(..., ge=0)
    engagement: float = Field(..., ge=0.0, le=1.0)


class NextModeResponse(BaseModel):
    content_id: str
    user_email: str
    previous_mode: str
    current_mode: str
    reason: str
    concept_id: str = ""
    concept: str = ""
    difficulty: str = "medium"
    repeated_mistakes: bool = False
    recommendations: list[str] = Field(default_factory=list)


class LearningEfficiencyUpdateRequest(BaseModel):
    topic: str = Field(..., min_length=2)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    time_spent: int = Field(..., ge=0)
    attempts: int = Field(..., ge=0)


class LearningEfficiencyTopicItem(BaseModel):
    concept_id: str = ""
    topic: str
    time_spent: int
    quiz_accuracy: float
    attempts: int
    completion_rate: float
    learning_efficiency_score: float
    difficulty_adjustment: str
    priority: str
    updated_at: str


class LearningEfficiencyResponse(BaseModel):
    user_id: str
    average_learning_efficiency_score: float
    prioritized_topics: list[LearningEfficiencyTopicItem] = Field(default_factory=list)
    updated_at: str


class ConfusionInteractionRequest(BaseModel):
    user_email: str = Field(..., min_length=3)
    topic: str = Field(..., min_length=2)
    question: str = ""
    is_correct: bool
    response_time_seconds: float = Field(..., ge=0.0)


class ConfusionActions(BaseModel):
    simpler_explanation: str = ""
    real_life_example: str = ""
    step_by_step_breakdown: list[str] = Field(default_factory=list)


class ConfusionSignals(BaseModel):
    repeated_wrong_answers: bool = False
    repeated_similar_questions: bool = False
    long_response_time: bool = False


class ConfusionTopicItem(BaseModel):
    concept_id: str = ""
    topic: str
    topic_status: str = "clear"
    signals: ConfusionSignals = Field(default_factory=ConfusionSignals)
    wrong_answer_count: int = 0
    similar_question_count: int = 0
    long_response_count: int = 0
    actions: ConfusionActions = Field(default_factory=ConfusionActions)
    updated_at: str = ""


class ConfusionStatusResponse(BaseModel):
    content_id: str
    user_email: str
    topics: list[ConfusionTopicItem] = Field(default_factory=list)


class TopicGoalAdaptation(BaseModel):
    goal: str = "general"
    style: str = ""
    level: str = "simplified"


class TopicLearningStateItem(BaseModel):
    concept_id: str = ""
    topic: str
    content_id: str = ""
    mastery_level: float
    confusion_level: float
    retention_score: float
    priority: str
    attempts: int = 0
    accuracy: float = 0.0
    next_mode_hint: str = "notes"
    goal_adaptation: TopicGoalAdaptation = Field(default_factory=TopicGoalAdaptation)
    prerequisites: list[str] = Field(default_factory=list)
    difficulty_level: str = "medium"
    reassessment_due_at: str = ""


class LearningStateResponse(BaseModel):
    user_id: str
    goal: str = "general"
    topics: list[TopicLearningStateItem] = Field(default_factory=list)
    updated_at: str


class RecentActivityInput(BaseModel):
    last_mode: str = ""
    avg_response_time_seconds: float = Field(default=0.0, ge=0.0)
    recent_correct_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    sessions_last_7_days: int = Field(default=0, ge=0)


class LearningNextActionRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    recent_activity: RecentActivityInput = Field(default_factory=RecentActivityInput)


class TopicStateSnapshot(BaseModel):
    mastery_level: float
    confusion_level: float
    retention_score: float
    priority: str


class LearningNextActionResponse(BaseModel):
    user_id: str
    goal: str = "general"
    concept_id: str = ""
    next_topic: str
    next_mode: str
    difficulty_level: str
    quiz_difficulty: str = "medium"
    rationale: list[str] = Field(default_factory=list)
    topic_state: TopicStateSnapshot
    recent_activity: RecentActivityInput = Field(default_factory=RecentActivityInput)


class TopicViewRequest(BaseModel):
    user_email: str = Field(..., min_length=3)
    topic: str = Field(..., min_length=2)
    paper_id: str = ""
    confidence: int = Field(default=3, ge=1, le=5)
    source: str = "manual"


class WeakAreaRequest(BaseModel):
    user_email: str = Field(..., min_length=3)
    concept: str = Field(..., min_length=2)
    paper_id: str = ""
    reason: str = ""
    severity: int = Field(default=3, ge=1, le=5)


class RevisionItem(BaseModel):
    concept: str
    score: float
    reason: str
    paper_id: str = ""


class FlashcardItem(BaseModel):
    concept: str
    question: str
    answer: str
    hint: str = ""
    paper_id: str = ""


class DailyRevisionResponse(BaseModel):
    user_email: str
    generated_at: str
    items: list[RevisionItem]


class FlashcardsResponse(BaseModel):
    user_email: str
    generated_at: str
    cards: list[FlashcardItem]


class ActiveRecallItem(BaseModel):
    id: str
    topic: str
    prompt: str
    answer: str
    paper_id: str = ""


class ActiveRecallResponse(BaseModel):
    paper_id: str
    user_email: str
    generated_at: str
    items: list[ActiveRecallItem]


class RecallAttemptRequest(BaseModel):
    user_email: str = Field(..., min_length=3)
    paper_id: str = ""
    topic: str = Field(..., min_length=2)
    is_correct: bool


class RecallPerformanceItem(BaseModel):
    topic: str
    paper_id: str = ""
    correct: int
    incorrect: int
    last_attempt: str


class RecallPerformanceResponse(BaseModel):
    user_email: str
    items: list[RecallPerformanceItem]


class RevisionScheduleUpdateRequest(BaseModel):
    user_email: str = Field(..., min_length=3)
    topic: str = Field(..., min_length=2)
    is_correct: bool
    paper_id: str = ""
    accuracy: float | None = Field(default=None, ge=0.0, le=1.0)


class RevisionScheduleItem(BaseModel):
    concept_id: str = ""
    topic: str
    paper_id: str = ""
    interval_days: int
    next_review_date: str
    last_reviewed_at: str = ""
    accuracy_snapshot: float = 0.0
    total_reviews: int = 0
    correct_reviews: int = 0
    is_due: bool = False


class RevisionScheduleResponse(BaseModel):
    user_email: str
    generated_at: str
    items: list[RevisionScheduleItem] = Field(default_factory=list)


class TopicMemoryItem(BaseModel):
    concept_id: str = ""
    topic: str
    paper_id: str = ""
    count: int = 0
    sources: list[str] = Field(default_factory=list)
    last_seen: str = ""


class QuizPerformanceSummaryItem(BaseModel):
    concept_id: str = ""
    topic: str
    paper_id: str = ""
    attempts: int = 0
    correct: int = 0
    incorrect: int = 0
    accuracy: float = 0.0
    last_attempt: str = ""


class WeakTopicItem(BaseModel):
    concept_id: str = ""
    concept: str
    paper_id: str = ""
    severity: float = 0.0
    reason: str = ""
    last_seen: str = ""


class StrongTopicItem(BaseModel):
    concept_id: str = ""
    concept: str
    paper_id: str = ""
    confidence: float = 0.0
    reason: str = ""
    last_seen: str = ""


class UserLearningMemoryResponse(BaseModel):
    user_email: str
    topics_studied: list[TopicMemoryItem]
    quiz_performance: list[QuizPerformanceSummaryItem]
    weak_topics: list[WeakTopicItem]
    strong_topics: list[StrongTopicItem]
    updated_at: str


class LearnerEventItem(BaseModel):
    user_id: str
    content_id: str = ""
    concept_id: str = ""
    topic: str = ""
    event_type: str = Field(..., pattern="^(quiz|chat|recall|mode_switch|intervention)$")
    timestamp: str
    correctness: bool | None = None
    response_time: float | None = None
    mode_used: str = ""
    metadata: dict[str, str | float | int | bool | None] = Field(default_factory=dict)


class LearnerEventTopicHistoryItem(BaseModel):
    concept_id: str = ""
    topic: str
    attempts: int = 0
    accuracy: float = 0.0
    last_interaction: str = ""


class LearnerEventSummary(BaseModel):
    user_id: str
    total_events: int = 0
    events_by_type: dict[str, int] = Field(default_factory=dict)
    overall_accuracy: float = 0.0
    recent_accuracy: float = 0.0
    previous_accuracy: float = 0.0
    improvement_delta: float = 0.0
    topic_history: list[LearnerEventTopicHistoryItem] = Field(default_factory=list)
    updated_at: str


class LearnerEventsResponse(BaseModel):
    user_id: str
    events: list[LearnerEventItem] = Field(default_factory=list)
    summary: LearnerEventSummary
    outcomes: dict[str, list[dict[str, str | float]]] = Field(default_factory=dict)
