# audio-segmentation
Extraction plugin for Hansken to classify and segment audio, relying heavily on the model in `inaSpeechSegmenter`

Please note that this model was not developed or trained by the Netherlands Forensic Institute.
This is merely a container that supports running the classification on Hansken projects.

## Building
To build, make sure you have acquired a wheel for the `extraction_plugin` package, and put it in your `dist`
folder.

After that, build the Docker image:

```bash
docker build -t audiosegmentation .
```

