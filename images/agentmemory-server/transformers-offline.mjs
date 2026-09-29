import { env } from "@huggingface/transformers";

// AgentMemory imports Transformers.js dynamically. Configure the singleton
// before that import so the provider can only read the image-bundled model.
env.localModelPath = process.env.TRANSFORMERS_MODEL_PATH || "/opt/agentmemory/models";
env.cacheDir = process.env.TRANSFORMERS_CACHE_DIR || "/opt/agentmemory/transformers-cache";
env.allowLocalModels = true;
env.allowRemoteModels = false;
env.useFS = true;
env.useFSCache = true;
