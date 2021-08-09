# audio-segmentation
Extraction plugin for Hansken to classify and segment audio, relying heavily on the model in `inaSpeechSegmenter`

Please note that this model was not developed or trained by the Netherlands Forensic Institute.
This is merely a container that supports running the classification on Hansken projects.

## Building
Build the Docker image:

```bash
docker build -t audiosegmentation .
```

## Developing
When developing and debugging, it's possible to avoid the Docker build step by simulating a tool run using hansken.py

Install the dependencies from `setup.py` and run the main entry point in `audio_segmentation.py`, specifying the required
command line arguments.
