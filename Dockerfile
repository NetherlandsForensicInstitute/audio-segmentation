FROM ubuntu

ENV DEBIAN_FRONTEND noninteractive

RUN apt update
RUN apt install -y libsndfile-dev gcc python3-dev python3-pip

RUN python3 -m pip install --prefix='/usr/local' pydub logbook tensorflow inaspeechsegmenter sndfile

COPY dist dist
RUN python3 -m pip install --prefix='/usr/local' --no-warn-script-location dist/*.whl

LABEL maintainer="fbda@nfi.nl"
LABEL hansken.extraction.plugin.image="audio-segmentation"
LABEL hansken.extraction.plugin.name="AudioSegmentation"

COPY /plugin /

EXPOSE 8999

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["serve_plugin 'audio_segmentation.py' 8999"]
