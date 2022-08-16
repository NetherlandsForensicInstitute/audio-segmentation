FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt --fix-missing update
RUN apt install -y libsndfile-dev gcc python3-dev python3-pip ffmpeg curl

RUN python3 -m pip install --no-cache pydub logbook tensorflow inaspeechsegmenter sndfile hansken_extraction_plugin dockerfile-parse

# Deprecated labels
LABEL maintainer="b.broere@nfi.nl"
LABEL hansken.extraction.plugin.image="audio-segmentation"
LABEL hansken.extraction.plugin.name="AudioSegmentation"

# New 0.6.0 labels that are read by audio_segmentation.py to serve the plugin info as well
LABEL org.hansken.plugin-info.id="nfi.nl/media/AudioSegmentation"
LABEL org.hansken.plugin-info.id-domain="nfi.nl"
LABEL org.hansken.plugin-info.id-category="media"
LABEL org.hansken.plugin-info.id-name="AudioSegmentation"
LABEL org.hansken.plugin-info.version="2022.8.16"
# TODO Find out if we can raise an error on docker build once this needs a bump
#      The value can be imported from the hansken_extraction_plugin Python package
LABEL org.hansken.plugin-info.api-version="0.5.0"
LABEL org.hansken.plugin-info.description="Audio segmentation and classification"
LABEL org.hansken.plugin-info.webpage="https://git.eminjenv.nl/hanskaton/extraction-plugins/audio-segmentation"
LABEL org.hansken.plugin-info.matcher='type:audio NOT prediction.modelName=inaSpeechSegmenter AND $data.type=transcoded'
LABEL org.hansken.plugin-info.license="Apache License 2.0"
LABEL org.hansken.plugin-info.maturity-level="PRODUCTION_READY"
LABEL org.hansken.plugin-info.author-name="Bart Broere"
LABEL org.hansken.plugin-info.author-organisation="NFI"
LABEL org.hansken.plugin-info.author-email="b.broere@nfi.nl"
LABEL org.hansken.plugin-info.resource-max-cpu="0.5"
LABEL org.hansken.plugin-info.resource-max-mem="1024"

COPY . /

EXPOSE 8999

# preload the model for offline Hansken installations
WORKDIR /
RUN curl -L https://github.com/ina-foss/inaSpeechSegmenter/releases/download/models/keras_speech_music_noise_cnn.hdf5 > /keras_speech_music_noise_cnn.hdf5

ENTRYPOINT ["/usr/local/bin/serve_plugin"]
CMD ["audio_segmentation.py", "8999"]
