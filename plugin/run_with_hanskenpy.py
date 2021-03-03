from hansken_extraction_plugin.runtime.extraction_plugin_runner import run_with_hanskenpy

from audio_segmentation import AudioSegmentation


def main():
    run_with_hanskenpy(AudioSegmentation)


if __name__ == '__main__':
    main()
