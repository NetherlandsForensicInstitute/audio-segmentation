import shutil
import wave
from io import BytesIO
from tempfile import NamedTemporaryFile

from hansken_extraction_plugin.api.extraction_plugin import ExtractionPlugin
from hansken_extraction_plugin.api.plugin_info import Author, MaturityLevel, PluginInfo, PluginId, PluginResources
from hansken_extraction_plugin.api.tracelet import Tracelet
from hansken_extraction_plugin.api.transformation import RangedTransformation, Range
from hansken_extraction_plugin.runtime.extraction_plugin_runner import run_with_hanskenpy
from inaSpeechSegmenter import Segmenter
from inaSpeechSegmenter.segmenter import DnnSegmenter
from logbook import Logger
from tensorflow import keras
from dockerfile_parse import DockerfileParser

log = Logger(__name__)
dockerfile_parser = DockerfileParser()

with open('Dockerfile', 'r') as f:
    dockerfile_parser.content = f.read()

docker_labels = dockerfile_parser.labels

VERSION = docker_labels['org.hansken.plugin-info.version']


class CustomDnnSegmenter(DnnSegmenter):
    outlabels = ('speech', 'music', 'noise')
    model_fname = 'keras_speech_music_noise_cnn.hdf5'
    inlabel = 'energy'
    nmel = 21
    viterbi_arg = 80

    def __init__(self, batch_size):  # noqa (We intentionally don't call the super __init__ because it wants internet)
        model_path = f'/{self.model_fname}'
        self.nn = keras.models.load_model(model_path, compile=False)
        self.batch_size = batch_size


class CustomSegmenter(Segmenter):

    def __init__(self, ffmpeg='ffmpeg', batch_size=32, energy_ratio=0.03):
        """
        Custom __init__ method that avoids using an internet connection.
        Everything is currently hardcoded to use the SMN model.
        """
        # test ffmpeg installation
        if shutil.which(ffmpeg) is None:
            raise (Exception("""ffmpeg program not found"""))
        self.ffmpeg = ffmpeg
        self.vad = CustomDnnSegmenter(batch_size)
        self.detect_gender = False
        self.energy_ratio = energy_ratio


def build_byte_dictionary(data):
    """
    Build a mapping of bytes to offsets in the stream.

    :param data: expected to be a bytestring, but a list of integers would also work
    :return: an inverted dictionary mapping bytes to offsets in the stream
    """
    return {v: k for k, v in dict(enumerate(data)).items()}


def get_descriptor_using_byte_dictionary(data, dictionary):
    """
    Get a list of offsets to reconstruct the input data

    :param data: data to get a list of offsets for
    :param dictionary: output of the build_byte_dictionary method
    :return: a list of offsets that should be the same size as the input data
    """
    descriptor = []
    for byte in data:
        descriptor.append(dictionary.get(byte))
    return descriptor


def get_ranges_using_byte_dictionary(data, dictionary):
    """
    Get a list of Range objects to get bytes from random parts of the input stream.

    :param data: data to get a list of Ranges for
    :param dictionary: output of the build_byte_dictionary method
    :return: a list of Range objects that reconstructs the input data
    """
    try:
        return [Range(index, 1)
                for index in get_descriptor_using_byte_dictionary(data, dictionary)]
    except:  # noqa
        return []


