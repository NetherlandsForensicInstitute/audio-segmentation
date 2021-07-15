FROM ubuntu

ENV DEBIAN_FRONTEND noninteractive

RUN apt update
RUN apt install -y libsndfile-dev gcc python3-dev python3-pip ffmpeg

RUN python3 -m pip install pydub logbook tensorflow inaspeechsegmenter sndfile hansken_extraction_plugin

LABEL maintainer="fbda@nfi.nl"
LABEL hansken.extraction.plugin.image="audio-segmentation"
LABEL hansken.extraction.plugin.name="AudioSegmentation"

COPY /plugin /

EXPOSE 8999

ENTRYPOINT ["/usr/local/bin/serve_plugin"]
CMD ["audio_segmentation.py", "8999"]
