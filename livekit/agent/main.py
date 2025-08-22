import os

from dotenv import load_dotenv
from hume.tts import PostedUtteranceVoiceWithName

from livekit.agents import Agent, AgentSession, AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli, mcp
from livekit.plugins import elevenlabs, hume, openai, silero

load_dotenv()
SAMBANOVA_URL = os.getenv('SAMBANOVA_URL')
SAMBANOVA_API_KEY = os.getenv('SAMBANOVA_API_KEY')
SAMBANOVA_STT_MODEL = os.getenv('SAMBANOVA_STT_MODEL')
SAMBANOVA_LLM_MODEL = os.getenv('SAMBANOVA_LLM_MODEL')
TTS_PROVIDER = os.getenv('TTS_PROVIDER')


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions='You are the voice assistant named Samba, on behalf of a company called SambaNova. '
            'You can retrieve data via the MCP server.  Be nice. Your interaction with the user will via voice '
            'Expect typos in the input due to transcription but take your best guess to respond to them. '
            'SambaNova is a hardware company that has developed a new chip called the RDU (reconfigurable data flow unit) that enables fast inference for AI.'
            "They support a bunch of models including OpenAI's whisper, Meta's llama models, Qwen and DeepSeek"
        )


def prewarm(proc: JobProcess):
    proc.userdata['vad'] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    await ctx.wait_for_participant()

    if TTS_PROVIDER.lower() == 'hume':
        tts = hume.TTS(
            voice=PostedUtteranceVoiceWithName(name='Colton Rivers', provider='HUME_AI'),
            description='The voice exudes calm, serene, and peaceful qualities, like a gentle stream flowing through a quiet forest.',
        )
    elif TTS_PROVIDER.lower() == 'elevenlabs':
        tts = elevenlabs.TTS(voice_id='ODq5zmih8GrVes37Dizd', model='eleven_multilingual_v2')
    else:
        raise Exception(f'{TTS_PROVIDER} not supported')

    session = AgentSession(
        stt=openai.STT(model=SAMBANOVA_STT_MODEL, api_key=SAMBANOVA_API_KEY, base_url=SAMBANOVA_URL),
        llm=openai.LLM(model=SAMBANOVA_LLM_MODEL, api_key=SAMBANOVA_API_KEY, base_url=SAMBANOVA_URL),
        tts=tts,
        vad=ctx.proc.userdata['vad'],
        mcp_servers=[mcp.MCPServerStdio(command='python', args=['-m', 'mcp_server_time'], env={})],
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
    )
    await session.generate_reply(instructions="Say 'Hi there! How can I help you today?'")


if __name__ == '__main__':
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name='sambanova-agent',
        )
    )
