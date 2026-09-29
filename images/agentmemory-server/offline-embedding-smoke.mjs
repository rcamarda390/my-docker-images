import { env, pipeline } from "@huggingface/transformers";

const modelId = "Xenova/all-MiniLM-L6-v2";
const expectedDimension = 384;

if (env.allowRemoteModels !== false) {
  throw new Error("Transformers.js remote model loading is not disabled");
}

const extractor = await pipeline("feature-extraction", modelId, { dtype: "q8" });
const output = await extractor(["air-gapped AgentMemory local embedding test"], {
  pooling: "mean",
  normalize: true,
});
const vectors = output.tolist();

if (vectors.length !== 1 || vectors[0].length !== expectedDimension) {
  throw new Error(
    `Unexpected embedding shape: ${JSON.stringify(output.dims)}; expected [1, ${expectedDimension}]`,
  );
}

console.log(
  `offline local embedding OK: model=${modelId} dimensions=${vectors[0].length} remote_models=${env.allowRemoteModels}`,
);
