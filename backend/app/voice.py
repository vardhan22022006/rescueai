"""
Server-side audio transcription stub for RescueAI.

Current use-case
----------------
Browser-based voice reports are transcribed client-side via the Web Speech
API (see frontend/src/components/VoiceReportForm.jsx) so this module is NOT
called in the normal intake flow.

This stub exists for a different scenario: transcribing raw audio files that
arrive from phone-call recordings (e.g. IVR calls forwarded by Twilio Voice,
or uploaded .wav/.mp3 files from field devices).

How to wire in whisper.cpp (free, local, no API key)
-----------------------------------------------------
1.  Install whisper.cpp:
        git clone https://github.com/ggerganov/whisper.cpp
        cd whisper.cpp && make

2.  Download a model (the "base" model is ~140 MB and works well for
    short disaster reports):
        bash models/download-ggml-model.sh base

3.  Install the Python binding:
        pip install pywhisper          # OR
        pip install git+https://github.com/aarnphm/whispercpp.git

4.  Replace the stub body below with:

        import whispercpp
        model = whispercpp.Whisper.from_pretrained("base")

        def transcribe_audio(file: bytes, language: str = "en") -> str:
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(file)
                tmp_path = tmp.name
            try:
                result = model.transcribe(tmp_path)
                return result["text"].strip()
            finally:
                os.unlink(tmp_path)

5.  Wire it into the intake endpoint by adding a new route (example):

        @router.post("/reports/intake/audio")
        async def intake_audio(
            audio: UploadFile,
            background_tasks: BackgroundTasks,
            source: SourceEnum = SourceEnum.voice,
            reporter_phone: Optional[str] = None,
            db: Session = Depends(get_db),
        ):
            raw_bytes = await audio.read()
            raw_text  = transcribe_audio(raw_bytes)          # <-- this module
            payload   = IntakePayload(
                source=source,
                raw_text=raw_text,
                reporter_phone=reporter_phone,
            )
            return _intake(payload, background_tasks, db)

Alternative free models
-----------------------
- faster-whisper   : pip install faster-whisper  (4-8× faster on CPU)
- openai-whisper   : pip install openai-whisper  (official Python package,
                     runs locally, ~1 GB for "small" model)
- vosk             : pip install vosk             (tiny, real-time capable,
                     good for low-resource devices)

All of the above run fully offline with no API key.
"""

from typing import Optional


def transcribe_audio(file: bytes, language: Optional[str] = "en") -> str:
    """
    Transcribe raw audio bytes to text.

    Args:
        file:     Raw audio content (WAV preferred; MP3/OGG also accepted by
                  most backends after conversion with ffmpeg).
        language: BCP-47 language hint, e.g. "en", "hi", "bn".
                  Pass None to let the model auto-detect.

    Returns:
        Transcribed text string.

    Raises:
        NotImplementedError: Always, until a real backend is wired in.
                             See module docstring for instructions.
    """
    # TODO: replace this raise with a real transcription backend.
    # See the module docstring above for step-by-step whisper.cpp wiring.
    raise NotImplementedError(
        "transcribe_audio() is a stub. "
        "See backend/app/voice.py for instructions on wiring in whisper.cpp "
        "or another free local transcription model."
    )