class AudioSegmentation(ExtractionPlugin):

    def plugin_info(self):
        # To update plugin info, update the Dockerfile.
        # This has been done to maintain a single source of truth for all these values
        plugin_info = PluginInfo(
            id=PluginId(domain=docker_labels["org.hansken.plugin-info.id-domain"],
                        category=docker_labels["org.hansken.plugin-info.id-category"],
                        name=docker_labels["org.hansken.plugin-info.id-name"]),
            version=VERSION,
            description=docker_labels["org.hansken.plugin-info.description"],
            author=Author(docker_labels['org.hansken.plugin-info.author-name'], 
                          docker_labels['org.hansken.plugin-info.author-email'], 
                          docker_labels['org.hansken.plugin-info.author-organisation']),
            # TODO find out how the maturity level can be read from the Dockerfile
            maturity=MaturityLevel.PRODUCTION_READY,  
            webpage_url=docker_labels['org.hansken.plugin-info.webpage'],
            # The transcoded stream is produced by traces/audio, and is ideal for our purpose.
            # Since it's wav, we can slice fragments using byte offsets
            matcher=docker_labels['org.hansken.plugin-info.matcher'],
            license=docker_labels['org.hansken.plugin-info.license'],
            resources=PluginResources(maximum_cpu=docker_labels['org.hansken.plugin-info.resource-max-cpu'],
                                      maximum_memory=docker_labels['org.hansken.plugin-info.resource-max-mem']),
        )
        log.debug(f'returning plugin info: {plugin_info}')
        return plugin_info

    def process(self, trace, data_context):
        """
        Classify audio fragments, and write subfragments as child traces.

        :param trace: expected to be an audio file
        :param data_context: data_context
        """
        log.info(f"processing trace {trace.get('name')}")
        byte_dictionary = build_byte_dictionary(trace.open().read(data_context.data_size))
        with NamedTemporaryFile('wb') as temporary_inputfragment:
            # Try to read in the fragment that we are going to process and store it temporarily
            temporary_inputfragment.write(trace.open().read(data_context.data_size))
            labeled_fragments = CustomSegmenter()(temporary_inputfragment.name)
            inputfragment = wave.open(BytesIO(trace.open().read(data_context.data_size)), 'rb')

            # This loop writes out each individual fragment as a child trace
            for i, (label, start, end) in enumerate(labeled_fragments):
                # Create a new child trace
                child_trace = trace.child_builder(name=f'Fragment #{i} ({label}) in {trace.get("name")}')

                # Calculate the frame where our classified fragment starts and ends
                start_frame = start * inputfragment.getframerate()
                end_frame = end * inputfragment.getframerate()

                # By seeking through the file, find the byte offset where our classified fragment starts and ends
                inputfragment.readframes(int(start_frame))
                start_byte = inputfragment._file.file.tell()
                inputfragment.readframes(int(end_frame - start_frame))
                end_byte = inputfragment._file.file.tell()

                # hacky way to make the headers contain the right sizes
                data_size = end_byte - start_byte  # see wav spec
                file_size = end_byte - start_byte + 44 - 8  # see wav spec
                data_size = data_size.to_bytes(4, "little")
                file_size = file_size.to_bytes(4, "little")
                data_size = get_ranges_using_byte_dictionary(data_size, byte_dictionary)
                file_size = get_ranges_using_byte_dictionary(file_size, byte_dictionary)

                # if it's possible to construct a wav file with better integrity, we do that
                if file_size and data_size:
                    child_trace.add_transformation(
                        'raw',
                        RangedTransformation([
                            Range(0, 4),  # the magic of the wav-file
                            *file_size,  # the size of the entire file minus 8 bytes
                            Range(8, 32),  # the part of the original header that can be kept intact
                            *data_size,  # the size of the data containing wave samples
                            Range(start_byte, end_byte - start_byte)  # the classified fragment's byte offset
                        ])
                    )

                # if we can't create a correct wav file, we copy the original header verbatim
                else:
                    child_trace.add_transformation(
                        'raw',
                        RangedTransformation([
                            Range(0, 44),  # the header of the original wav-file
                            Range(start_byte, end_byte - start_byte)  # the classified fragment's byte offset
                        ])
                    )
                child_trace.add_tracelet(
                    Tracelet('prediction', {
                        'prediction.type': 'classification',
                        'prediction.modelName': 'inaSpeechSegmenter',
                        'prediction.modelVersion': VERSION,
                        'prediction.class': label
                    })
                )
                child_trace.build()

                # Rewind it for our next classified audio sample
                inputfragment.rewind()


if __name__ == '__main__':
    run_with_hanskenpy(AudioSegmentation)
