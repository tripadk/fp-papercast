# Backend Logic Fix TODO

## Plan Steps (Approved by User)

### Phase 1: Create New Services
- [ ] 1.1 Create `services/llm_utils.py` (shared Groq caller)
- [ ] 1.2 Create `services/chat_service.py`
- [ ] 1.3 Overwrite `services/podcast_service.py` (LLM version)
- [ ] 1.4 Create `services/learning_service.py`

### Phase 2: Update Routers
- [ ] 2.1 Simplify `routers/chat.py`
- [ ] 2.2 Update `routers/learning_state.py` (add LLM insights)
- [ ] 2.3 Create `routers/podcast.py`
- [ ] 2.4 Update `routers/__init__.py` (import podcast)
- [ ] 2.5 Update `main.py` (include_router)

### Phase 3: Test & Verify
- [ ] 3.1 Test chat endpoint
- [ ] 3.2 Test learning-state
- [ ] 3.3 Test podcast
- [ ] 3.4 Check no crashes/logs/JSON

**Current Progress: Phase 1**

Updated: None yet

