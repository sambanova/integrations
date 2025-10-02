import {createOpenAI} from '@ai-sdk/openai';
import {createAiGateway} from 'ai-gateway-provider';
import {generateText} from "ai";
import {createSambaNova} from 'sambanova-ai-provider';
import {createCerebras} from '@ai-sdk/cerebras';


//npm install sambanova-ai-provider
//npm install ai-gateway-provider
//npm install @ai-sdk/openai
//npm install @ai-sdk/cerebras

const aigateway = createAiGateway({
  accountId: "da0eb50826b24813cfc22c880931da65",
  gateway: 'test',
//   apiKey: 'optionally my cloudflare api key',
//   options: {  // Optional per-request override
//     skipCache: true
//   }
});

// using cerebras provider

cerebras_api_key = ''

const cerebras = createCerebras({
    apiKey: cerebras_api_key
});

const cerebras2 = createCerebras({
    apiKey: cerebras_api_key
});

const model = aigateway([
  cerebras('llama3.1-8b'),  // Primary choice
  cerebras2("llama-4-scout-17b-16e-instruct"),                   // Fallback if first failsapiKey
]);

// using sambanova provider

// sambanova_api_key = ''

// const sambanova = createSambaNova({
//     apiKey: sambanova_api_key
// });

// const sambanova2 = createSambaNova({
//     apiKey: sambanova_api_key
// });

// const model = aigateway([
//   sambanova('DeepSeek-V3-0324'),  // Primary choice
//   sambanova2("DeepSeek-V3.1-Terminus"),                   // Fallback if first failsapiKey
// ]);


// using openai provider as proxy

// const sambanova = createOpenAI({
//     baseURL: 'https://api.sambanova.ai/v1',
//     apiKey: sambanova_api_key
// });

// const sambanova2 = createOpenAI({
//     baseURL: 'https://api.sambanova.ai/v1',
//     apiKey: sambanova_api_key
// });

// const model = aigateway([
//   sambanova('DeepSeek-V3-0324'),  // Primary choice
//   sambanova2("DeepSeek-V3.1-Terminus"),                   // Fallback if first failsapiKey
// ]);

// using openai provider

// openai_api_key = ''

// const openai = createOpenAI({
//     apiKey: openai_api_key
// });

// const openai2 = createOpenAI({
//     apiKey: openai_api_key
// });

// const model = aigateway([
//   openai('gpt-4.1'),  // Primary choice
//   openai2("gpt-4o"),                   // Fallback if first failsapiKey
// ]);

const {text} = await generateText({
  model: model,
  prompt: 'Write a vegetarian lasagna recipe for 4 people.',
});

console.log(text);  